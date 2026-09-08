from datetime import date, time
import pytest
from services.meeting_service import MeetingService
from tests.service_helpers import service_context


def test_meeting_validation_and_update(db):
    service = MeetingService(*service_context(db))
    row = service.save(title="Annual", venue="Hall", meeting_date=date.today())
    assert row["status"] == "SCHEDULED"
    service.save(identity=row["id"], status="COMPLETED")
    with pytest.raises(ValueError):
        service.save(title="Bad", venue="Hall", meeting_date=date.today(),
                     start_time=time(15), end_time=time(10))
