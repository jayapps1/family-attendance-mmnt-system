from decimal import Decimal
from sqlalchemy import select, func
from models import ContributionType, ContributionPeriod, MemberContribution, ContributionPayment
from repositories.base import Repository


class ContributionRepository(Repository[MemberContribution]):
    def __init__(self, session):
        super().__init__(session, MemberContribution)
        self.types = Repository(session, ContributionType)
        self.periods = Repository(session, ContributionPeriod)
        self.payments = Repository(session, ContributionPayment)

    def find(self, period_id, member_id):
        return self.session.scalar(select(MemberContribution).where(
            MemberContribution.contribution_period_id == period_id,
            MemberContribution.family_member_id == member_id))

    def total_paid(self, obligation_id) -> Decimal:
        return self.session.scalar(select(func.coalesce(func.sum(ContributionPayment.amount_paid), 0)).where(
            ContributionPayment.member_contribution_id == obligation_id,
            ContributionPayment.is_reversed.is_(False))) or Decimal("0.00")

    def payment_history(self, obligation_id):
        return list(self.session.scalars(select(ContributionPayment).where(
            ContributionPayment.member_contribution_id == obligation_id
        ).order_by(ContributionPayment.payment_date, ContributionPayment.created_at)))

    def annual_periods(self, year=None):
        from models import ContributionFrequency
        query = select(ContributionPeriod).join(ContributionType).where(ContributionType.frequency == ContributionFrequency.ANNUAL)
        if year is not None:
            query = query.where(ContributionPeriod.year == year)
        return list(self.session.scalars(query.order_by(ContributionPeriod.year.desc().nulls_last(), ContributionPeriod.created_at.desc())))
