from models import ContributionFrequency
from ui.components import Field, FormDialog, enum_options


def type_form(app):
    FormDialog(app, "Contribution type", [
        Field("name", "Name", required=True),
        Field("frequency", "Frequency", choices=enum_options(ContributionFrequency), required=True),
        Field("default_amount", "Default amount (GHS, optional)", "money"),
        Field("description", "Description", "multiline")],
        lambda values: app.services["contributions"].create_type(**values),
        initial={"frequency": "ANNUAL"})
