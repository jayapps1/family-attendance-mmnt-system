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

    def shared_children(self, one, two):
        from models import FamilyMember
        from sqlalchemy.orm import aliased
        a, b = aliased(FamilyRelationship), aliased(FamilyRelationship)
        return list(self.session.scalars(select(FamilyMember).join(a, a.child_id == FamilyMember.id)
            .join(b, b.child_id == FamilyMember.id).where(a.parent_id == one, b.parent_id == two)
            .order_by(FamilyMember.date_of_birth.asc().nulls_last(), FamilyMember.family_number)))

    def child_metadata(self, marriage_id):
        from models import MarriageChild
        return list(self.session.scalars(select(MarriageChild).where(MarriageChild.marriage_id == marriage_id)
                                        .order_by(MarriageChild.birth_order)))

    def ordered_children(self, marriage):
        shared = self.shared_children(marriage.spouse_one_id, marriage.spouse_two_id)
        ranks = {r.child_id: r.birth_order for r in self.child_metadata(marriage.id)} if marriage.id else {}
        return sorted(shared, key=lambda r: (ranks.get(r.id, float('inf')), r.date_of_birth is None,
                                             r.date_of_birth, r.family_number))

    def write_child_order(self, marriage_id, identities):
        from models import MarriageChild
        rows = self.child_metadata(marriage_id)
        # Move all old positions above the target range before swapping/inserting.
        offset = max([r.birth_order for r in rows] + [len(identities)]) + 1
        for row in rows:
            row.birth_order += offset
        self.session.flush()
        existing = {r.child_id: r for r in rows}
        for row in rows:
            if row.child_id not in identities:
                self.session.delete(row)
        for position, child in enumerate(identities, 1):
            row = existing.get(child)
            if row is None:
                row = MarriageChild(marriage_id=marriage_id, child_id=child)
                self.session.add(row)
            row.birth_order = position
        self.session.flush()
