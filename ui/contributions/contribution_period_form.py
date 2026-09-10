from ui.components import Field, FormDialog, options


def period_form(app, types, period=None):
    if not types:
        from ui.contributions.annual_setup import annual_setup
        annual_setup(app)
        return
    FormDialog(app, "Contribution period", [
        Field("contribution_type_id", "Contribution type", choices=options(types, "name"), required=True),
        Field("title", "Period title", required=True), Field("year", "Year (optional)", "int"),
        Field("amount_per_member", "Amount per member (GHS)", "money", required=True),
        Field("start_date", "Start date", "date"), Field("due_date", "Due date", "date"),
        Field("description", "Description", "multiline")],
        lambda values: app.services["contributions"].update_period(period["id"], **values) if period else app.services["contributions"].create_period(**values), initial=period)
