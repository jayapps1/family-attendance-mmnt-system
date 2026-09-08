from models import MeetingStatus, MeetingType
from ui.components import Field, FormDialog, enum_options, member_options


def meeting_form(app, members, row=None):
    choices = {"": None, **member_options(members)}
    fields = [Field("title", "Title", required=True), Field("meeting_date", "Meeting date", "date", required=True),
              Field("start_time", "Start time", "time"), Field("end_time", "End time", "time"),
              Field("venue", "Venue", required=True), Field("location", "Location"),
              Field("meeting_type", "Type", choices=enum_options(MeetingType), required=True),
              Field("status", "Status", choices=enum_options(MeetingStatus), required=True),
              Field("chairperson_id", "Chairperson", choices=choices), Field("secretary_id", "Secretary", choices=choices),
              Field("agenda", "Agenda", "multiline"), Field("description", "Description", "multiline"),
              Field("notes", "Notes", "multiline")]
    FormDialog(app, "Meeting", fields,
               lambda values: app.services["meetings"].save(identity=row["id"] if row else None, **values),
               initial=row or {"meeting_type": "GENERAL", "status": "SCHEDULED"})
