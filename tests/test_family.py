from datetime import date
from services.family_service import FamilyService
from tests.service_helpers import service_context
from utils.date_utils import age_on


def test_create_number_search_archive(db):
    service = FamilyService(*service_context(db))
    first = service.create(first_name="Ada", last_name="Family", sex="FEMALE")
    second = service.create(first_name="Kojo", last_name="Family", sex="MALE")
    assert first["family_number"] != second["family_number"]
    assert any(row["id"] == first["id"] for row in service.list("Ada"))
    service.archive(first["id"])
    assert not any(row["id"] == first["id"] for row in service.list(active=True))
    assert age_on(date(2000, 9, 9), date(2026, 9, 8)) == 25
