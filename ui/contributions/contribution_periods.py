from tkinter import ttk, messagebox
from ui.components import Screen, TableView, display
from ui.theme import ScrollArea, SectionCard, ResponsiveGrid, StatCard, StatusBadge
from ui.contributions.contribution_period_form import period_form
from ui.contributions.payment_form import preferred_period


class ContributionPeriods(Screen):
    def __init__(self, app):
        super().__init__(app, "Contribution Periods", back=self.back)
        ttk.Label(self.page_header, text="Configure and manage family contribution periods.", style="Subtitle.TLabel").pack(anchor="w")
        self.types = []
        self.button("+ New Contribution Period", lambda:period_form(app,self.types), variant="Primary")
        self.button("View selected", self.view)
        self.button("Edit selected", self.edit)
        self.button("Activate selected", lambda:self.change("ACTIVE"))
        self.button("Close selected", lambda:self.change("CLOSED"), variant="Warning")
        area = ScrollArea(self)
        area.pack(fill="both", expand=True)
        self.active = ttk.Frame(area.body)
        self.active.pack(fill="x")
        history = SectionCard(area.body, "Contribution period history")
        history.pack(fill="both", expand=True, pady=12)
        self.grid = TableView(history.body, ("title","year","amount_per_member","start_date","due_date","eligible_contributors","status","action"))
        self.grid.tree.heading("title",text="Contribution")
        self.grid.tree.heading("amount_per_member",text="Amount")
        self.grid.tree.configure(height=7)
        self.grid.pack(fill="both", expand=True)
        self.grid.tree.bind("<Double-1>",lambda e:self.view())
        self.grid.tree.bind("<Return>",lambda e:self.view())
        app.run(lambda:(app.services['contributions'].types(),app.services['contributions'].period_overview()), self.render)

    def back(self):
        from ui.contributions.contribution_dashboard import ContributionDashboard
        self.app.show(ContributionDashboard, remember=False)

    def render(self, data):
        self.types, rows = data
        self.grid.set_rows([dict(r,action="View" if r['status']=='CLOSED' else "View / Edit") for r in rows])
        active = preferred_period([r for r in rows if r['status']=='ACTIVE'])
        if not rows:
            card = SectionCard(self.active,"No contribution period has been configured.")
            card.pack(fill="x")
            ttk.Button(card.body,text="Create First Contribution Period",style="PrimaryButton.TButton",command=lambda:period_form(self.app,self.types)).pack(anchor="w")
            return
        if not active:
            ttk.Label(self.active,text="No active contribution period. Select a draft period to activate.",style="Subtitle.TLabel").pack(anchor="w",pady=15)
            return
        card = SectionCard(self.active,"ACTIVE CONTRIBUTION",active['title'])
        card.pack(fill="x")
        ttk.Label(card.body,text=f"{active.get('year') or ''}   |   GHS {active['amount_per_member']:,.2f} per eligible member",style="CardTitle.TLabel").pack(anchor="w",pady=8)
        ttk.Label(card.body,text=f"Start: {display(active['start_date']) or 'Not set'}    Due: {display(active['due_date']) or 'Not set'}",style="CardHelper.TLabel").pack(anchor="w")
        ttk.Label(card.body,text=f"Expected: GHS {active['expected_total']:,.2f}",style="Card.TLabel").pack(anchor="w",pady=8)
        if active['historical_collected']:
            ttk.Label(card.body,text=f"Collected includes GHS {active['historical_collected']:,.2f} retained from members no longer eligible.",style="CardHelper.TLabel",wraplength=700).pack(anchor="w",pady=6)
        StatusBadge(card.body,"ACTIVE").pack(anchor="w")
        actions=ttk.Frame(card.body,style="Card.TFrame");actions.pack(fill="x",pady=10)
        for text,command in (("View",lambda:self.view(active)),("Edit",lambda:self.edit(active)),("Close Period",lambda:self.change("CLOSED",active))):
            ttk.Button(actions,text=text,command=command).pack(side="left",padx=(0,8))
        cards=ResponsiveGrid(self.active,minimum=210,maximum=3);cards.pack(fill="x",pady=12)
        for key,label in (("eligible_contributors","Eligible"),("PAID","Paid"),("PARTIALLY_PAID","Partial"),("UNPAID","Unpaid"),("collected","Collected"),("outstanding","Outstanding")):
            cards.add(StatCard(cards,label,display(active[key])))

    def view(self, row=None):
        from ui.contributions.contribution_register import ContributionRegister
        row=row or self.grid.selected()
        self.app.show(lambda app:ContributionRegister(app,row['id']))

    def edit(self,row=None):
        row=row or self.grid.selected()
        if row['status']=='CLOSED': raise ValueError("Closed periods cannot be edited.")
        period_form(self.app,self.types,row)

    def change(self,status,row=None):
        row=row or self.grid.selected()
        if messagebox.askyesno("Contribution period",f"Change {row['title']} to {status.lower()}?",parent=self):
            self.app.run(lambda:self.app.services['contributions'].set_period_status(row['id'],status),lambda _:self.app.refresh())
