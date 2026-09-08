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


from services.child_order import ChildOrderMixin


class RelationshipService(ChildOrderMixin, Service):
    def list(self):
        with self.transaction() as session:
            return [snapshot(row) for row in RelationshipRepository(session).list()]

    @staticmethod
    def _validate_rows(rows, parent_id, child_id, relationship_type):
        if parent_id == child_id:
            raise ValidationError("A person cannot be their own parent")
        if any(r.parent_id == parent_id and r.child_id == child_id for r in rows):
            raise ValidationError("This parent-child relationship already exists.")
        if relationship_type in (RelationshipType.FATHER, RelationshipType.MOTHER) and any(
                r.child_id == child_id and r.relationship_type == relationship_type for r in rows):
            raise ValidationError("This child already has a " + relationship_type.value.lower() + ". Edit or remove the existing relationship first.")
        if parent_id in descendants([(r.parent_id, r.child_id) for r in rows], child_id):
            raise ValidationError("Cannot create this relationship because it would create a genealogy cycle.")

    def _save(self, session, parent_id, child_id, relationship_type, identity=None):
        kind = RelationshipType(relationship_type)
        repo = RelationshipRepository(session)
        for member in (parent_id, child_id):
            FamilyRepository(session).get(member)
        rows = [row for row in repo.list() if row.id != identity]
        self._validate_rows(rows, parent_id, child_id, kind)
        row = repo.get(identity, lock=True) if identity else FamilyRelationship()
        row.parent_id, row.child_id, row.relationship_type = parent_id, child_id, kind
        repo.add(row)
        self._sync_child_orders(session)
        self.audit(session, "UPDATE_RELATIONSHIP" if identity else "CREATE_RELATIONSHIP", row)
        return snapshot(row)

    def save(self, parent_id, child_id, relationship_type, identity=None):
        with self.transaction() as session:
            RelationshipRepository(session).lock_domain("genealogy")
            return self._save(session, parent_id, child_id, relationship_type, identity)

    add_parent_child_relationship = save

    def validate_relationship(self, parent_id, child_id, relationship_type, identity=None):
        with self.transaction() as session:
            for member in (parent_id, child_id):
                FamilyRepository(session).get(member)
            rows = [r for r in RelationshipRepository(session).list() if r.id != identity]
            self._validate_rows(rows, parent_id, child_id, RelationshipType(relationship_type))
        return True

    def would_create_cycle(self, parent_id, child_id):
        with self.transaction() as session:
            return parent_id == child_id or parent_id in descendants(RelationshipRepository(session).edges(), child_id)

    def remove_relationship(self, identity):
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain("genealogy")
            row = repo.get(identity, lock=True)
            self.audit(session, "REMOVE_RELATIONSHIP", row, "Removed direct parent-child link")
            session.delete(row)
            session.flush()
            self._sync_child_orders(session)

    def link_relative(self, current_id, direction, relationship_type, *, existing_id=None,
                      new_member=None, second_parent_id=None, second_parent_type=None, media_root=None):
        """Save a new/existing relative and both parent links as one transaction."""
        from sqlalchemy.orm import sessionmaker
        from services.family_service import FamilyService
        from utils.profile_image import PreparedPhoto
        from utils.file_manager import FileManager
        if direction not in ("child", "parent") or (existing_id is None) == (new_member is None):
            raise ValidationError("Choose one existing member or provide one new member.")
        if second_parent_id and direction != "child":
            raise ValidationError("A second parent is only available when adding a child.")
        created_photo = None
        try:
            with self.transaction() as session:
                RelationshipRepository(session).lock_domain("genealogy")
                FamilyRepository(session).get(current_id)
                if new_member is not None:
                    nested = sessionmaker(bind=session.connection(), join_transaction_mode="create_savepoint")
                    family = FamilyService(nested, self.actor_id)
                    if isinstance(new_member.get("profile_image_path"), PreparedPhoto) and media_root is None:
                        raise ValidationError("A media folder is required for the profile photo.")
                    member = family.save_with_photo(new_member, media_root) if media_root is not None else family.create(**new_member)
                    if isinstance(new_member.get("profile_image_path"), PreparedPhoto):
                        created_photo = member["profile_image_path"]
                else:
                    member = snapshot(FamilyRepository(session).get(existing_id))
                parent, child = (current_id, member["id"]) if direction == "child" else (member["id"], current_id)
                self._save(session, parent, child, relationship_type)
                if second_parent_id:
                    if not second_parent_type:
                        raise ValidationError("Select the second parent's relationship type.")
                    self._save(session, second_parent_id, child, second_parent_type)
                return member
        except Exception:
            if created_photo:
                FileManager(media_root).discard_import(created_photo)
            raise

    @staticmethod
    def _couple(session, row):
        members = FamilyRepository(session)
        one, two = snapshot(members.get(row.spouse_one_id)), snapshot(members.get(row.spouse_two_id))
        from utils.family_labels import birth_label
        repo = RelationshipRepository(session)
        raw = repo.ordered_children(row)
        children = [dict(snapshot(child), birth_order=i, birth_position=birth_label(i, len(raw)))
                    for i, child in enumerate(raw, 1)]
        known_dates = [r['date_of_birth'] for r in children if r.get('date_of_birth')]
        warning = ('The recorded child order appears inconsistent with the dates of birth. Please review.'
                   if known_dates != sorted(known_dates) else '')
        name = lambda r: ' '.join(filter(None, [r['first_name'], r.get('middle_name'), r['last_name']]))
        return dict(snapshot(row), spouse_one=one, spouse_two=two,
                    couple_name=name(one) + ' & ' + name(two), children=children, child_count=len(children), order_warning=warning)

    def marriages(self, member_id=None):
        with self.transaction() as session:
            return [self._couple(session, row) for row in RelationshipRepository(session).marriages(member_id)]

    get_marriages_for_member = marriages

    def get_marriage(self, identity):
        with self.transaction() as session:
            return self._couple(session, Repository(session, Marriage).get(identity))

    def get_children_of_marriage(self, identity):
        return self.get_marriage(identity)['children']

    def get_shared_children(self, spouse_one_id, spouse_two_id):
        with self.transaction() as session:
            return self._couple(session, Marriage(spouse_one_id=spouse_one_id, spouse_two_id=spouse_two_id))['children']

    def child_links_for_marriage(self, identity, child_id):
        with self.transaction() as session:
            row = Repository(session, Marriage).get(identity)
            return [snapshot(r) for r in RelationshipRepository(session).list()
                    if r.child_id == child_id and r.parent_id in {row.spouse_one_id, row.spouse_two_id}]

    def add_child_to_marriage(self, identity, *, new_member=None, existing_id=None,
                              spouse_one_type='FATHER', spouse_two_type='MOTHER',
                              confirmed_links=None, media_root=None, birth_order=None):
        from sqlalchemy.orm import sessionmaker
        from services.family_service import FamilyService
        from utils.profile_image import PreparedPhoto
        from utils.file_manager import FileManager
        if (new_member is None) == (existing_id is None):
            raise ValidationError('Choose one new or existing child.')
        photo = None
        try:
            with self.transaction() as session:
                RelationshipRepository(session).lock_domain('genealogy')
                marriage = Repository(session, Marriage).get(identity, lock=True)
                if new_member is not None:
                    nested = sessionmaker(bind=session.connection(), join_transaction_mode='create_savepoint')
                    family = FamilyService(nested, self.actor_id)
                    if isinstance(new_member.get('profile_image_path'), PreparedPhoto) and media_root is None:
                        raise ValidationError('A media folder is required for the profile photo.')
                    member = family.save_with_photo(new_member, media_root) if media_root is not None else family.create(**new_member)
                    if isinstance(new_member.get('profile_image_path'), PreparedPhoto):
                        photo = member['profile_image_path']
                else:
                    member = snapshot(FamilyRepository(session).get(existing_id))
                links = [r for r in RelationshipRepository(session).list() if r.child_id == member['id']
                         and r.parent_id in {marriage.spouse_one_id, marriage.spouse_two_id}]
                if len(links) == 2:
                    raise ValidationError('This member is already registered as a child of this couple.')
                expected = {(str(r.id), r.relationship_type.value) for r in links}
                if links and set(confirmed_links or []) != expected:
                    raise ValidationError('Confirm the existing parent link before adding the missing link.')
                for parent, role in ((marriage.spouse_one_id, spouse_one_type), (marriage.spouse_two_id, spouse_two_type)):
                    existing = next((r for r in links if r.parent_id == parent), None)
                    if existing:
                        if existing.relationship_type.value != role:
                            raise ValidationError('The existing parent role must remain unchanged. Edit the relationship separately.')
                    else:
                        self._save(session, parent, member['id'], role)
                repo = RelationshipRepository(session)
                children = [r.id for r in repo.ordered_children(marriage) if r.id != member['id']]
                position = len(children)+1 if birth_order is None else self._position(birth_order, len(children)+1)
                children.insert(position-1, member['id'])
                repo.write_child_order(marriage.id, children)
                if existing_id is not None:
                    self.audit(session, 'LINK_EXISTING_CHILD', marriage, str(member['id']))
                self.audit(session, 'ADD_CHILD_TO_MARRIAGE', marriage, 'Linked child ' + str(member['id']))
                member['order_warning'] = self._couple(session, marriage)['order_warning']
                return member
        except Exception:
            if photo:
                FileManager(media_root).discard_import(photo)
            raise

    def link_existing_child_to_marriage(self, identity, child_id, **values):
        return self.add_child_to_marriage(identity, existing_id=child_id, **values)

    def delete_marriage(self, identity):
        with self.transaction() as session:
            RelationshipRepository(session).lock_domain('genealogy')
            row = Repository(session, Marriage).get(identity, lock=True)
            self.audit(session, 'DELETE_MARRIAGE', row, 'Removed marriage only; members and parent-child links preserved')
            session.delete(row)

    delete_parent_child_relationship = remove_relationship

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
            self._sync_child_orders(session)
            self.audit(session, "UPDATE_MARRIAGE" if identity else "CREATE_MARRIAGE", row)
            return snapshot(row)

    @staticmethod
    def graph(session):
        from services.genealogy import Genealogy
        from utils.date_utils import age_on
        members = {row.id: dict(snapshot(row), age=age_on(row.date_of_birth, row.date_of_death))
                   for row in FamilyRepository(session).list()}
        graph = Genealogy(members, [snapshot(row) for row in RelationshipRepository(session).list()])
        graph.order_keys = {}
        positions = defaultdict(list)
        for marriage in sorted(RelationshipRepository(session).marriages(), key=lambda r: (r.marriage_date is None, r.marriage_date, str(r.id))):
            couple = RelationshipService._couple(session, marriage)
            for child in couple['children']:
                positions[child['id']].append(couple['couple_name'] + ': ' + child['birth_position'])
                graph.order_keys.setdefault(child['id'], (str(marriage.id), child['birth_order']))
        for identity, labels in positions.items():
            graph.members[identity]['birth_position'] = '; '.join(labels)
        return graph

    def tree(self, member_id):
        with self.transaction() as session:
            graph = self.graph(session)
            result = graph.summary(member_id)
            marriages = RelationshipRepository(session).marriages(member_id)
            spouses = {r.spouse_two_id if r.spouse_one_id == member_id else r.spouse_one_id for r in marriages}
            result["spouses"] = [dict(graph.members[i], relationship_label="Spouse") for i in sorted(spouses, key=str)]
            visible = {member_id} | {r["id"] for r in result["ancestors"] + result["descendants"]}
            co_parents = {r["parent_id"] for r in graph.relationships if r["relationship_type"] != "GUARDIAN"
                          and r["child_id"] in visible} - visible
            result["co_parents"] = [dict(graph.members[i], relationship_label="Co-parent (outside lineage)") for i in sorted(co_parents, key=str)]
            result["edges"] = [r for r in graph.relationships if r["relationship_type"] != "GUARDIAN"
                               and r["child_id"] in visible and r["parent_id"] in visible | co_parents]
            result["child_order"] = graph.order_keys
            result["marriages"] = [snapshot(r) for r in RelationshipRepository(session).marriages()]
            return result

    def get_parents(self, member_id): return self.tree(member_id)["parents"]
    def get_guardians(self, member_id): return self.tree(member_id)["guardians"]
    def get_children(self, member_id): return self.tree(member_id)["children"]
    def get_siblings(self, member_id): return self.tree(member_id)["siblings"]
    def get_grandparents(self, member_id): return self.tree(member_id)["grandparents"]
    def get_grandchildren(self, member_id): return self.tree(member_id)["grandchildren"]
    def get_ancestors(self, member_id): return self.tree(member_id)["ancestors"]
    def get_descendants(self, member_id): return self.tree(member_id)["descendants"]

    def get_father(self, member_id):
        return next((r for r in self.get_parents(member_id) if r["relationship_type"] == "FATHER"), None)

    def get_mother(self, member_id):
        return next((r for r in self.get_parents(member_id) if r["relationship_type"] == "MOTHER"), None)

    def get_generation_distance(self, ancestor_id, descendant_id):
        with self.transaction() as session:
            graph = self.graph(session)
            if ancestor_id not in graph.members or descendant_id not in graph.members:
                raise ValidationError("Member not found")
            return 0 if ancestor_id == descendant_id else graph.depths(ancestor_id).get(descendant_id)

    def get_relationship_between(self, member_a_id, member_b_id):
        """Return A's relationship to B, using shortest biological generation distance."""
        from services.genealogy import generation_label
        with self.transaction() as session:
            graph = self.graph(session)
            if member_a_id not in graph.members or member_b_id not in graph.members:
                raise ValidationError("Member not found")
            if member_a_id == member_b_id:
                return "Self"
            sex = graph.members[member_a_id]["sex"]
            for row in graph.relationships:
                if row["parent_id"] == member_a_id and row["child_id"] == member_b_id:
                    return row["relationship_type"].title()
                if row["parent_id"] == member_b_id and row["child_id"] == member_a_id and row["relationship_type"] == "GUARDIAN":
                    return "Ward"
            depth = graph.depths(member_b_id, ancestors=True).get(member_a_id)
            if depth:
                return generation_label(sex, depth, ancestor=True)
            depth = graph.depths(member_b_id).get(member_a_id)
            if depth:
                return generation_label(sex, depth, ancestor=False)
            if member_a_id in {r["id"] for r in graph.siblings(member_b_id)}:
                return "Brother" if sex == "MALE" else "Sister"
            a_ancestors = graph.depths(member_a_id, ancestors=True)
            b_ancestors = graph.depths(member_b_id, ancestors=True)
            common = set(a_ancestors) & set(b_ancestors)
            if common:
                root = min(common, key=lambda i: (a_ancestors[i]+b_ancestors[i], max(a_ancestors[i], b_ancestors[i]), str(i)))
                a, b = a_ancestors[root], b_ancestors[root]
                if a == 1:
                    return ("Great-" * (b-2) + ("uncle" if sex == "MALE" else "aunt")).capitalize()
                if b == 1:
                    return ("Great-" * (a-2) + ("nephew" if sex == "MALE" else "niece")).capitalize()
                degree, removed = min(a,b)-1, abs(a-b)
                label = {1: "First", 2: "Second", 3: "Third"}.get(degree, f"Degree {degree}") + " cousin"
                if removed:
                    label += f", {removed} generation(s) removed"
                return label
            if any({r.spouse_one_id, r.spouse_two_id} == {member_a_id, member_b_id}
                   for r in RelationshipRepository(session).marriages(member_a_id)):
                return "Spouse (marriage history)"
            return "No known direct-line relationship"

    def create_spouse_and_marriage(self, current_id, new_member, *, media_root=None, **marriage_values):
        from sqlalchemy.orm import sessionmaker
        from services.family_service import FamilyService
        from utils.profile_image import PreparedPhoto
        from utils.file_manager import FileManager
        photo = None
        values = dict(new_member)
        values.setdefault('affiliation_type', 'MARRIED_IN')
        try:
            with self.transaction() as session:
                RelationshipRepository(session).lock_domain('genealogy')
                FamilyRepository(session).get(current_id)
                nested = sessionmaker(bind=session.connection(), join_transaction_mode='create_savepoint')
                family = FamilyService(nested, self.actor_id)
                if isinstance(values.get('profile_image_path'), PreparedPhoto) and media_root is None:
                    raise ValidationError('A media folder is required for the profile photo.')
                member = family.save_with_photo(values, media_root) if media_root is not None else family.create(**values)
                if isinstance(values.get('profile_image_path'), PreparedPhoto):
                    photo = member['profile_image_path']
                return RelationshipService(nested, self.actor_id).save_marriage(current_id, member['id'], **marriage_values)
        except Exception:
            if photo:
                FileManager(media_root).discard_import(photo)
            raise
