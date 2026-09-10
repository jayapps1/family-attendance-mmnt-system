from datetime import date
from decimal import Decimal
import uuid
import pytest
from models import MemberContribution, ContributionPayment
from services.contribution_eligibility import get_member_contribution_eligibility
from services.contribution_service import ContributionService
from services.family_service import FamilyService
from services.report_service import ReportService
from tests.service_helpers import service_context


@pytest.mark.parametrize("born,on,expected,age", [
    (date(2003,12,20),date(2026,9,9),"UNDER_23",22),
    (date(2003,12,20),date(2026,12,19),"UNDER_23",22),
    (date(2003,12,20),date(2026,12,20),"ELIGIBLE",23),
    (date(2004,2,29),date(2027,2,28),"UNDER_23",22),
    (date(2004,2,29),date(2027,3,1),"ELIGIBLE",23),
    (None,date(2026,9,9),"DOB_UNKNOWN",None),
])
def test_exact_age_boundary(born,on,expected,age):
    result=get_member_contribution_eligibility(dict(date_of_birth=born,living_status="LIVING",is_active=True),on)
    assert (result['eligibility'],result['age'])==(expected,age)


def test_deceased_and_unknown_living_are_never_eligible():
    assert get_member_contribution_eligibility(dict(living_status='DECEASED',date_of_birth=None))['eligibility']=='DECEASED'
    assert not get_member_contribution_eligibility(dict(living_status='UNKNOWN',date_of_birth=date(1980,1,1)))['eligible']
    assert 'age' not in MemberContribution.__table__.c
    from models import FamilyMember
    assert 'age' not in FamilyMember.__table__.c


def test_ten_member_totals_and_review_does_not_create_debt(db,monkeypatch,tmp_path):
    from repositories.family_repository import FamilyRepository
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    identities=set()
    for index in range(10):
        row=family.create(first_name='Eligibility',last_name=str(index),sex='MALE',
            date_of_birth=date(1980,1,1) if index<7 else date(date.today().year-19,1,1),
            living_status='DECEASED' if index<2 else 'LIVING')
        identities.add(row['id'])
    original=FamilyRepository.search
    monkeypatch.setattr(FamilyRepository,'search',lambda self,*a,**k:[r for r in original(self,*a,**k) if r.id in identities])
    period=finance.setup_annual(2086,'60')
    summary=finance.daily_summary(period['id'])
    assert (summary['eligible_contributors'],summary['DECEASED'],summary['UNDER_23'])==(5,2,3)
    assert (summary['expected_total'],summary['outstanding'],summary['UNPAID'])==(Decimal('300'),Decimal('300'),5)
    rows=finance.register_rows(period['id'])
    assert all(r['amount_due']==0 and r['outstanding']==0 and r['status'] is None for r in rows if not r['eligible'])
    assert finance.obligations(period['id'])==[]
    _,unpaid=ReportService(*context,tmp_path).data('Unpaid members',period_id=period['id'])
    assert len(unpaid)==5
    unknown=family.create(first_name='Missing',last_name='DOB',sex='FEMALE')
    identities.add(unknown['id'])
    assert finance.payment_preview(period['id'],unknown['id'])['eligibility']=='DOB_UNKNOWN'
    with pytest.raises(ValueError,match='date of birth'):
        finance.assign_members(period['id'],[unknown['id']])
    with pytest.raises(ValueError,match='date of birth'):
        finance.record_contribution(unknown['id'],period['id'],'30')
    family.update(unknown['id'],date_of_birth=date(1990,1,1))
    assert finance.payment_preview(period['id'],unknown['id'])['can_pay']


