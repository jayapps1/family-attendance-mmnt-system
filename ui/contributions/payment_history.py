from ui.components import Screen, Field, FormDialog


class PaymentHistory(Screen):
    def __init__(self, app, obligation):
        super().__init__(app, "Payment history")
        self.obligation = obligation
        self.button("Back to register", self.back)
        self.button("Reverse selected payment", self.reverse)
        self.grid = self.table(("receipt_number", "payment_date", "amount_paid", "payment_method",
                                "reference", "is_reversed", "reversal_reason"))
        app.run(lambda: app.services["contributions"].payment_history(obligation["id"]), self.grid.set_rows)

    def back(self):
        from ui.contributions.contribution_register import ContributionRegister
        self.app.show(lambda app: ContributionRegister(app, self.obligation["contribution_period_id"]))

    def reverse(self):
        payment = self.grid.selected()
        if payment["is_reversed"]:
            raise ValueError("Payment is already reversed")
        FormDialog(self.app, "Reverse payment", [Field("reason", "Reason", "multiline", required=True)],
                   lambda values: self.app.services["contributions"].reverse_payment(payment["id"], values["reason"]))
