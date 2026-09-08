import pytest
from PIL import Image
from services.family_service import FamilyService
from services.relationship_service import RelationshipService
from services.branch_service import BranchService
from services.genealogy import Genealogy, generation_label
from utils.profile_image import prepare_portrait
from tests.service_helpers import service_context


def family_chain(context):
    family, links = FamilyService(*context), RelationshipService(*context)
    members = [family.create(first_name=name, last_name="Arthur", sex=sex)
               for name, sex in (("Akosua", "FEMALE"), ("Ama", "FEMALE"), ("Abena", "FEMALE"), ("Kwame", "MALE"))]
    for parent, child in zip(members, members[1:]):
        links.save(parent["id"], child["id"], "MOTHER")
    return family, links, members


def test_four_generations_and_relationship_direction(db):
    family, links, people = family_chain(service_context(db))
    a, b, c, d = [p["id"] for p in people]
    assert links.get_relationship_between(a, b) == "Mother"
    assert links.get_relationship_between(a, c) == "Grandmother"
    assert links.get_relationship_between(a, d) == "Great-grandmother"
    assert links.get_relationship_between(d, a) == "Great-grandson"
    assert links.get_relationship_between(c, a) == "Granddaughter"
    assert links.get_relationship_between(b, a) == "Daughter"
    assert links.get_generation_distance(a, d) == 3
    assert links.get_generation_distance(d, a) is None
    assert links.get_generation_distance(a, a) == 0
    assert links.get_mother(d)["id"] == c
    assert links.get_father(d) is None
    assert [r["id"] for r in links.get_grandparents(d)] == [b]
    assert [r["id"] for r in links.get_grandchildren(a)] == [c]
    assert len([r for r in links.list() if r["parent_id"] in {a,b,c,d}]) == 3


def test_guardians_are_not_bloodline_and_siblings_deduplicate(db):
    context = service_context(db)
    family, links, people = family_chain(context)
    mother, child = people[2], people[3]
    father = family.create(first_name="Kofi", last_name="Arthur", sex="MALE")
    sibling = family.create(first_name="Sena", last_name="Arthur", sex="FEMALE")
    guardian = family.create(first_name="Guardian", last_name="Arthur", sex="FEMALE")
    links.save(father["id"], child["id"], "FATHER")
    links.save(father["id"], sibling["id"], "FATHER")
    links.save(mother["id"], sibling["id"], "MOTHER")
    links.save(guardian["id"], child["id"], "GUARDIAN")
    assert [r["id"] for r in links.get_siblings(child["id"])] == [sibling["id"]]
    assert links.get_relationship_between(sibling["id"], child["id"]) == "Sister"
    assert links.get_relationship_between(guardian["id"], child["id"]) == "Guardian"
    assert links.get_descendants(guardian["id"]) == []
    assert links.get_guardians(child["id"])[0]["id"] == guardian["id"]
    assert guardian["id"] not in {r["id"] for r in links.get_ancestors(child["id"])}


def test_parent_validation_edits_removal_and_cycles(db):
    context = service_context(db)
    family, links, people = family_chain(context)
    a,b,c,d = [r["id"] for r in people]
    extra = family.create(first_name="Other", last_name="Parent", sex="FEMALE")["id"]
    with pytest.raises(ValueError, match="already has a mother"):
        links.save(extra, d, "MOTHER")
    with pytest.raises(ValueError, match="already exists"):
        links.save(c, d, "MOTHER")
    with pytest.raises(ValueError, match="cycle"):
        links.save(d, a, "FATHER")
    with pytest.raises(ValueError):
        links.save(a, a, "GUARDIAN")
    assert links.would_create_cycle(d, a)
    relation = next(r for r in links.list() if r["parent_id"] == c and r["child_id"] == d)
    links.save(c, d, "GUARDIAN", identity=relation["id"])
    assert links.get_mother(d) is None
    assert links.get_relationship_between(c,d) == "Guardian"
    links.save(extra,d,"MOTHER")
    links.remove_relationship(relation["id"])
    assert links.get_guardians(d) == []


def test_new_child_second_parent_atomic_and_photo_cleanup(db, tmp_path):
    context = service_context(db)
    family, links = FamilyService(*context), RelationshipService(*context)
    mother = family.create(first_name="Mother", last_name="Atomic", sex="FEMALE")
    father = family.create(first_name="Father", last_name="Atomic", sex="MALE")
    photo = prepare_portrait(Image.new("RGB",(400,600),"teal"))
    child = links.link_relative(mother["id"], "child", "MOTHER",
        new_member=dict(first_name="Child",last_name="Atomic",sex="FEMALE", profile_image_path=photo),
        second_parent_id=father["id"],second_parent_type="FATHER",media_root=tmp_path)
    assert links.get_mother(child["id"])["id"] == mother["id"]
    assert links.get_father(child["id"])["id"] == father["id"]
    before_ids = {r["id"] for r in family.list()}
    before_photos = set(tmp_path.rglob("*.jpg"))
    with pytest.raises(ValueError, match="already has a mother"):
        links.link_relative(mother["id"], "child", "MOTHER",
            new_member=dict(first_name="Rejected", last_name="Atomic",sex="MALE",profile_image_path=photo),
            second_parent_id=father["id"],second_parent_type="MOTHER",media_root=tmp_path)
    assert {r["id"] for r in family.list()} == before_ids
    assert set(tmp_path.rglob("*.jpg")) == before_photos
    with pytest.raises(ValueError, match="cycle"):
        links.link_relative(child["id"], "child", "GUARDIAN", existing_id=mother["id"])


