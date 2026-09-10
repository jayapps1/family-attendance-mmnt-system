from utils.family_labels import AFFILIATIONS
import tkinter as tk
from tkinter import ttk
from ui.components import Screen, TableView, member_options
from ui.theme import ResponsiveGrid, StatCard
from ui.contributions.payment_form import payment_form
from ui.contributions.payment_history import PaymentHistory


class ContributionRegister(Screen):
    def __init__(self, app, period_id):
        super().__init__(app, "Contribution register")
        self.period_id, self.members = period_id, []
        self.button("Periods", self.back)
        self.button("Assign members", self.assign)
        self.pay_button = self.button("Record payment", lambda: payment_form(app, self.grid.selected()))
        self.button("Payment history", self.history)
        self.button("Edit Member", self.edit_member)
        from services.contribution_eligibility import LABELS
        self.eligibility_options = {"All": None, **{label: code for code,label in LABELS.items()}}
        self.eligibility = ttk.Combobox(self.toolbar, values=list(self.eligibility_options), state="readonly", width=29)
        self.eligibility.set("Eligible")
        self.eligibility.pack(side="left", padx=6)
        self.eligibility.bind('<<ComboboxSelected>>', lambda e: self.render_rows())
        from ui.contributions.contribution_details import contribution_details
        self.button('View details', lambda: contribution_details(app, self.grid.selected()))
        self.affiliation = ttk.Combobox(self.toolbar, values=['All Members', *AFFILIATIONS], state='readonly', width=21)
        self.affiliation.set('All Members'); self.affiliation.pack(side='left', padx=6)
        self.affiliation.bind('<<ComboboxSelected>>', lambda e: self.render_rows())
        self.filter = ttk.Combobox(self.toolbar, values=["ALL", "PAID", "PARTIALLY_PAID", "UNPAID"], state="readonly", width=18)
        self.filter.set("ALL")
        self.filter.pack(side="left")
        self.filter.bind("<<ComboboxSelected>>", lambda e: self.render_rows())
        summary_grid = ResponsiveGrid(self, minimum=220, maximum=3)
        summary_grid.pack(fill="x", pady=(0, 12))
        self.summary_cards = {}
        for key, label, tone in (("expected_total", "Expected total", "info"), ("collected", "Collected", "success"), ("outstanding", "Outstanding", "warning")):
            self.summary_cards[key] = summary_grid.add(StatCard(summary_grid, label, tone=tone))
        self.summary = ttk.Label(self, style="Subtitle.TLabel")
        self.summary.pack(anchor="w", pady=(0, 12))
        self.grid = self.table(("family_number", "member", "age", "eligibility_label", "amount_due", "total_paid", "outstanding", "status", "action"))
        self.grid.tree.bind('<<TreeviewSelect>>',self.selection_changed,add='+')
        self.grid.tree.bind('<Double-1>',self.row_action)
        self.grid.tree.bind('<Return>',self.row_action)
        app.run(lambda: (app.services["contributions"].register_rows(period_id),
                         app.services["family"].list(), app.services["contributions"].daily_summary(period_id)), self.render)

    def row_action(self,event=None):
        if self.grid.tree.selection():
            row=self.grid.selected()
            if row['can_pay']: payment_form(self.app,row)
            elif row.get('id'): self.history()
            else: self.edit_member()

    def selection_changed(self,event=None):
        if self.grid.tree.selection():
            row = self.grid.selected()
            self.pay_button.configure(state='normal' if row.get('can_pay',row['outstanding'] > 0) else 'disabled',
                                      text='Not eligible' if not row['eligible'] else 'PAID IN FULL' if row['outstanding'] == 0 else 'Record payment')

    def history(self):
        row = self.grid.selected()
        self.app.show(lambda app: PaymentHistory(app, row))

    def edit_member(self):
        from ui.family.member_form import member_form
        selected = self.grid.selected()
        member_form(self.app, next(r for r in self.members if r['id'] == selected['family_member_id']))

    def back(self):
        from ui.contributions.contribution_dashboard import ContributionDashboard
        self.app.show(ContributionDashboard)

    def render(self, data):
        self.rows, self.members, summary = data
        for key, card in self.summary_cards.items():
            card.set(f"GHS {summary[key]:,.2f}")
        self.summary.configure(text=f'Paid: {summary["PAID"]}    Partially paid: {summary["PARTIALLY_PAID"]}    Unpaid: {summary["UNPAID"]}')
        self.render_rows()

    def render_rows(self):
        self.pay_button.configure(state='disabled',text='Record payment')
        names = {v: k for k, v in member_options(self.members).items()}
        status = self.filter.get()
        affiliation = AFFILIATIONS.get(self.affiliation.get())
        eligible = self.eligibility_options.get(self.eligibility.get())
        self.grid.set_rows([r for r in self.rows if (status == 'ALL' or r['status'] == status)
                            and (affiliation is None or r['affiliation_type'] == affiliation)
                            and (eligible is None or r['eligibility'] == eligible)])

    def assign(self):
        dialog = tk.Toplevel(self.app)
        dialog.title("Select eligible members")
        dialog.geometry("760x500")
        dialog.transient(self.app)
        dialog.grab_set()
        ttk.Label(dialog, text="Select the members eligible for this period. Use Ctrl or Shift for multiple selections.").pack(pady=12)
        eligibility = ttk.Combobox(dialog, values=['Selected Members', 'All Active Members', 'Lineage Members Only', 'Married-In Members Only'], state='readonly', width=30)
        eligibility.set('Selected Members'); eligibility.pack(pady=8)
        table = TableView(dialog, ("family_number", "first_name", "last_name"), selectmode="extended")
        table.pack(fill="both", expand=True, padx=12)
        assigned = {r["family_member_id"] for r in self.rows if r.get("id")}
        eligible_ids = {r["family_member_id"] for r in self.rows if r["eligible"]}
        table.set_rows([r for r in self.members if r["id"] in eligible_ids and r["id"] not in assigned])
        def submit():
            mode = eligibility.get()
            candidates = list(table.rows.values())
            ids = [r['id'] for r in (table.selections() if mode == 'Selected Members' else candidates)
                   if mode not in ('Lineage Members Only', 'Married-In Members Only') or
                   r['affiliation_type'] == ('LINEAGE_MEMBER' if mode == 'Lineage Members Only' else 'MARRIED_IN')]
            if not ids:
                return
            button.configure(state="disabled")
            def done(_):
                dialog.destroy()
                self.app.refresh()
            self.app.run(lambda: self.app.services["contributions"].assign_members(self.period_id, ids), done,
                         lambda: button.configure(state="normal") if dialog.winfo_exists() else None)
        button = ttk.Button(dialog, text="Assign selected members", style="PrimaryButton.TButton", command=submit)
        button.pack(pady=12)
