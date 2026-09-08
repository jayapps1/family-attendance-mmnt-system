import pytest
from services.family_service import FamilyService
from services.relationship_service import RelationshipService
from tests.service_helpers import service_context


def setup_couple(db):
    context = service_context(db)
    family, links = FamilyService(*context), RelationshipService(*context)
    james = family.create(first_name='James', last_name='Appiah-Gyachie', sex='MALE')
    agnes = family.create(first_name='Agnes', last_name='Ampoful', sex='FEMALE')
    marriage = links.save_marriage(james['id'], agnes['id'])
    return family, links, james, agnes, marriage


def test_exact_couple_scenario(db):
    family, links, james, agnes, marriage = setup_couple(db)
    before = len(family.list())
    michael = links.add_child_to_marriage(marriage['id'], new_member=dict(first_name='Michael', last_name='Appiah-Gyachie', sex='MALE'))
    assert len(family.list()) == before + 1
    assert links.get_father(michael['id'])['id'] == james['id']
    assert links.get_mother(michael['id'])['id'] == agnes['id']
    for parent in (james, agnes):
        assert michael['id'] in {c['id'] for c in links.get_children(parent['id'])}
    assert links.get_marriage(marriage['id'])['child_count'] == 1
    janet = links.add_child_to_marriage(marriage['id'], new_member=dict(first_name='Janet', last_name='Appiah-Gyachie', sex='FEMALE'))
    original_links = links.list()
    links.delete_marriage(marriage['id'])
    assert len(links.list()) == len(original_links)
    assert {james['id'], agnes['id'], michael['id'], janet['id']} <= {p['id'] for p in family.list()}
    marriage = links.save_marriage(james['id'], agnes['id'])
    assert links.get_marriage(marriage['id'])['child_count'] == 2
    link = next(r for r in links.list() if r['child_id'] == michael['id'] and r['parent_id'] == james['id'])
    links.delete_parent_child_relationship(link['id'])
    assert links.get_marriage(marriage['id'])['child_count'] == 1
    assert michael['id'] in {p['id'] for p in family.list()}


def test_existing_partial_duplicate_and_remarriage(db):
    family, links, james, agnes, marriage = setup_couple(db)
    child = family.create(first_name='Existing', last_name='Child', sex='FEMALE')
    first = links.save(james['id'], child['id'], 'FATHER')
    with pytest.raises(ValueError, match='Confirm'):
        links.link_existing_child_to_marriage(marriage['id'], child['id'])
    links.link_existing_child_to_marriage(marriage['id'], child['id'], confirmed_links=[(str(first['id']), 'FATHER')])
    with pytest.raises(ValueError, match='already registered'):
        links.link_existing_child_to_marriage(marriage['id'], child['id'])
    other = family.create(first_name='Other', last_name='Spouse', sex='FEMALE')
    second = links.save_marriage(james['id'], other['id'])
    assert links.get_children_of_marriage(second['id']) == []
    assert len(links.get_shared_children(james['id'], agnes['id'])) == 1
    links.save_marriage(james['id'], agnes['id'], status='DIVORCED', identity=marriage['id'])
    assert links.get_marriage(marriage['id'])['child_count'] == 1


def test_atomic_failure_cycle_and_safe_delete(db):
    family, links, james, agnes, marriage = setup_couple(db)
    count = len(family.list())
    with pytest.raises(ValueError, match='already has a father'):
        links.add_child_to_marriage(marriage['id'], spouse_two_type='FATHER', new_member=dict(first_name='Rollback', last_name='Child', sex='MALE'))
    assert len(family.list()) == count
    with pytest.raises(ValueError):
        links.link_existing_child_to_marriage(marriage['id'], james['id'])
    ancestor = family.create(first_name='Ancestor', last_name='Parent', sex='MALE')
    links.save(ancestor['id'], james['id'], 'FATHER')
    with pytest.raises(ValueError, match='cycle'):
        links.link_existing_child_to_marriage(marriage['id'], ancestor['id'])
    with pytest.raises(ValueError, match='Archive the member instead'):
        family.delete_permanently(james['id'])
    family.archive(james['id'])
    assert next(r for r in family.list() if r['id'] == james['id'])['is_active'] is False


def test_permanent_delete_only_unreferenced_members(db):
    import uuid
    from models import FamilyMember, FamilyBranch, Sex
    context = service_context(db)
    family = FamilyService(*context)
    clean = FamilyMember(family_number='DELETE-' + uuid.uuid4().hex[:12], first_name='Unreferenced', last_name='Import', sex=Sex.MALE)
    db.add(clean); db.flush()
    identity = clean.id
    family.delete_permanently(identity)
    assert identity not in {r['id'] for r in family.list()}
    founder = FamilyMember(family_number='KEEP-' + uuid.uuid4().hex[:12], first_name='Referenced', last_name='Import', sex=Sex.MALE)
    db.add(founder); db.flush()
    db.add(FamilyBranch(name='Protected ' + uuid.uuid4().hex, founding_member_id=founder.id)); db.flush()
    with pytest.raises(ValueError, match='historical records'):
        family.delete_permanently(founder.id)
