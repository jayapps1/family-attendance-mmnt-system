from datetime import date
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from models import MarriageChild
from services.family_service import FamilyService
from services.relationship_service import RelationshipService
from services.branch_service import BranchService
from services.contribution_service import ContributionService
from services.report_service import ReportService
from tests.service_helpers import service_context
from utils.family_labels import ordinal


@pytest.mark.parametrize('number,label', [(1,'1st Child'),(2,'2nd Child'),(3,'3rd Child'),(4,'4th Child'),(11,'11th Child'),(12,'12th Child'),(13,'13th Child'),(21,'21st Child'),(22,'22nd Child'),(101,'101st Child')])
def test_ordinals(number, label):
    assert ordinal(number) == label


def scenario(db):
    context = service_context(db)
    family, links = FamilyService(*context), RelationshipService(*context)
    james = family.create(first_name='James', last_name='Appiah-Gyachie', sex='MALE', affiliation_type='LINEAGE_MEMBER')
    agnes = family.create(first_name='Agnes', last_name='Ampoful', sex='FEMALE', affiliation_type='MARRIED_IN')
    marriage = links.save_marriage(james['id'], agnes['id'])
    return context, family, links, james, agnes, marriage


def test_order_insert_reorder_profiles_tree_branch_and_delete(db):
    context, family, links, james, agnes, marriage = scenario(db)
    branch = BranchService(*context).save('Order branch ' + str(james['id']), james['id'])
    children = {}
    for name, position, year in [('Michael',1,1998),('Janet',2,2000),('Grace',3,2004),('Daniel',3,2002)]:
        children[name] = links.add_child_to_marriage(marriage['id'], birth_order=position,
            new_member=dict(first_name=name, last_name='Appiah-Gyachie', sex='MALE' if name in ('Michael','Daniel') else 'FEMALE', date_of_birth=date(year,1,1)))
        if name == 'Michael':
            assert links.get_children_of_marriage(marriage['id'])[0]['birth_position'] == '1st Child - Only child'
            assert links.get_next_birth_order(marriage['id']) == 2
    names = ['Michael','Janet','Daniel','Grace']
    ordered = links.get_children_of_marriage(marriage['id'])
    assert [r['first_name'] for r in ordered] == names
    assert [r['birth_order'] for r in ordered] == [1,2,3,4]
    assert ordered[0]['birth_position'].endswith('Firstborn')
    assert ordered[-1]['birth_position'].endswith('Last-born')
    for child in children.values():
        assert child['affiliation_type'] == 'LINEAGE_MEMBER'
        assert links.get_father(child['id'])['id'] == james['id']
        assert links.get_mother(child['id'])['id'] == agnes['id']
    for parent in (james, agnes):
        assert [r['first_name'] for r in links.get_children(parent['id'])] == names
    from ui.family.family_tree import generation_layout
    tree = links.tree(james['id'])
    members, edges, positions = generation_layout(tree)
    assert len(members) == 6
    assert [members[i]['first_name'] for i in sorted([c['id'] for c in children.values()], key=lambda i: positions[i][0])] == names
    assert 'Firstborn' in links.tree(children['Michael']['id'])['member']['birth_position']
    details = BranchService(*context).details(branch['id'])
    assert details['descendants'] == 4 and details['lineage_members'] == 5
    assert details['married_in_members'] == 1 and details['total_associated_members'] == 6
    bm, _, bp = generation_layout(details['tree'], True)
    assert agnes['id'] in bm and bp[agnes['id']][1] == bp[james['id']][1]
    ids = [c['id'] for c in ordered]
    changed = links.set_child_birth_order(marriage['id'], children['Grace']['id'], 1)
    assert changed['children'][0]['first_name'] == 'Grace' and changed['order_warning']
    with pytest.raises(ValueError, match='changed'):
        links.reorder_children(marriage['id'], ids, expected_order=ids)
    links.reorder_children(marriage['id'], ids)
    assert not links.get_marriage(marriage['id'])['order_warning']
    assert len(db.scalars(select(MarriageChild).where(MarriageChild.marriage_id == marriage['id'])).all()) == 4
    links.delete_marriage(marriage['id'])
    assert not db.scalars(select(MarriageChild).where(MarriageChild.marriage_id == marriage['id'])).all()
    assert {james['id'],agnes['id'],*ids} <= {r['id'] for r in family.list()}
    assert len([r for r in links.list() if r['child_id'] in ids]) == 8


