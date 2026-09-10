from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from models import (
    ContributionType, ContributionFrequency, ContributionPeriod, ContributionPeriodStatus,
    MemberContribution, ContributionStatus, ContributionPayment, PaymentMethod, LivingStatus,
)
from repositories.contribution_repository import ContributionRepository
from repositories.family_repository import FamilyRepository
from services.base import Service, snapshot
from utils.validators import money, required, dates, ValidationError


from services.simple_contribution import SimpleContributionMixin
from services.contribution_eligibility import require_eligible, historical_period


class ContributionService(SimpleContributionMixin, Service):
    """All financial writes and cached status updates commit atomically with audit events."""

    @staticmethod
    def balance(repo, row):
        paid = repo.total_paid(row.id)
        status = (ContributionStatus.PAID if paid >= row.amount_due else
                  ContributionStatus.PARTIALLY_PAID if paid > 0 else ContributionStatus.UNPAID)
        return {"total_paid": paid, "outstanding": row.amount_due - paid, "status": status.value}

    def types(self):
        with self.transaction() as session:
            return [snapshot(row) for row in ContributionRepository(session).types.list()]

    def create_type(self, name, frequency, default_amount=None, description=None):
        with self.transaction() as session:
            row = ContributionRepository(session).types.add(ContributionType(
                name=required(name, "Name", 150), frequency=ContributionFrequency(frequency),
                default_amount=money(default_amount) if default_amount is not None else None,
                description=description, created_by=self.actor_id))
            self.audit(session, "CREATE_CONTRIBUTION_TYPE", row)
            return snapshot(row)

    def periods(self):
        with self.transaction() as session:
            repo = ContributionRepository(session)
            return [dict(snapshot(row), frequency=repo.types.get(row.contribution_type_id).frequency.value) for row in sorted(repo.periods.list(), key=lambda p:(p.year or 0,p.created_at,str(p.id)), reverse=True)]

    def create_period(self, contribution_type_id, title, amount_per_member, year=None,
                      start_date=None, due_date=None, description=None):
        dates(start_date, due_date)
        with self.transaction() as session:
            repo = ContributionRepository(session)
            kind = repo.types.get(contribution_type_id)
            if not kind.is_active:
                raise ValidationError("Contribution type is inactive")
            row = repo.periods.add(ContributionPeriod(
                contribution_type_id=contribution_type_id, title=required(title, "Title"),
                amount_per_member=money(amount_per_member), year=year, start_date=start_date,
                due_date=due_date, description=description, created_by=self.actor_id))
            self.audit(session, "CREATE_CONTRIBUTION", row)
            return snapshot(row)

    def set_period_status(self, period_id, status):
        target = ContributionPeriodStatus(status)
        with self.transaction() as session:
            row = ContributionRepository(session).periods.get(period_id, lock=True)
            allowed = {ContributionPeriodStatus.DRAFT: {ContributionPeriodStatus.ACTIVE},
                       ContributionPeriodStatus.ACTIVE: {ContributionPeriodStatus.CLOSED},
                       ContributionPeriodStatus.CLOSED: set()}
            if target != row.status and target not in allowed[row.status]:
                raise ValidationError("Period can only move from draft to active to closed")
            row.status = target
            self.audit(session, "UPDATE_CONTRIBUTION_PERIOD", row)
            return snapshot(row)

    def assign_members(self, period_id, member_ids):
        """Assignment and all payment paths enforce the centralized eligibility rule."""
        with self.transaction() as session:
            repo = ContributionRepository(session)
            period = repo.periods.get(period_id, lock=True)
            if period.status is ContributionPeriodStatus.CLOSED:
                raise ValidationError("Period is closed")
            created = []
            for member_id in dict.fromkeys(member_ids):
                member = FamilyRepository(session).get(member_id, lock=True)
                require_eligible(member)
                if repo.find(period_id, member_id):
                    continue
                row = repo.add(MemberContribution(
                    contribution_period_id=period_id, family_member_id=member_id,
                    amount_due=period.amount_per_member,
                    status=ContributionStatus.PAID if period.amount_per_member == 0 else ContributionStatus.UNPAID))
                self.audit(session, "ASSIGN_CONTRIBUTION", row)
                created.append(snapshot(row))
            return created

    def record_payment(self, obligation_id, amount_paid, payment_method, payment_date=None,
                       reference=None, remarks=None, receipt_number=None):
        amount = money(amount_paid, positive=True)
        receipt = required(receipt_number, "Receipt number", 80) if receipt_number else "R-" + uuid.uuid4().hex
        with self.transaction() as session:
            repo = ContributionRepository(session)
            initial = repo.get(obligation_id)
            period = repo.periods.get(initial.contribution_period_id, lock=True)
            row = repo.get(obligation_id, lock=True)
            if period.status is not ContributionPeriodStatus.ACTIVE:
                raise ValidationError("Payments require an active period")
            require_eligible(FamilyRepository(session).get(row.family_member_id, lock=True))
            from sqlalchemy import select
            if session.scalar(select(ContributionPayment.id).where(ContributionPayment.receipt_number == receipt)):
                raise ValidationError('This receipt has already been recorded. Check payment history before recording another payment.')
            outstanding = self.balance(repo, row)['outstanding']
            if amount > outstanding:
                raise ValidationError(f'Amount received is greater than the remaining balance of GHS {outstanding:,.2f}.')
            paid_on = payment_date or date.today()
            if paid_on > date.today():
                raise ValidationError("Payment date cannot be in the future")
            payment = repo.payments.add(ContributionPayment(
                member_contribution_id=row.id, amount_paid=amount, payment_date=paid_on,
                payment_method=PaymentMethod(payment_method), reference=reference, remarks=remarks,
                receipt_number=receipt, received_by=self.actor_id, recorded_by=self.actor_id))
            row.status = ContributionStatus(self.balance(repo, row)["status"])
            self.audit(session, "RECORD_PAYMENT", payment)
            return snapshot(payment)

    def reverse_payment(self, payment_id, reason):
        reason = required(reason, "Reversal reason", 2000)
        with self.transaction() as session:
            repo = ContributionRepository(session)
            initial = repo.payments.get(payment_id)
            obligation = repo.get(initial.member_contribution_id)
            repo.periods.get(obligation.contribution_period_id, lock=True)
            obligation = repo.get(obligation.id, lock=True)
            payment = repo.payments.get(payment_id, lock=True)
            if payment.is_reversed:
                raise ValidationError("Payment has already been reversed")
            payment.is_reversed, payment.reversed_by = True, self.actor_id
            payment.reversed_at, payment.reversal_reason = datetime.now(timezone.utc), reason
            session.flush()
            obligation.status = ContributionStatus(self.balance(repo, obligation)["status"])
            self.audit(session, "REVERSE_PAYMENT", payment, reason)
            return snapshot(payment)

    def obligations(self, period_id=None, member_id=None, status=None, affiliation_type=None):
        with self.transaction() as session:
            repo = ContributionRepository(session)
            criteria = []
            if period_id:
                criteria.append(MemberContribution.contribution_period_id == period_id)
            if member_id:
                criteria.append(MemberContribution.family_member_id == member_id)
            rows = []
            for row in repo.list(*criteria):
                member = FamilyRepository(session).get(row.family_member_id)
                if affiliation_type is not None and member.affiliation_type.value != affiliation_type:
                    continue
                period = repo.periods.get(row.contribution_period_id)
                kind = repo.types.get(period.contribution_type_id)
                rows.append(dict(snapshot(row), **self._preview(session, period, member)))
            return [row for row in rows if status is None or row["status"] == status]

    def payment_history(self, obligation_id):
        with self.transaction() as session:
            from repositories.user_repository import UserRepository
            names = UserRepository(session).names()
            return [dict(snapshot(row), recorded_by_name=names.get(row.recorded_by, "Unknown"))
                    for row in ContributionRepository(session).payment_history(obligation_id)]

    def summary(self, period_id, affiliation_type=None):
        return self.daily_summary(period_id, affiliation_type)

    def get_obligation(self, obligation_id):
        with self.transaction() as session:
            row = ContributionRepository(session).get(obligation_id)
            period_id, member_id = row.contribution_period_id, row.family_member_id
        return next(r for r in self.obligations(period_id, member_id) if r['id'] == obligation_id)

    def recent_payments(self, period_id=None, limit=10, search="", method=None, status=None, payment_date=None):
        from repositories.user_repository import UserRepository
        with self.transaction() as session:
            names = UserRepository(session).names()
            result = []
            for payment, obligation, member, period, kind in ContributionRepository(session).transactions(period_id):
                label = " ".join(filter(None, (member.first_name, member.middle_name, member.last_name)))
                if search.casefold().strip() not in (label + " " + member.family_number + " " + (payment.receipt_number or "") + " " + (payment.reference or "")).casefold():
                    continue
                state = "REVERSED" if payment.is_reversed else "VALID"
                if method and payment.payment_method.value != method or status and state != status:
                    continue
                if payment_date and payment.payment_date != payment_date:
                    continue
                result.append(dict(snapshot(payment), member=label, family_number=member.family_number,
                    contribution=kind.name, period=period.title, contribution_period_id=period.id,
                    family_member_id=member.id, recorded_by_name=names.get(payment.recorded_by, "Unknown"),
                    received_by_name=names.get(payment.received_by, "Unknown"), reversed_by_name=names.get(payment.reversed_by, ""),
                    payment_status=state, action="View / Reverse" if not payment.is_reversed else "View"))
            return result if limit is None else result[:limit]

    def payment_summary(self, period_id=None):
        rows = [r for r in self.recent_payments(limit=None) if not r["is_reversed"]]
        today = date.today()
        daily = [r for r in rows if r["payment_date"] == today]
        monthly = [r for r in rows if (r["payment_date"].year, r["payment_date"].month) == (today.year, today.month)]
        current = [r for r in rows if period_id and r["contribution_period_id"] == period_id]
        total = lambda entries: sum((r["amount_paid"] for r in entries), Decimal("0.00"))
        return dict(payments_today=len(daily), collected_today=total(daily), payments_month=len(monthly),
                    collected_month=total(monthly), current_collected=total(current))

    def period_overview(self):
        return [dict(period, **self.daily_summary(period["id"])) for period in self.periods()]

    def update_period(self, identity, contribution_type_id, title, amount_per_member, year=None,
                      start_date=None, due_date=None, description=None):
        dates(start_date, due_date)
        amount = money(amount_per_member)
        with self.transaction() as session:
            repo = ContributionRepository(session)
            row = repo.periods.get(identity, lock=True)
            if row.status is ContributionPeriodStatus.CLOSED:
                raise ValidationError("Closed periods cannot be edited.")
            from models import MemberContribution
            if repo.list(MemberContribution.contribution_period_id == identity) and (
                    row.amount_per_member != amount or row.contribution_type_id != contribution_type_id or row.year != year):
                raise ValidationError("Amount, type and year cannot change after obligations exist. Create a new period.")
            if not repo.types.get(contribution_type_id).is_active:
                raise ValidationError("Contribution type is inactive")
            row.contribution_type_id, row.title, row.amount_per_member = contribution_type_id, required(title, "Title"), amount
            row.year, row.start_date, row.due_date, row.description = year, start_date, due_date, description
            self.audit(session, "UPDATE_CONTRIBUTION_PERIOD", row)
            return snapshot(row)
