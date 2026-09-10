from tkinter import messagebox
from ui.components import Screen, display, TableView
from ui.theme import ResponsiveGrid, StatCard
from tkinter import ttk
from ui.contributions.contribution_type_form import type_form
from ui.contributions.contribution_period_form import period_form
from ui.contributions.contribution_register import ContributionRegister


class ContributionDashboard(Screen):
    def __init__(self, app):
        super().__init__(app, "Contributions")
        self.types = []
        from ui.contributions.payment_form import quick_payment
        from ui.contributions.annual_setup import annual_setup
        self.button("+ RECORD CONTRIBUTION", lambda: quick_payment(app), variant="Primary")
        self.button('Set annual amount', lambda: annual_setup(app))
        self.button("Open register", self.register)
        from ui.contributions.contribution_periods import ContributionPeriods
        from ui.contributions.recent_payments import RecentPayments
        self.button("Contribution Periods",lambda:app.show(ContributionPeriods))
        self.button("Recent Payments",lambda:app.show(RecentPayments))
        advanced = ttk.Menubutton(self.toolbar, text='Advanced setup')
        import tkinter as tk
        menu = tk.Menu(advanced, tearoff=False)
        for label, command in [('New type',lambda:type_form(app)),('View types',self.show_types),
                               ('New period',lambda:period_form(app,self.types)),('Activate selected period',lambda:self.status('ACTIVE')),
                               ('Close selected period',lambda:self.status('CLOSED'))]:
            def invoke(command=command):
                try: command()
                except ValueError as exc: messagebox.showerror('Select period',str(exc),parent=self)
            menu.add_command(label=label,command=invoke)
        advanced.configure(menu=menu); advanced.pack(side='left')
        result = getattr(app,'last_contribution_result',None)
        if result:
            ttk.Label(self,text=f"Saved: {result['member']} | Paid GHS {result['total_paid']:,.2f} | Balance GHS {result['outstanding']:,.2f} | {result['status'].replace('_',' ')}",
                      style='Subtitle.TLabel',wraplength=1000).pack(anchor='w',pady=(0,8))
        self.summary_title = ttk.Label(self, text="Select a period to view its financial summary.", style="Subtitle.TLabel")
        self.summary_title.pack(anchor="w", pady=(0, 10))
        ttk.Label(self,text="Collected includes retained payments from members no longer eligible; their balances are excluded.",style="Subtitle.TLabel",wraplength=900).pack(anchor="w",pady=(0,8))
        from ui.theme import ScrollArea
        card_area=ScrollArea(self)
        card_area.pack(fill="both",expand=True,pady=(0,8))
        cards = ResponsiveGrid(card_area.body, minimum=210, maximum=3)
        cards.pack(fill="x")
        self.summary_cards = {}
        for key, label, tone in (("eligible_contributors", "Eligible contributors", "info"), ("collected", "Collected", "success"),
                                 ("outstanding", "Outstanding", "warning"), ("PAID", "Paid members", "success"),
                                 ("PARTIALLY_PAID", "Partially paid", "warning"), ("UNPAID", "Unpaid", "danger"),
                                 ("UNDER_23", "Under 23", "info"), ("DECEASED", "Deceased", "info"), ("DOB_UNKNOWN", "DOB review required", "warning")):
            self.summary_cards[key] = cards.add(StatCard(cards, label, tone=tone))
        tabs = ttk.Notebook(card_area.body)
        tabs.pack(fill='both', expand=True, pady=(8,0))
        periods_page, recent_page = ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(periods_page, text='Contribution periods')
        tabs.add(recent_page, text='Recent payments')
        self.grid = TableView(periods_page, ("title", "year", "amount_per_member", "start_date", "due_date", "status"))
        self.grid.tree.configure(height=5)
        self.grid.pack(fill='both', expand=True)
        self.recent = TableView(recent_page, ("member", "payment_date", "amount_paid", "payment_method", "is_reversed"))
        self.recent.tree.configure(height=5)
        self.recent.pack(fill='both', expand=True)
        self.grid.tree.bind("<<TreeviewSelect>>", self.load_summary, add="+")
        app.run(lambda: (app.services["contributions"].types(), app.services["contributions"].periods()), self.render)

    def render(self, data):
        self.types, periods = data
        self.grid.set_rows(periods)
        if periods:
            from ui.contributions.payment_form import preferred_period
            preferred = preferred_period([p for p in periods if p['status'] == 'ACTIVE'])
            index = next((i for i,p in enumerate(periods) if preferred and p['id'] == preferred['id']),0)
            self.grid.tree.selection_set(str(index))

    def load_summary(self, event=None):
        if not self.grid.tree.selection():
            return
        period = self.grid.selected()
        self.summary_title.configure(text=period["title"] + f" | Fixed amount: GHS {period['amount_per_member']:,.2f}")
        for card in self.summary_cards.values():
            card.set("--")
        def render(summary):
            if self.grid.tree.selection() and self.grid.selected()["id"] == period["id"]:
                for key, card in self.summary_cards.items():
                    card.set(display(summary.get(key,0)))
        self.app.run(lambda: self.app.services["contributions"].daily_summary(period["id"]), render)
        self.app.run(lambda: self.app.services['contributions'].recent_payments(period['id']),
                     lambda rows: self.recent.set_rows(rows) if self.grid.tree.selection() and self.grid.selected()['id'] == period['id'] else None)

    def show_types(self):
        self.show_text("Contribution types", "\n".join(f'{r["name"]} - {r["frequency"]} - Default GHS {r["default_amount"]}'
                                                      for r in self.types))

    def status(self, status):
        period = self.grid.selected()
        if messagebox.askyesno("Confirm", f'Change {period["title"]} to {status}?', parent=self):
            self.app.run(lambda: self.app.services["contributions"].set_period_status(period["id"], status),
                         lambda _: self.app.refresh())

    def register(self):
        identity = self.grid.selected()["id"]
        self.app.show(lambda app: ContributionRegister(app, identity))
