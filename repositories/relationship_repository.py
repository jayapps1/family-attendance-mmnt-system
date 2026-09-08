from sqlalchemy import select, or_
from models import FamilyRelationship, Marriage
from repositories.base import Repository


class RelationshipRepository(Repository[FamilyRelationship]):
    def __init__(self, session):
        super().__init__(session, FamilyRelationship)

    def edges(self):
        return list(self.session.execute(select(FamilyRelationship.parent_id, FamilyRelationship.child_id)))

    def marriages(self, member_id=None):
        query = select(Marriage)
        if member_id:
            query = query.where(or_(Marriage.spouse_one_id == member_id, Marriage.spouse_two_id == member_id))
        return list(self.session.scalars(query))
