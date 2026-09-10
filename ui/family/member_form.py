from utils.family_labels import AFFILIATIONS
from models import Sex, MaritalStatus, LivingStatus
from ui.components import Field, FormDialog, enum_options


def member_fields():
    fields = [
        Field("first_name", "First name", required=True), Field("middle_name", "Middle name"),
        Field("last_name", "Last name", required=True), Field("sex", "Sex", choices=enum_options(Sex), required=True),
        Field("affiliation_type", "Family affiliation", choices=AFFILIATIONS, required=True),
        Field("date_of_birth", "Date of birth (YYYY-MM-DD)", "date"),
        Field("phone_number", "Phone number"), Field("current_residence", "Current residence"),
        Field("marital_status", "Marital status", choices=enum_options(MaritalStatus), required=True),
        Field("living_status", "Living status", choices=enum_options(LivingStatus), required=True),
        Field("date_of_death", "Date of death (YYYY-MM-DD)", "date"),
        Field("profile_image_path", "Profile photo", "photo"), Field("notes", "Notes", "multiline"),
    ]
    sections = {
        "Personal information": {"first_name", "middle_name", "last_name", "sex", "date_of_birth"},
        "Contact information": {"phone_number", "current_residence"},
        "Family information": {"affiliation_type", "marital_status", "living_status", "date_of_death"},
        "Profile / notes": {"profile_image_path", "notes"},
    }
    for field in fields:
        field.section = next(title for title, names in sections.items() if field.name in names)
    return fields


def member_form(app, member=None, success=None):
    fields = member_fields()
    initial = member or {"marital_status": "SINGLE", "living_status": "LIVING", "affiliation_type": "LINEAGE_MEMBER"}
    service = app.services["family"]
    FormDialog(app, "Edit member" if member else "Add member", fields,
               lambda values: service.save_with_photo(values, app.media_root, identity=member["id"] if member else None),
               initial=initial, save_label="Save member", success=success)
