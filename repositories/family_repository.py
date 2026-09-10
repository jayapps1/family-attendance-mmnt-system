from sqlalchemy import select, or_, func
from models import FamilyMember
from repositories.base import Repository


class FamilyRepository(Repository[FamilyMember]):
    def __init__(self, session):
        super().__init__(session, FamilyMember)

    def search(self, text="", active=None, affiliation_type=None, living_status=None):
        query = select(FamilyMember)
        if text:
            term = "%" + text.replace("%", r"\%").replace("_", r"\_") + "%"
            query = query.where(or_(*[column.ilike(term, escape="\\") for column in (
                FamilyMember.family_number, FamilyMember.first_name, FamilyMember.middle_name, FamilyMember.last_name,
                FamilyMember.phone_number, FamilyMember.current_residence, func.concat_ws(" ", FamilyMember.first_name, FamilyMember.middle_name, FamilyMember.last_name))]))
        if living_status is not None:
            from models import LivingStatus
            query = query.where(FamilyMember.living_status == LivingStatus(living_status))
        if affiliation_type is not None:
            from models import FamilyAffiliationType
            query = query.where(FamilyMember.affiliation_type == FamilyAffiliationType(affiliation_type))
        if active is not None:
            query = query.where(FamilyMember.is_active == active)
        return list(self.session.scalars(query.order_by(FamilyMember.last_name, FamilyMember.first_name)))
