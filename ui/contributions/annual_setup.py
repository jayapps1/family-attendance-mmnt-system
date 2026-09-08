from datetime import date
from ui.components import Field, FormDialog


def annual_setup(app):
    return FormDialog(app, 'Set annual contribution', [
        Field('year','Year','int',required=True), Field('amount_per_member','Annual amount per member (GHS)','money',required=True)],
        lambda values:app.services['contributions'].setup_annual(**values), initial={'year':date.today().year},save_label='Save annual contribution')