def test_new_and_existing_parent_workflows(db):
    context = service_context(db)
    family, links = FamilyService(*context), RelationshipService(*context)
    child = family.create(first_name="Child", last_name="ParentFlow",sex="MALE")
    mother = links.link_relative(child["id"], "parent", "MOTHER",
                               new_member=dict(first_name="New",last_name="Mother",sex="FEMALE"))
    father = family.create(first_name="Existing",last_name="Father",sex="MALE")
    links.link_relative(child["id"],"parent","FATHER",existing_id=father["id"])
    assert links.get_mother(child["id"])["id"] == mother["id"]
    assert links.get_father(child["id"])["id"] == father["id"]


def test_branches_inherit_multiple_lineages_and_exclude_spouses(db):
    context = service_context(db)
    family, links, people = family_chain(context)
    branches = BranchService(*context)
    first = branches.save("First " + str(people[0]["id"]), people[0]["id"])
    second = branches.save("Second " + str(people[1]["id"]), people[1]["id"])
    spouse = family.create(first_name="Spouse",last_name="Outside",sex="FEMALE")
    links.save_marriage(people[3]["id"],spouse["id"])
    child = links.link_relative(people[3]["id"],"child","FATHER",
                               new_member=dict(first_name="Sena",last_name="Arthur",sex="FEMALE",phone_number="0249991234",current_residence="Kumasi"))
    rows = branches.get_branch_members(first["id"])
    assert len(rows) == 5
    assert {r["member"]["id"] for r in rows} == {r["id"] for r in people} | {child["id"]}
    assert next(r["generation"] for r in rows if r["member"]["id"] == child["id"]) == 4
    assert {r["id"] for r in branches.get_member_branches(child["id"])} == {first["id"],second["id"]}
    assert branches.get_member_branches(spouse["id"]) == []
    assert branches.details(first["id"])["spouses"][0]["id"] == spouse["id"]
    assert branches.details(first["id"])["generations"] == 4
    assert branches.details(first["id"])["direct_children"] == 1
    for term in ("Sena","0249991234","Kumasi",child["family_number"]):
        assert branches.get_branch_members(first["id"],term)[0]["member"]["id"] == child["id"]
    assert {r["id"] for r in family.list(branch_id=first["id"])} == {r["member"]["id"] for r in rows}
    branches.save(first["name"],people[1]["id"],is_active=False,identity=first["id"])
    assert branches.details(first["id"])["descendants"] == 3
    with pytest.raises(ValueError, match="founding member"):
        branches.save("No founder",None)


def test_unlimited_generation_depth_and_pedigree_deduplication():
    members = {i:dict(id=i,sex="FEMALE",family_number=str(i),first_name="Member",last_name=str(i)) for i in range(1200)}
    edges = [dict(id=i,parent_id=i,child_id=i+1,relationship_type="MOTHER") for i in range(1199)]
    graph=Genealogy(members,edges)
    assert graph.depths(0)[1199] == 1199
    assert len(graph.relatives(0)) == 1199
    assert generation_label("FEMALE",4,ancestor=True) == "Great-great-grandmother"
    diamond=Genealogy({i:members[i] for i in range(4)},[
        dict(id=0,parent_id=0,child_id=1,relationship_type="MOTHER"),
        dict(id=1,parent_id=0,child_id=2,relationship_type="MOTHER"),
        dict(id=2,parent_id=1,child_id=3,relationship_type="MOTHER"),
        dict(id=3,parent_id=2,child_id=3,relationship_type="FATHER")])
    assert diamond.depths(0) == {1:1,2:1,3:2}
    assert len(diamond.relatives(0)) == 3
    from ui.family.family_tree import generation_layout
    data=diamond.summary(0)
    nodes, edges, positions=generation_layout(data,True)
    assert len(nodes)==len(positions)==4
    assert all(positions[r["child_id"]][1]>positions[r["parent_id"]][1] for r in edges)


def test_collateral_relatives_and_two_parent_tree(db):
    context = service_context(db)
    family, links, people = family_chain(context)
    aunt = family.create(first_name="Aunt",last_name="Arthur",sex="FEMALE")
    links.save(people[1]["id"],aunt["id"],"MOTHER")
    assert links.get_relationship_between(aunt["id"],people[3]["id"]) == "Aunt"
    assert links.get_relationship_between(people[3]["id"],aunt["id"]) == "Nephew"
    cousin = links.link_relative(aunt["id"],"child","MOTHER",new_member=dict(first_name="Cousin",last_name="Arthur",sex="MALE"))
    assert links.get_relationship_between(cousin["id"],people[3]["id"]) == "First cousin"
    father=family.create(first_name="Other",last_name="Father",sex="MALE")
    links.save(father["id"],people[3]["id"],"FATHER")
    tree=links.tree(people[0]["id"])
    assert father["id"] in {r["id"] for r in tree["co_parents"]}
    from ui.family.family_tree import generation_layout
    nodes, edges, positions=generation_layout(tree)
    assert positions[father["id"]][1] == positions[people[2]["id"]][1]
    assert father["id"] not in generation_layout(tree,True)[0]
