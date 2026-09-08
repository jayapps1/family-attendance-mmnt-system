"""Daily annual collection: read-only previews and atomic first payments."""
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import sessionmaker
from models import ContributionType, ContributionFrequency, ContributionPeriod, ContributionPeriodStatus, MemberContribution, ContributionStatus, LivingStatus
from repositories.contribution_repository import ContributionRepository
from repositories.family_repository import FamilyRepository
from services.base import snapshot
from utils.validators import ValidationError, money


class SimpleContributionMixin:
    def setup_annual(self, year, amount_per_member):
        if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 9999:
            raise ValidationError('Enter a valid four-digit contribution year.')
        amount = money(amount_per_member, positive=True)
        with self.transaction() as session:
            repo = ContributionRepository(session)
            repo.lock_domain('annual_contribution_setup')
            existing = repo.annual_periods(year)
            if existing:
                if len(existing) != 1:
                    raise ValidationError('Multiple annual contributions already exist for this year. Select the required period in Contributions.')
                period = repo.periods.get(existing[0].id, lock=True)
                if period.amount_per_member != amount:
                    raise ValidationError('This year is already configured with a different amount. Existing obligations and payments must be preserved.')
                if period.status is ContributionPeriodStatus.CLOSED:
                    raise ValidationError('This annual contribution is closed.')
                period.status = ContributionPeriodStatus.ACTIVE
                self.audit(session, 'SETUP_ANNUAL_CONTRIBUTION', period)
                return snapshot(period)
            kind = next((r for r in repo.types.list() if r.name == 'Annual Family Contribution'), None)
            if kind is None:
                kind = repo.types.add(ContributionType(name='Annual Family Contribution', frequency=ContributionFrequency.ANNUAL, created_by=self.actor_id))
                self.audit(session, 'CREATE_CONTRIBUTION_TYPE', kind)
            if not kind.is_active or kind.frequency is not ContributionFrequency.ANNUAL:
                raise ValidationError('The Annual Family Contribution type must be active and annual.')
            period = repo.periods.add(ContributionPeriod(contribution_type_id=kind.id, title=f'Annual Contribution {year}',
                year=year, amount_per_member=amount, start_date=date(year,1,1), due_date=date(year,12,31),
                status=ContributionPeriodStatus.ACTIVE, created_by=self.actor_id))
            self.audit(session, 'SETUP_ANNUAL_CONTRIBUTION', period)
            return snapshot(period)

    def _preview(self, session, period, member):
        repo = ContributionRepository(session)
        kind = repo.types.get(period.contribution_type_id)
        row = repo.find(period.id, member.id)
        due = row.amount_due if row else period.amount_per_member
        paid = repo.total_paid(row.id) if row else Decimal('0.00')
        can_create = kind.frequency is ContributionFrequency.ANNUAL and member.is_active and member.living_status is not LivingStatus.DECEASED
        return dict(id=row.id if row else None, family_member_id=member.id, contribution_period_id=period.id,
            member=' '.join(filter(None,(member.first_name,member.middle_name,member.last_name))), family_number=member.family_number,
            affiliation_type=member.affiliation_type.value, period=period.title, contribution=kind.name,
            period_status=period.status.value, amount_due=due, total_paid=paid, outstanding=due-paid,
            status='PAID' if paid >= due else 'PARTIALLY_PAID' if paid > 0 else 'UNPAID',
            can_pay=period.status is ContributionPeriodStatus.ACTIVE and due > paid and (row is not None or can_create))

    def payment_preview(self, period_id, member_id):
        with self.transaction() as session:
            period = ContributionRepository(session).periods.get(period_id)
            return self._preview(session, period, FamilyRepository(session).get(member_id))

    def register_rows(self, period_id):
        with self.transaction() as session:
            repo = ContributionRepository(session)
            period = repo.periods.get(period_id)
            kind = repo.types.get(period.contribution_type_id)
            assigned = {r.family_member_id for r in repo.list(MemberContribution.contribution_period_id == period_id)}
            return [self._preview(session, period, member) for member in FamilyRepository(session).search()
                    if member.id in assigned or (period.status is ContributionPeriodStatus.ACTIVE and kind.frequency is ContributionFrequency.ANNUAL
                       and member.is_active and member.living_status is not LivingStatus.DECEASED)]

    def daily_summary(self, period_id):
        rows = self.register_rows(period_id)
        return dict(total_members=len(rows), expected_total=sum((r['amount_due'] for r in rows), Decimal('0')),
            collected=sum((r['total_paid'] for r in rows), Decimal('0')), outstanding=sum((r['outstanding'] for r in rows), Decimal('0')),
            **{status: sum(r['status'] == status for r in rows) for status in ('PAID','PARTIALLY_PAID','UNPAID')})

    def record_contribution(self, member_id, period_id, amount_paid, payment_method='CASH', **values):
        # Reuse the established payment transaction, bound to this same connection/savepoint.
        # A failed payment rolls back the automatically created obligation as well.
        with self.transaction() as session:
            repo = ContributionRepository(session)
            period = repo.periods.get(period_id, lock=True)
            if period.status is not ContributionPeriodStatus.ACTIVE:
                raise ValidationError('Payments require an active period')
            row = repo.find(period_id, member_id)
            if row is None:
                kind = repo.types.get(period.contribution_type_id)
                member = FamilyRepository(session).get(member_id, lock=True)
                if kind.frequency is not ContributionFrequency.ANNUAL:
                    raise ValidationError('Assign this member to the non-annual contribution first.')
                if not member.is_active or member.living_status is LivingStatus.DECEASED:
                    raise ValidationError('New annual obligations require an active, non-deceased member.')
                row = repo.add(MemberContribution(contribution_period_id=period_id, family_member_id=member_id,
                    amount_due=period.amount_per_member, status=ContributionStatus.UNPAID))
                self.audit(session, 'ASSIGN_CONTRIBUTION', row)
            nested = sessionmaker(bind=session.connection(), join_transaction_mode='create_savepoint')
            service = type(self)(nested, self.actor_id)
            payment = service.record_payment(row.id, amount_paid, payment_method, **values)
            return dict(payment, summary=self._preview(session, period, FamilyRepository(session).get(member_id)))
