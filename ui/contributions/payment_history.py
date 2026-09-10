from ui.components import Screen, Field, FormDialog


class PaymentHistory(Screen):
    def __init__(self, app, obligation, return_to=None):
        self.return_to = return_to
        super().__init__(app, "Payment history", back=self.back)
        self.obligation = obligation
        self.button("Reverse selected payment", self.reverse)
        from tkinter import ttk
        self.summary_label = ttk.Label(self, style='Subtitle.TLabel',wraplength=1000)
        self.summary_label.pack(anchor='w',pady=(0,12))
        def render_summary(row):
            self.obligation=row
            self.summary_label.configure(text=f"{row['member']} | {row['period']} | Due GHS {row['amount_due']:,.2f} | Paid GHS {row['total_paid']:,.2f} | Balance GHS {row['outstanding']:,.2f} | {(row['status'] or 'No payments').replace('_',' ') + ' | ' + row['eligibility_label']}")
        app.run(lambda: app.services['contributions'].payment_preview(obligation['contribution_period_id'],obligation['family_member_id']),render_summary)
        self.grid = self.table(("receipt_number", "payment_date", "amount_paid", "payment_method",
                                "reference", "recorded_by_name", "is_reversed", "reversal_reason"))
        app.run(lambda: app.services["contributions"].payment_history(obligation["id"]), self.grid.set_rows)

    def back(self):
        self.app.back()
        if self.return_to:
            self.return_to()

    def reverse(self):
        payment = self.grid.selected()
        if payment["is_reversed"]:
            raise ValueError("Payment is already reversed")
        FormDialog(self.app, f"Reverse GHS {payment['amount_paid']:,.2f} - {self.obligation.get('member', 'Member')}", [Field("reason", "Confirm reversal: reason required", "multiline", required=True)],
                   lambda values: self.app.services["contributions"].reverse_payment(payment["id"], values["reason"]),
                   save_label="Reverse payment", button_style="DangerButton.TButton")
