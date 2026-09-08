from decimal import Decimal
import pytest
from services.family_service import FamilyService
from services.contribution_service import ContributionService
from tests.service_helpers import service_context


def test_annual_first_payment_atomic_and_installments(db):
    context=service_context(db)
    family, finance=FamilyService(*context),ContributionService(*context)
    james=family.create(first_name='James',last_name='Appiah-Gyachie',sex='MALE',phone_number='0542011738')
    period=finance.setup_annual(2091,'60')
    assert finance.setup_annual(2091,'60')['id'] == period['id']
    assert finance.obligations(period['id'],james['id']) == []
    assert finance.payment_preview(period['id'],james['id'])['outstanding'] == Decimal('60')
    assert next(r for r in finance.register_rows(period['id']) if r['family_member_id']==james['id'])['status']=='UNPAID'
    assert finance.obligations(period['id'],james['id']) == []
    with pytest.raises(ValueError,match='remaining balance of GHS 60.00'):
        finance.record_contribution(james['id'],period['id'],'70')
    assert finance.obligations(period['id'],james['id']) == []
    for amount,paid,balance,status in [('30','30','30','PARTIALLY_PAID'),('20','50','10','PARTIALLY_PAID'),('10','60','0','PAID')]:
        payment=finance.record_contribution(james['id'],period['id'],amount)
        row=payment['summary']
        assert (row['amount_due'],row['total_paid'],row['outstanding'],row['status']) == (Decimal('60'),Decimal(paid),Decimal(balance),status)
    obligation=finance.obligations(period['id'],james['id'])[0]
    history=finance.payment_history(obligation['id'])
    assert len(history)==3 and len(finance.obligations(period['id'],james['id']))==1
    assert not finance.payment_preview(period['id'],james['id'])['can_pay']
    finance.reverse_payment(history[0]['id'],'Wrong entry')
    assert finance.payment_preview(period['id'],james['id'])['outstanding']==Decimal('30')
    assert len(finance.payment_history(obligation['id']))==3
    with pytest.raises(ValueError,match='different amount'): finance.setup_annual(2091,'80')
    assert finance.setup_annual(2092,'80')['amount_per_member']==Decimal('80')


def test_annual_eligibility_existing_history_and_failure_rollback(db):
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    member=family.create(first_name='Married',last_name='In',sex='FEMALE',affiliation_type='MARRIED_IN')
    period=finance.setup_annual(2093,'125.50')
    for amount in ('0','-1','NaN'):
        with pytest.raises(ValueError): finance.record_contribution(member['id'],period['id'],amount)
    assert finance.obligations(period['id'],member['id'])==[]
    first=finance.record_contribution(member['id'],period['id'],'25.50',receipt_number='TEST-'+str(member['id']))
    family.archive(member['id'])
    # An existing obligation remains payable regardless of affiliation/archive state.
    assert finance.record_contribution(member['id'],period['id'],'50')['summary']['outstanding']==Decimal('50')
    other=finance.setup_annual(2094,'80')
    with pytest.raises(ValueError,match='active, non-deceased'):
        finance.record_contribution(member['id'],other['id'],'20')
    assert finance.obligations(other['id'],member['id'])==[]
    finance.set_period_status(period['id'],'CLOSED')
    with pytest.raises(ValueError,match='active period'):
        finance.record_contribution(member['id'],period['id'],'20')
