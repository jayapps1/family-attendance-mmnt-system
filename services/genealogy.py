"""Pure, cycle-safe biological lineage traversal; no derived database rows."""
from collections import defaultdict, deque


def generation_label(sex, distance, *, ancestor):
    noun = ("father" if sex == "MALE" else "mother" if sex == "FEMALE" else "parent") if ancestor else (
        "son" if sex == "MALE" else "daughter" if sex == "FEMALE" else "child")
    if distance == 1:
        return noun.capitalize()
    return ("Great-" * max(0, distance - 2) + "grand" + noun).capitalize()


class Genealogy:
    def __init__(self, members, relationships):
        self.order_keys = {}
        self.members = members
        self.relationships = relationships
        self.parents, self.children = defaultdict(set), defaultdict(set)
        for row in relationships:
            if row["relationship_type"] in ("FATHER", "MOTHER"):
                self.parents[row["child_id"]].add(row["parent_id"])
                self.children[row["parent_id"]].add(row["child_id"])

    def depths(self, member_id, *, ancestors=False):
        graph = self.parents if ancestors else self.children
        seen, queue = {member_id: 0}, deque([member_id])
        while queue:
            current = queue.popleft()
            for relative in graph[current]:
                if relative not in seen:
                    seen[relative] = seen[current] + 1
                    queue.append(relative)
        seen.pop(member_id)
        return seen

    def relatives(self, member_id, *, ancestors=False):
        depths = self.depths(member_id, ancestors=ancestors)
        return [dict(self.members[identity], generation=depths[identity],
                     relationship_label=generation_label(self.members[identity]["sex"], depths[identity], ancestor=ancestors))
                for identity in sorted(depths, key=lambda i: (depths[i], self.order_keys.get(i, ("~", 0)), self.members[i].get("family_number", ""), str(i)))
                if identity in self.members]

    def siblings(self, member_id):
        ids = set().union(*(self.children[parent] for parent in self.parents[member_id])) - {member_id}
        return [dict(self.members[i], relationship_label="Brother" if self.members[i]["sex"] == "MALE" else "Sister")
                for i in sorted(ids, key=lambda i: (self.order_keys.get(i, ("~", 0)), self.members[i].get("family_number", str(i)))) if i in self.members]

    def summary(self, member_id):
        if member_id not in self.members:
            raise ValueError("Member not found")
        ancestors = self.relatives(member_id, ancestors=True)
        descendants = self.relatives(member_id)
        parents = [dict(self.members[r["parent_id"]], relationship_id=r["id"],
                        relationship_type=r["relationship_type"], relationship_label=r["relationship_type"].title())
                   for r in self.relationships if r["child_id"] == member_id]
        wards = [dict(self.members[r["child_id"]], relationship_id=r["id"], relationship_label="Ward")
                 for r in self.relationships if r["parent_id"] == member_id and r["relationship_type"] == "GUARDIAN"]
        visible = {member_id} | {r["id"] for r in ancestors + descendants}
        return dict(member=self.members[member_id], ancestors=ancestors, descendants=descendants,
                    parents=[r for r in parents if r["relationship_type"] != "GUARDIAN"],
                    guardians=[r for r in parents if r["relationship_type"] == "GUARDIAN"], wards=wards,
                    children=[r for r in descendants if r["generation"] == 1],
                    grandparents=[r for r in ancestors if r["generation"] == 2],
                    grandchildren=[r for r in descendants if r["generation"] == 2],
                    siblings=self.siblings(member_id),
                    edges=[r for r in self.relationships if r["relationship_type"] != "GUARDIAN"
                           and r["parent_id"] in visible and r["child_id"] in visible])
