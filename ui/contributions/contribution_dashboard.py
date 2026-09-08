from tkinter import messagebox
from ui.components import Screen
from ui.contributions.contribution_type_form import type_form
from ui.contributions.contribution_period_form import period_form
from ui.contributions.contribution_register import ContributionRegister


class ContributionDashboard(Screen):
    def __init__(self, app):
        super().__init__(app, "Contributions")
        self.types = []
        self.button("New type", lambda: type_form(app))
        self.button("View types", self.show_types)
        self.button("New period", lambda: period_form(app, self.types))
        self.button("Activate period", lambda: self.status("ACTIVE"))
        self.button("Close period", lambda: self.status("CLOSED"))
        self.button("Open register", self.register)
        self.grid = self.table(("title", "year", "amount_per_member", "start_date", "due_date", "status"))
        app.run(lambda: (app.services["contributions"].types(), app.services["contributions"].periods()), self.render)

    def render(self, data):
        self.types, periods = data
        self.grid.set_rows(periods)

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
