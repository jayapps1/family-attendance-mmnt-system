"""Branches are founder-rooted biological lineages, never membership rows."""
from models import FamilyBranch
from repositories.base import Repository
from repositories.family_repository import FamilyRepository
from repositories.relationship_repository import RelationshipRepository
from services.base import Service, snapshot
from services.relationship_service import RelationshipService
from utils.validators import ValidationError, required


class BranchService(Service):
    def save(self, name, founding_member_id, description=None, is_active=True, identity=None):
        if founding_member_id is None:
            raise ValidationError("Select a founding member for this branch.")
        with self.transaction() as session:
            repo = Repository(session, FamilyBranch)
            repo.lock_domain("genealogy")
            FamilyRepository(session).get(founding_member_id)
            row = repo.get(identity, lock=True) if identity else FamilyBranch()
            row.name = required(name, "Branch name", 150)
            row.founding_member_id, row.description, row.is_active = founding_member_id, description, bool(is_active)
            repo.add(row)
            self.audit(session, "UPDATE_BRANCH" if identity else "CREATE_BRANCH", row)
            return snapshot(row)

    def list(self, search="", active=None):
        with self.transaction() as session:
            graph = RelationshipService.graph(session)
            rows = []
            for branch in Repository(session, FamilyBranch).list():
                founder = graph.members.get(branch.founding_member_id)
                label = self.name(founder) if founder else "Founder missing - edit branch"
                if active is not None and branch.is_active != active:
                    continue
                if search and search.casefold() not in (branch.name + " " + label).casefold():
                    continue
                rows.append(dict(snapshot(branch), founder=label,
                                 descendant_count=len(graph.depths(branch.founding_member_id)) if founder else 0,
                                 status="ACTIVE" if branch.is_active else "INACTIVE"))
            return sorted(rows, key=lambda row: row["name"].casefold())

    @staticmethod
    def name(member):
        return member["family_number"] + " - " + " ".join(filter(None, (member["first_name"], member.get("middle_name"), member["last_name"])))

    @staticmethod
    def lineage(graph, founder_id):
        if founder_id not in graph.members:
            raise ValidationError("This branch needs a valid founding member. Edit the branch first.")
        return [dict(graph.members[founder_id], generation=0, relationship_label="Founder"), *graph.relatives(founder_id)]

    def get_branch_members(self, branch_id, search=""):
        with self.transaction() as session:
            branch = Repository(session, FamilyBranch).get(branch_id)
            graph = RelationshipService.graph(session)
            rows = self.lineage(graph, branch.founding_member_id)
            term = search.casefold().strip()
            if term:
                rows = [row for row in rows if term in " ".join(str(row.get(k) or "") for k in
                        ("family_number", "first_name", "middle_name", "last_name", "phone_number", "current_residence")).casefold()]
            return [{"member": row, "generation": row["generation"]} for row in rows]

    def details(self, branch_id):
        with self.transaction() as session:
            branch = Repository(session, FamilyBranch).get(branch_id)
            graph = RelationshipService.graph(session)
            rows = self.lineage(graph, branch.founding_member_id)
            ids = {r["id"] for r in rows}
            spouses = set()
            for marriage in RelationshipRepository(session).marriages():
                if marriage.spouse_one_id in ids:
                    spouses.add(marriage.spouse_two_id)
                if marriage.spouse_two_id in ids:
                    spouses.add(marriage.spouse_one_id)
            associated = []
            for marriage in RelationshipRepository(session).marriages():
                for person, anchor in ((marriage.spouse_one_id, marriage.spouse_two_id), (marriage.spouse_two_id, marriage.spouse_one_id)):
                    if anchor in ids and person not in ids and person not in {r['id'] for r in associated}:
                        associated.append(dict(graph.members[person], spouse_anchor=anchor, relationship_label='Spouse (outside lineage)'))
            tree = dict(member=rows[0], ancestors=[], descendants=rows[1:], siblings=[], spouses=associated, associated_spouses=associated, child_order=graph.order_keys, marriages=[snapshot(r) for r in RelationshipRepository(session).marriages()],
                        edges=[r for r in graph.relationships if r["relationship_type"] != "GUARDIAN"
                               and r["parent_id"] in ids | spouses and r["child_id"] in ids])
            return dict(branch=snapshot(branch), founder=rows[0], members=rows, tree=tree,
                        direct_children=len(graph.children[branch.founding_member_id]),
                        descendants=len(rows)-1, generations=max(r["generation"] for r in rows),
                        married_in_members=sum(graph.members[i].get('affiliation_type') == 'MARRIED_IN' for i in ids | spouses),
                        total_associated_members=len(ids | spouses),
                        lineage_members=len(rows), living=sum(r["living_status"] == "LIVING" for r in rows),
                        deceased=sum(r["living_status"] == "DECEASED" for r in rows),
                        spouses=[graph.members[i] for i in sorted(spouses - ids, key=str)])

    def get_member_branches(self, member_id):
        with self.transaction() as session:
            graph = RelationshipService.graph(session)
            if member_id not in graph.members:
                raise ValidationError("Member not found")
            ancestors = graph.depths(member_id, ancestors=True)
            return [dict(snapshot(branch), generation=0 if branch.founding_member_id == member_id else ancestors[branch.founding_member_id])
                    for branch in Repository(session, FamilyBranch).list()
                    if branch.founding_member_id == member_id or branch.founding_member_id in ancestors]
