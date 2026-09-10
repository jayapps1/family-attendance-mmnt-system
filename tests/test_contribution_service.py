from datetime import date
from decimal import Decimal
import pytest
from services.family_service import FamilyService
from services.contribution_service import ContributionService
from tests.service_helpers import service_context


def test_payment_lifecycle_and_reversal(db):
    context = service_context(db)
    member = FamilyService(*context).create(first_name="Test", last_name="Finance", sex="FEMALE", date_of_birth=date(1990, 1, 1))
    service = ContributionService(*context)
    kind = service.create_type("Annual test " + str(member["id"]), "ANNUAL", "60")
    period = service.create_period(kind["id"], "Test", "60")
    obligation = service.assign_members(period["id"], [member["id"]])[0]
    assert service.assign_members(period["id"], [member["id"]]) == []
    with pytest.raises(ValueError):
        service.record_payment(obligation["id"], "20", "CASH")
    service.set_period_status(period["id"], "ACTIVE")
    first = service.record_payment(obligation["id"], "20", "CASH")
    assert service.obligations(period["id"])[0]["status"] == "PARTIALLY_PAID"
    with pytest.raises(ValueError):
        service.record_payment(obligation["id"], "41", "CASH")
    service.record_payment(obligation["id"], "40", "MOBILE_MONEY")
    assert service.get_obligation(obligation["id"])["outstanding"] == Decimal("0")
    assert service.obligations(period["id"])[0]["status"] == "PAID"
    service.reverse_payment(first["id"], "Incorrect entry")
    assert service.get_obligation(obligation["id"])["outstanding"] == Decimal("20")
    assert len(service.payment_history(obligation["id"])) == 2
    with pytest.raises(ValueError):
        service.reverse_payment(first["id"], "Again")
    service.set_period_status(period["id"], "CLOSED")
    with pytest.raises(ValueError):
        service.record_payment(obligation["id"], "20", "CASH")


@pytest.mark.parametrize("amount", [0.1, "-1", "NaN", "1.001", "Infinity"])
def test_money_validation(amount):
    from utils.validators import money
    with pytest.raises(ValueError):
        money(amount)
