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


class ContributionService(Service):
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
            return [snapshot(row) for row in ContributionRepository(session).periods.list()]

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
        """Explicit member selection defines eligibility; archived/deceased members are excluded."""
        with self.transaction() as session:
            repo = ContributionRepository(session)
            period = repo.periods.get(period_id, lock=True)
            if period.status is ContributionPeriodStatus.CLOSED:
                raise ValidationError("Period is closed")
            created = []
            for member_id in dict.fromkeys(member_ids):
                member = FamilyRepository(session).get(member_id)
                if not member.is_active or member.living_status is LivingStatus.DECEASED:
                    raise ValidationError("Only active, non-deceased members can be assigned")
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
                       reference=None, remarks=None):
        amount = money(amount_paid, positive=True)
        with self.transaction() as session:
            repo = ContributionRepository(session)
            initial = repo.get(obligation_id)
            period = repo.periods.get(initial.contribution_period_id, lock=True)
            row = repo.get(obligation_id, lock=True)
            if period.status is not ContributionPeriodStatus.ACTIVE:
                raise ValidationError("Payments require an active period")
            if amount > self.balance(repo, row)["outstanding"]:
                raise ValidationError("Payment exceeds the outstanding balance")
            paid_on = payment_date or date.today()
            if paid_on > date.today():
                raise ValidationError("Payment date cannot be in the future")
            payment = repo.payments.add(ContributionPayment(
                member_contribution_id=row.id, amount_paid=amount, payment_date=paid_on,
                payment_method=PaymentMethod(payment_method), reference=reference, remarks=remarks,
                receipt_number="R-" + uuid.uuid4().hex, received_by=self.actor_id, recorded_by=self.actor_id))
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

    def obligations(self, period_id=None, member_id=None, status=None):
        with self.transaction() as session:
            repo = ContributionRepository(session)
            criteria = []
            if period_id:
                criteria.append(MemberContribution.contribution_period_id == period_id)
            if member_id:
                criteria.append(MemberContribution.family_member_id == member_id)
            rows = [dict(snapshot(row), **self.balance(repo, row)) for row in repo.list(*criteria)]
            return [row for row in rows if status is None or row["status"] == status]

    def payment_history(self, obligation_id):
        with self.transaction() as session:
            return [snapshot(row) for row in ContributionRepository(session).payment_history(obligation_id)]

    def summary(self, period_id):
        rows = self.obligations(period_id=period_id)
        return {"expected_total": sum((r["amount_due"] for r in rows), Decimal("0")),
                "collected": sum((r["total_paid"] for r in rows), Decimal("0")),
                "outstanding": sum((r["outstanding"] for r in rows), Decimal("0")),
                **{s.value: sum(r["status"] == s.value for r in rows) for s in ContributionStatus}}
