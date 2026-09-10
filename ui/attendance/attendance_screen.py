from models import AttendanceStatus
from ui.components import Screen, Field, FormDialog, enum_options, member_options, options, show_details


class AttendanceScreen(Screen):
    def __init__(self, app, meeting_id=None):
        super().__init__(app, "Attendance")
        self.meeting_id, self.members, self.meetings = meeting_id, [], []
        self.button("Record / update", self.record)
        self.button("Member history", self.history)
        self.button("Summary", self.summary)
        self.grid = self.table(("member", "meeting", "status", "reason", "arrival_time", "remarks", "recorded_by_name"))
        app.run(lambda: (app.services["attendance"].list(meeting_id), app.services["family"].list(),
                         app.services["meetings"].list()), self.render)

    def render(self, data):
        rows, self.members, self.meetings = data
        names = {v: k for k, v in member_options(self.members).items()}
        meetings = {r["id"]: r["title"] for r in self.meetings}
        self.grid.set_rows([dict(r, member=names[r["family_member_id"]], meeting=meetings[r["meeting_id"]]) for r in rows])

    def record(self):
        FormDialog(self.app, "Record attendance", [
            Field("meeting_id", "Meeting", choices=options(self.meetings), required=True),
            Field("family_member_id", "Member", choices=member_options(self.members), required=True),
            Field("status", "Status", choices=enum_options(AttendanceStatus), required=True),
            Field("reason", "Permission / absence reason", "multiline"),
            Field("arrival_time", "Arrival time", "time"), Field("remarks", "Remarks", "multiline")],
            lambda values: self.app.services["attendance"].record(**values),
            initial={"meeting_id": self.meeting_id, "status": "PRESENT"})

    def history(self):
        row = self.grid.selected()
        self.app.run(lambda: self.app.services["attendance"].member_history(row["family_member_id"]),
                     lambda rows: self.show_text("Member attendance history", "\n".join(
                         f'{r["meeting_date"]}: {r["meeting_title"]} - {r["status"]}' for r in rows)))

    def summary(self):
        self.app.run(lambda: self.app.services["attendance"].summary(meeting_id=self.meeting_id),
                     lambda result: show_details(self, "Attendance summary", result, statistics=True))
