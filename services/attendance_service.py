from collections import Counter
from models import Attendance, AttendanceStatus, MeetingStatus
from repositories.attendance_repository import AttendanceRepository
from repositories.meeting_repository import MeetingRepository
from repositories.family_repository import FamilyRepository
from repositories.user_repository import UserRepository
from services.base import Service, snapshot
from utils.validators import required, ValidationError


class AttendanceService(Service):
    def record(self, meeting_id, family_member_id, status, reason=None, arrival_time=None, remarks=None):
        status = AttendanceStatus(status)
        if status is AttendanceStatus.PERMISSION:
            reason = required(reason, "Permission reason", 2000)
        with self.transaction() as session:
            meeting = MeetingRepository(session).get(meeting_id, lock=True)
            if meeting.status is MeetingStatus.CANCELLED:
                raise ValidationError("Cannot record attendance for a cancelled meeting")
            FamilyRepository(session).get(family_member_id)
            repo = AttendanceRepository(session)
            row = repo.find(meeting_id, family_member_id)
            action = "UPDATE_ATTENDANCE" if row else "RECORD_ATTENDANCE"
            row = row or Attendance(meeting_id=meeting_id, family_member_id=family_member_id)
            row.status, row.reason, row.arrival_time, row.remarks = status, reason, arrival_time, remarks
            row.recorded_by = self.actor_id
            repo.add(row)
            self.audit(session, action, row)
            return snapshot(row)

    def list(self, meeting_id=None):
        with self.transaction() as session:
            criteria = [Attendance.meeting_id == meeting_id] if meeting_id else []
            names = UserRepository(session).names()
            return [dict(snapshot(row), recorded_by_name=names.get(row.recorded_by, "Unknown"))
                    for row in AttendanceRepository(session).list(*criteria)]

    def member_history(self, member_id):
        with self.transaction() as session:
            names = UserRepository(session).names()
            return [dict(snapshot(row), recorded_by_name=names.get(row.recorded_by, "Unknown"),
                         meeting_title=meeting.title, meeting_date=meeting.meeting_date)
                    for row, meeting in AttendanceRepository(session).history(member_id)]

    def summary(self, *, member_id=None, meeting_id=None):
        rows = self.member_history(member_id) if member_id else self.list(meeting_id)
        counts = Counter(row["status"] for row in rows)
        attended = counts["PRESENT"] + counts["LATE"]
        return {"total_records": len(rows), "total_meetings": len({r["meeting_id"] for r in rows}), "meetings_attended": attended,
                "absences": counts["ABSENT"], "permissions": counts["PERMISSION"],
                "late": counts["LATE"], "excused": counts["EXCUSED"],
                "attendance_percentage": round(100 * attended / len(rows), 2) if rows else 0,
                "basis": "Recorded attendance; cancelled meetings excluded from member history"}
