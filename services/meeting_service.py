import uuid
from models import Meeting, MeetingStatus, MeetingType
from repositories.meeting_repository import MeetingRepository
from services.base import Service, snapshot
from utils.validators import required, ValidationError


class MeetingService(Service):
    FIELDS = {"title", "meeting_date", "start_time", "end_time", "venue", "location", "meeting_type",
              "status", "chairperson_id", "secretary_id", "agenda", "description", "notes"}

    def list(self):
        with self.transaction() as session:
            return [snapshot(row) for row in sorted(MeetingRepository(session).list(),
                                                    key=lambda row: row.meeting_date, reverse=True)]

    def save(self, identity=None, **values):
        if set(values) - self.FIELDS:
            raise ValidationError("Unsupported meeting fields")
        with self.transaction() as session:
            repo = MeetingRepository(session)
            row = repo.get(identity, lock=True) if identity else Meeting(
                meeting_number="MTG-" + uuid.uuid4().hex[:20], created_by=self.actor_id)
            for key, value in values.items():
                setattr(row, key, value)
            row.title = required(row.title, "Title")
            row.venue = required(row.venue, "Venue")
            if not row.meeting_date:
                raise ValidationError("Meeting date is required")
            row.status = MeetingStatus(row.status or "SCHEDULED")
            row.meeting_type = MeetingType(row.meeting_type or "GENERAL")
            if row.start_time and row.end_time and row.end_time < row.start_time:
                raise ValidationError("End time must not precede start time")
            repo.add(row)
            self.audit(session, "UPDATE_MEETING" if identity else "CREATE_MEETING", row)
            return snapshot(row)
