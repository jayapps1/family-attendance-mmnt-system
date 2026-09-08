from sqlalchemy import select
from models import Attendance, Meeting, MeetingStatus
from repositories.base import Repository


class AttendanceRepository(Repository[Attendance]):
    def __init__(self, session):
        super().__init__(session, Attendance)

    def find(self, meeting_id, member_id):
        return self.session.scalar(select(Attendance).where(
            Attendance.meeting_id == meeting_id, Attendance.family_member_id == member_id))

    def history(self, member_id):
        return list(self.session.execute(select(Attendance, Meeting).join(Meeting).where(
            Attendance.family_member_id == member_id, Meeting.status != MeetingStatus.CANCELLED
        ).order_by(Meeting.meeting_date)))
