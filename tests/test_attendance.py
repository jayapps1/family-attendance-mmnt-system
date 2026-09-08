from datetime import date
import pytest
from services.family_service import FamilyService
from services.meeting_service import MeetingService
from services.attendance_service import AttendanceService
from tests.service_helpers import service_context


def test_attendance_upsert_and_calculation(db):
    context = service_context(db)
    member = FamilyService(*context).create(first_name="Test", last_name="Attendance", sex="MALE")
    meeting = MeetingService(*context).save(title="Meeting", venue="Hall", meeting_date=date.today())
    service = AttendanceService(*context)
    with pytest.raises(ValueError):
        service.record(meeting["id"], member["id"], "PERMISSION")
    service.record(meeting["id"], member["id"], "PRESENT")
    service.record(meeting["id"], member["id"], "LATE")
    assert len(service.list(meeting["id"])) == 1
    assert service.summary(member_id=member["id"])["attendance_percentage"] == 100
