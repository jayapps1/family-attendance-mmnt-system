from datetime import date
from models import PaymentMethod
from ui.components import Field, FormDialog, enum_options


def payment_form(app, obligation):
    FormDialog(app, f'Record payment - balance GHS {obligation["outstanding"]}', [
        Field("amount_paid", "Amount paid (GHS)", "money", required=True),
        Field("payment_date", "Payment date", "date", required=True),
        Field("payment_method", "Payment method", choices=enum_options(PaymentMethod), required=True),
        Field("reference", "Reference"), Field("remarks", "Remarks", "multiline")],
        lambda values: app.services["contributions"].record_payment(obligation["id"], **values),
        initial={"payment_date": date.today(), "payment_method": "CASH"})
