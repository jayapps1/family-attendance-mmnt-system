from models import Sex, MaritalStatus, LivingStatus
from ui.components import Field, FormDialog, enum_options


def member_form(app, member=None):
    fields = [
        Field("first_name", "First name", required=True), Field("middle_name", "Middle name"),
        Field("last_name", "Last name", required=True), Field("sex", "Sex", choices=enum_options(Sex), required=True),
        Field("date_of_birth", "Date of birth (YYYY-MM-DD)", "date"),
        Field("phone_number", "Phone number"), Field("current_residence", "Current residence"),
        Field("marital_status", "Marital status", choices=enum_options(MaritalStatus), required=True),
        Field("living_status", "Living status", choices=enum_options(LivingStatus), required=True),
        Field("date_of_death", "Date of death (YYYY-MM-DD)", "date"),
        Field("profile_image_path", "Profile image (relative media path)"), Field("notes", "Notes", "multiline"),
    ]
    initial = member or {"marital_status": "SINGLE", "living_status": "LIVING"}
    service = app.services["family"]
    FormDialog(app, "Edit member" if member else "Add member", fields,
               lambda values: service.update(member["id"], **values) if member else service.create(**values),
               initial=initial)