def test_death_preserves_partial_payment_and_blocks_every_entry_path(db,tmp_path):
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    member=family.create(first_name='James',last_name='Eligibility',sex='MALE',date_of_birth=date(1990,1,1))
    period=finance.setup_annual(2087,'60')
    initial=finance.record_contribution(member['id'],period['id'],'30')
    obligation=finance.obligations(period['id'],member['id'])[0]
    before=finance.daily_summary(period['id'])
    family.update(member['id'],living_status='DECEASED')
    after=finance.daily_summary(period['id'])
    assert after['expected_total']==before['expected_total']-Decimal('60')
    assert after['outstanding']==before['outstanding']-Decimal('30')
    assert after['collected']==before['collected']
    preview=finance.payment_preview(period['id'],member['id'])
    assert (preview['status'],preview['eligibility'],preview['total_paid'],preview['outstanding'])==('PARTIALLY_PAID','DECEASED',Decimal('30'),Decimal('0'))
    assert preview['historical_balance']==Decimal('30') and not preview['can_pay']
    for call in (lambda:finance.record_contribution(member['id'],period['id'],'10'),
                 lambda:finance.record_payment(obligation['id'],'10','CASH'),
                 lambda:finance.assign_members(period['id'],[member['id']])):
        with pytest.raises(ValueError,match='deceased'):call()
    assert len(finance.payment_history(obligation['id']))==1
    db.expire_all()
    assert db.get(MemberContribution,obligation['id']).amount_due==Decimal('60')
    assert db.get(ContributionPayment,initial['id']).amount_paid==Decimal('30')
    _,rows=ReportService(*context,tmp_path).data('Partially paid members',period_id=period['id'])
    assert not any(r['family_member_id']==member['id'] for r in rows)
    finance.set_period_status(period['id'],'CLOSED')
    assert finance.daily_summary(period['id'])['outstanding']==Decimal('30')
    finance.reverse_payment(initial['id'],'Correction after death')
    assert len(finance.payment_history(obligation['id']))==1


def test_eligible_installments_recent_search_and_reversal_summary(db):
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    member=family.create(first_name='James',last_name='Payment '+uuid.uuid4().hex,sex='MALE',date_of_birth=date(1990,1,1))
    period=finance.setup_annual(2088,'60')
    for amount,balance in (('30','30'),('20','10'),('10','0')):
        result=finance.record_contribution(member['id'],period['id'],amount)
        assert result['summary']['outstanding']==Decimal(balance)
    rows=finance.recent_payments(period['id'],limit=None,search=member['family_number'])
    assert len(rows)==3 and all(r['recorded_by_name'] and r['received_by_name'] for r in rows)
    assert finance.payment_summary(period['id'])['current_collected']==Decimal('60')
    finance.reverse_payment(result['id'],'Wrong entry')
    assert len(finance.recent_payments(period['id'],limit=None,status='REVERSED'))==1
    assert len(finance.recent_payments(period['id'],limit=None))==3
    assert finance.payment_summary(period['id'])['current_collected']==Decimal('50')
    with pytest.raises(ValueError):finance.update_period(period['id'],period['contribution_type_id'],'Changed','80',2088)


@pytest.mark.parametrize("change,reason", [({'date_of_birth':date(date.today().year-22,12,31)},'age 23'),
    ({'living_status':'DECEASED'},'deceased'),({'date_of_birth':None},'date of birth'),
    ({'living_status':'UNKNOWN'},'living')])
def test_saved_obligation_cannot_bypass_changed_eligibility(db,change,reason):
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    member=family.create(first_name='Changed',last_name='Eligibility',sex='MALE',date_of_birth=date(1990,1,1))
    kind=finance.create_type('Change '+str(member['id']),'ANNUAL','60')
    period=finance.create_period(kind['id'],'Change eligibility','60')
    obligation=finance.assign_members(period['id'],[member['id']])[0]
    finance.set_period_status(period['id'],'ACTIVE')
    family.update(member['id'],**change)
    with pytest.raises(ValueError,match=reason):finance.record_payment(obligation['id'],'10','CASH')
    with pytest.raises(ValueError,match=reason):finance.record_contribution(member['id'],period['id'],'10')
    assert finance.payment_history(obligation['id'])==[]
    assert finance.payment_preview(period['id'],member['id'])['outstanding']==0