def test_invalid_order_partial_links_remarriage_and_affiliation(db):
    context, family, links, james, agnes, marriage = scenario(db)
    before = len(family.list())
    for value in (0, -1, 2, 1.5, True):
        with pytest.raises(ValueError, match='Birth order'):
            links.add_child_to_marriage(marriage['id'], birth_order=value, new_member=dict(first_name='Rollback', last_name='Child', sex='MALE'))
        assert len(family.list()) == before
    michael = links.add_child_to_marriage(marriage['id'], new_member=dict(first_name='Michael', last_name='Child', sex='MALE'))
    another = links.create_spouse_and_marriage(james['id'], dict(first_name='Adwoa', last_name='Other', sex='FEMALE'))
    spouse = next(r for r in family.list() if r['id'] == another['spouse_two_id'])
    assert spouse['affiliation_type'] == 'MARRIED_IN'
    daniel = links.add_child_to_marriage(another['id'], new_member=dict(first_name='Daniel', last_name='Child', sex='MALE'))
    assert [r['id'] for r in links.get_children_of_marriage(marriage['id'])] == [michael['id']]
    assert links.get_children_of_marriage(another['id'])[0]['birth_order'] == 1
    assert daniel['id'] != michael['id']
    with pytest.raises(ValueError):
        links.reorder_children(marriage['id'], [michael['id'], michael['id']])
    first = next(r for r in links.list() if r['parent_id'] == james['id'] and r['child_id'] == michael['id'])
    links.remove_relationship(first['id'])
    assert links.get_children_of_marriage(marriage['id']) == []
    assert not db.scalars(select(MarriageChild).where(MarriageChild.marriage_id == marriage['id'])).all()
    mother = next(r for r in links.list() if r['child_id'] == michael['id'])
    links.link_existing_child_to_marriage(marriage['id'], michael['id'], confirmed_links=[(str(mother['id']), 'MOTHER')], birth_order=1)
    assert links.get_children_of_marriage(marriage['id'])[0]['birth_order'] == 1
    assert agnes['id'] in {r['id'] for r in family.list(affiliation_type='MARRIED_IN')}
    assert james['id'] not in {r['id'] for r in family.list(affiliation_type='MARRIED_IN')}
    family.update(agnes['id'], affiliation_type='LINEAGE_MEMBER')
    assert agnes['id'] in {r['id'] for r in family.list(affiliation_type='LINEAGE_MEMBER')}


def test_requested_payment_scenario_receipts_affiliation_reports(db, tmp_path):
    context, family, links, james, agnes, marriage = scenario(db)
    finance = ContributionService(*context)
    kind = finance.create_type('Annual ' + uuid.uuid4().hex, 'ANNUAL', '60')
    period = finance.create_period(kind['id'], 'Annual Contribution 2026', '60')
    finance.assign_members(period['id'], [james['id'], agnes['id']])
    finance.set_period_status(period['id'], 'ACTIVE')
    obligation = finance.obligations(period['id'], james['id'])[0]
    receipt = 'TEST-' + uuid.uuid4().hex
    first = finance.record_payment(obligation['id'], '20', 'CASH', receipt_number=receipt)
    assert finance.get_obligation(obligation['id'])['outstanding'] == Decimal('40')
    with pytest.raises(ValueError, match='receipt'):
        finance.record_payment(obligation['id'], '20', 'CASH', receipt_number=receipt)
    second = finance.record_payment(obligation['id'], '40', 'MOBILE_MONEY')
    assert finance.get_obligation(obligation['id'])['status'] == 'PAID'
    with pytest.raises(ValueError, match='GHS 0.00'):
        finance.record_payment(obligation['id'], '5', 'CASH')
    for amount in ('0', '-1'):
        with pytest.raises(ValueError):
            finance.record_payment(obligation['id'], amount, 'CASH')
    with pytest.raises(ValueError):
        finance.reverse_payment(second['id'], '')
    finance.reverse_payment(second['id'], 'Incorrect amount')
    row = finance.get_obligation(obligation['id'])
    assert (row['total_paid'], row['outstanding'], row['status']) == (Decimal('20'), Decimal('40'), 'PARTIALLY_PAID')
    history = finance.payment_history(obligation['id'])
    assert len(history) == 2 and sum(p['is_reversed'] for p in history) == 1
    assert finance.summary(period['id'], 'MARRIED_IN')['expected_total'] == Decimal('60')
    assert finance.obligations(period['id'], affiliation_type='MARRIED_IN')[0]['family_member_id'] == agnes['id']
    report = ReportService(*context, tmp_path)
    columns, rows = report.data('Contribution summary', period_id=period['id'], affiliation_type='LINEAGE_MEMBER')
    assert rows[0]['expected_total'] == Decimal('60') and rows[0]['collected'] == Decimal('20')
    _, rows = report.data('Payment transaction history', period_id=period['id'], affiliation_type='MARRIED_IN')
    assert rows == []
    columns, rows = report.data('Family register', affiliation_type='MARRIED_IN')
    assert 'birth_position' in columns and 'branch' in columns and agnes['id'] in {r['id'] for r in rows}
