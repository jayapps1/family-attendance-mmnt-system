from tkinter import messagebox
from ui.components import Screen, Field, FormDialog, member_options, options
from services.report_service import ReportService


class ReportsScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Reports")
        self.members, self.periods = [], []
        self.button("Generate PDF / Excel", self.export)
        self.show_instructions()
        app.run(lambda: (app.services["family"].list(), app.services["contributions"].periods()), self.loaded)

    def show_instructions(self):
        from tkinter import ttk
        ttk.Label(self, text="Choose a report and optional member or contribution period.\n"
                  "For a family branch report, select its founding member.\n"
                  "Exports are saved under reports/pdf or reports/excel.", justify="left",
                  font=("Segoe UI", 12)).pack(anchor="w", pady=12)

    def loaded(self, data):
        self.members, self.periods = data

    def export(self):
        FormDialog(self.app, "Export report", [
            Field("name", "Report", choices={r: r for r in ReportService.REPORTS}, required=True),
            Field("format", "Format", choices={"PDF": "PDF", "Excel": "Excel"}, required=True),
            Field("member_id", "Member / branch founder (optional)", choices={"All": None, **member_options(self.members)}),
            Field("period_id", "Contribution period (optional)", choices={"All": None, **options(self.periods)})],
            lambda values: self.app.services["reports"].export(**values),
            initial={"format": "PDF"},
            success=lambda path: messagebox.showinfo("Report created", path, parent=self))
