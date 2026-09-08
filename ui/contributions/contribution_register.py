import tkinter as tk
from tkinter import ttk
from ui.components import Screen, TableView, member_options
from ui.contributions.payment_form import payment_form
from ui.contributions.payment_history import PaymentHistory


class ContributionRegister(Screen):
    def __init__(self, app, period_id):
        super().__init__(app, "Contribution register")
        self.period_id, self.members = period_id, []
        self.button("Periods", self.back)
        self.button("Assign members", self.assign)
        self.button("Record payment", lambda: payment_form(app, self.grid.selected()))
        self.button("Payment history", self.history)
        self.filter = ttk.Combobox(self.toolbar, values=["ALL", "PAID", "PARTIALLY_PAID", "UNPAID"], state="readonly", width=18)
        self.filter.set("ALL")
        self.filter.pack(side="left")
        self.filter.bind("<<ComboboxSelected>>", lambda e: self.render_rows())
        self.summary = ttk.Label(self, font=("Segoe UI", 12))
        self.summary.pack(anchor="w", pady=8)
        self.grid = self.table(("member", "amount_due", "total_paid", "outstanding", "status"))
        app.run(lambda: (app.services["contributions"].obligations(period_id),
                         app.services["family"].list(), app.services["contributions"].summary(period_id)), self.render)

    def history(self):
        row = self.grid.selected()
        self.app.show(lambda app: PaymentHistory(app, row))

    def back(self):
        from ui.contributions.contribution_dashboard import ContributionDashboard
        self.app.show(ContributionDashboard)

    def render(self, data):
        self.rows, self.members, summary = data
        self.summary.configure(text=f'Expected GHS {summary["expected_total"]:,.2f}   Collected {summary["collected"]:,.2f}   Outstanding {summary["outstanding"]:,.2f}')
        self.render_rows()

    def render_rows(self):
        names = {v: k for k, v in member_options(self.members).items()}
        status = self.filter.get()
        self.grid.set_rows([dict(r, member=names[r["family_member_id"]]) for r in self.rows
                            if status == "ALL" or r["status"] == status])

    def assign(self):
        dialog = tk.Toplevel(self.app)
        dialog.title("Select eligible members")
        dialog.geometry("760x500")
        dialog.transient(self.app)
        dialog.grab_set()
        ttk.Label(dialog, text="Select the members eligible for this period. Use Ctrl or Shift for multiple selections.").pack(pady=12)
        table = TableView(dialog, ("family_number", "first_name", "last_name"), selectmode="extended")
        table.pack(fill="both", expand=True, padx=12)
        assigned = {r["family_member_id"] for r in self.rows}
        table.set_rows([r for r in self.members if r["is_active"] and r["living_status"] != "DECEASED" and r["id"] not in assigned])
        def submit():
            ids = [r["id"] for r in table.selections()]
            if not ids:
                return
            button.configure(state="disabled")
            def done(_):
                dialog.destroy()
                self.app.refresh()
            self.app.run(lambda: self.app.services["contributions"].assign_members(self.period_id, ids), done,
                         lambda: button.configure(state="normal") if dialog.winfo_exists() else None)
        button = ttk.Button(dialog, text="Assign selected members", command=submit)
        button.pack(pady=12)
