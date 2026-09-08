from models import RelationshipType, MarriageStatus
from ui.components import Field, FormDialog, member_options, enum_options


def relationship_form(app, members, row=None):
    choices = member_options(members)
    FormDialog(app, "Parent / child relationship", [
        Field("parent_id", "Parent or guardian", choices=choices, required=True),
        Field("child_id", "Child", choices=choices, required=True),
        Field("relationship_type", "Relationship", choices=enum_options(RelationshipType), required=True)],
        lambda values: app.services["relationships"].save(**values, identity=row["id"] if row else None), initial=row)


def marriage_form(app, members, row=None):
    choices = member_options(members)
    FormDialog(app, "Marriage", [
        Field("spouse_one_id", "First spouse", choices=choices, required=True),
        Field("spouse_two_id", "Second spouse", choices=choices, required=True),
        Field("status", "Status", choices=enum_options(MarriageStatus), required=True),
        Field("marriage_date", "Marriage date", "date"), Field("marriage_location", "Location"),
        Field("notes", "Notes", "multiline")],
        lambda values: app.services["relationships"].save_marriage(**values, identity=row["id"] if row else None),
        initial=row or {"status": "MARRIED"})
