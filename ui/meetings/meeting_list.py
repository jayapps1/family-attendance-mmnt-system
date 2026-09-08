from ui.components import Screen, display, show_details
from ui.meetings.meeting_form import meeting_form


class MeetingList(Screen):
    def __init__(self, app):
        super().__init__(app, "Meetings")
        self.members = []
        self.button("Add meeting", lambda: meeting_form(app, self.members))
        self.button("Edit meeting", lambda: meeting_form(app, self.members, self.grid.selected()))
        self.button("Details", self.details)
        self.button("Attendance", self.attendance)
        self.grid = self.table(("meeting_number", "title", "meeting_date", "start_time", "venue", "status"))
        app.run(lambda: (app.services["meetings"].list(), app.services["family"].list()), self.render)

    def render(self, data):
        rows, self.members = data
        self.grid.set_rows(rows)

    def details(self):
        row = self.grid.selected()
        show_details(self, "Meeting details", row)

    def attendance(self):
        from ui.attendance.attendance_screen import AttendanceScreen
        row = self.grid.selected()
        self.app.show(lambda app: AttendanceScreen(app, row["id"]))
