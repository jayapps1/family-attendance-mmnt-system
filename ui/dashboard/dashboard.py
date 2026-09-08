from tkinter import ttk
from ui.components import Screen


class Dashboard(Screen):
    def __init__(self, app):
        super().__init__(app, "Dashboard")
        self.summary = ttk.Label(self, text="Loading...", font=("Segoe UI", 13), justify="left")
        self.summary.pack(anchor="w", pady=12)
        app.run(self.load, self.render)

    def load(self):
        family = self.app.services["family"].list(active=True)
        meetings = self.app.services["meetings"].list()
        periods = self.app.services["contributions"].periods()
        active = [p for p in periods if p["status"] == "ACTIVE"]
        summaries = [(p, self.app.services["contributions"].summary(p["id"])) for p in active]
        return len(family), len(meetings), summaries

    def render(self, data):
        members, meetings, summaries = data
        lines = [f"Active family members: {members}", f"Meetings: {meetings}", "", "Active contributions"]
        for period, summary in summaries:
            lines += [period["title"], f'Expected GHS {summary["expected_total"]:,.2f}   Collected GHS {summary["collected"]:,.2f}',
                      f'Outstanding GHS {summary["outstanding"]:,.2f}   Paid {summary["PAID"]}   Partial {summary["PARTIALLY_PAID"]}   Unpaid {summary["UNPAID"]}', ""]
        self.summary.configure(text="\n".join(lines))
