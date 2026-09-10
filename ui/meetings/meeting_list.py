from ui.components import Screen, member_options, show_details
from ui.meetings.meeting_form import meeting_form


class MeetingList(Screen):
    def __init__(self, app):
        super().__init__(app, "Meetings")
        self.members = []
        from tkinter import ttk
        self.search = ttk.Entry(self.toolbar,width=24)
        self.search.pack(side='left',padx=6)
        self.search.bind('<KeyRelease>',lambda e:self.filter_rows())
        self.button('Start meeting',lambda:self.set_status('ONGOING'))
        self.button('Complete meeting',lambda:self.set_status('COMPLETED'))
        self.button('Cancel meeting',lambda:self.set_status('CANCELLED'),variant='Warning')
        self.button("Add meeting", lambda: meeting_form(app, self.members))
        self.button("Edit meeting", lambda: meeting_form(app, self.members, self.grid.selected()))
        self.button("Details", self.details)
        self.button("Attendance", self.attendance)
        self.grid = self.table(("meeting_number", "title", "meeting_date", "start_time", "venue", "status"))
        app.run(lambda: (app.services["meetings"].list(), app.services["family"].list()), self.render)

    def render(self, data):
        rows, self.members = data
        self.rows=rows
        self.filter_rows()

    def details(self):
        row = self.grid.selected()
        names = {identity: name for name, identity in member_options(self.members).items()}
        details = {key: value for key, value in row.items() if key not in {"chairperson_id", "secretary_id"}}
        details.update(chairperson=names.get(row.get("chairperson_id"), "Not assigned"),
                       secretary=names.get(row.get("secretary_id"), "Not assigned"))
        show_details(self, "Meeting details", details)

    def attendance(self):
        from ui.attendance.attendance_screen import AttendanceScreen
        row = self.grid.selected()
        self.app.show(lambda app: AttendanceScreen(app, row["id"]))

    def filter_rows(self):
        term=self.search.get().casefold().strip()
        self.grid.set_rows([r for r in getattr(self,'rows',[]) if term in ' '.join(str(r.get(k) or '') for k in ('meeting_number','title','venue','location','meeting_date')).casefold()])

    def set_status(self,status):
        from tkinter import messagebox
        row=self.grid.selected()
        if messagebox.askyesno('Meeting status',f"Change {row['title']} to {status.lower()}?",parent=self):
            self.app.run(lambda:self.app.services['meetings'].save(identity=row['id'],status=status),lambda _:self.app.refresh())
