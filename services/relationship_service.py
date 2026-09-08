from collections import defaultdict, deque
from models import FamilyRelationship, RelationshipType, Marriage, MarriageStatus
from repositories.relationship_repository import RelationshipRepository
from repositories.family_repository import FamilyRepository
from repositories.base import Repository
from services.base import Service, snapshot
from utils.validators import ValidationError


def descendants(edges, start):
    children = defaultdict(set)
    for parent, child in edges:
        children[parent].add(child)
    found, queue = set(), deque(children[start])
    while queue:
        member = queue.popleft()
        if member not in found:
            found.add(member)
            queue.extend(children[member] - found)
    return found


class RelationshipService(Service):
    def list(self):
        with self.transaction() as session:
            return [snapshot(row) for row in RelationshipRepository(session).list()]

    def save(self, parent_id, child_id, relationship_type, identity=None):
        if parent_id == child_id:
            raise ValidationError("A person cannot be their own parent")
        kind = RelationshipType(relationship_type)
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain("genealogy")
            for member in (parent_id, child_id):
                FamilyRepository(session).get(member)
            rows = [row for row in repo.list() if row.id != identity]
            if any(row.parent_id == parent_id and row.child_id == child_id for row in rows):
                raise ValidationError("Relationship already exists")
            if parent_id in descendants([(r.parent_id, r.child_id) for r in rows], child_id):
                raise ValidationError("This relationship would create an ancestry cycle")
            row = repo.get(identity, lock=True) if identity else FamilyRelationship()
            row.parent_id, row.child_id, row.relationship_type = parent_id, child_id, kind
            repo.add(row)
            self.audit(session, "UPDATE_RELATIONSHIP" if identity else "CREATE_RELATIONSHIP", row)
            return snapshot(row)

    def marriages(self, member_id=None):
        with self.transaction() as session:
            return [snapshot(row) for row in RelationshipRepository(session).marriages(member_id)]

    def save_marriage(self, spouse_one_id, spouse_two_id, status="MARRIED", identity=None, **values):
        if spouse_one_id == spouse_two_id:
            raise ValidationError("A person cannot marry themselves")
        if set(values) - {"marriage_date", "marriage_location", "notes"}:
            raise ValidationError("Unsupported marriage fields")
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain("genealogy")
            for member in (spouse_one_id, spouse_two_id):
                FamilyRepository(session).get(member)
            pair = {spouse_one_id, spouse_two_id}
            if any(row.id != identity and {row.spouse_one_id, row.spouse_two_id} == pair
                   and row.status in (MarriageStatus.MARRIED, MarriageStatus.SEPARATED)
                   for row in repo.marriages()):
                raise ValidationError("This couple already has a current marriage record")
            marriages = Repository(session, Marriage)
            row = marriages.get(identity, lock=True) if identity else Marriage()
            row.spouse_one_id, row.spouse_two_id, row.status = spouse_one_id, spouse_two_id, MarriageStatus(status)
            for key, value in values.items():
                setattr(row, key, value)
            marriages.add(row)
            self.audit(session, "UPDATE_MARRIAGE" if identity else "CREATE_MARRIAGE", row)
            return snapshot(row)

    def tree(self, member_id):
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            members = {row.id: snapshot(row) for row in FamilyRepository(session).list()}
            if member_id not in members:
                raise ValidationError("Member not found")
            edges = repo.edges()
            ancestors = descendants([(child, parent) for parent, child in edges], member_id)
            children = descendants(edges, member_id)
            parents = {parent for parent, child in edges if child == member_id}
            siblings = {child for parent, child in edges if parent in parents} - {member_id}
            spouses = {r.spouse_two_id if r.spouse_one_id == member_id else r.spouse_one_id
                       for r in repo.marriages(member_id)}
            return {"member": members[member_id],
                    "ancestors": [members[i] for i in ancestors],
                    "descendants": [members[i] for i in children],
                    "siblings": [members[i] for i in siblings], "spouses": [members[i] for i in spouses],
                    "edges": [{"parent_id": p, "child_id": c} for p, c in edges
                              if p in ancestors | children | {member_id} and c in ancestors | children | {member_id}]}
