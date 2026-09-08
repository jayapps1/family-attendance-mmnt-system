from utils.family_labels import AFFILIATIONS
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
        from ui.theme import ScrollArea, ResponsiveGrid, SectionCard
        area = ScrollArea(self)
        area.pack(fill="both", expand=True)
        grid = ResponsiveGrid(area.body, minimum=330, maximum=2)
        grid.pack(fill="x")
        groups = (("Family records", "Registers, member profiles and your family lineage.", ReportService.REPORTS[:4]),
                  ("Meetings & attendance", "Gatherings, participation and member attendance history.", ReportService.REPORTS[4:7]),
                  ("Contributions", "Payment status, collections and outstanding balances.", ReportService.REPORTS[7:12]),
                  ("Payment history", "Transactions and individual contribution records.", ReportService.REPORTS[12:]))
        for title, help_text, reports in groups:
            card = grid.add(SectionCard(grid, title, help_text))
            ttk.Label(card.body, text="\n".join(reports), style="Card.TLabel").pack(anchor="w", pady=(0, 16))
            for format in ("PDF", "Excel"):
                ttk.Button(card.body, text="Export " + format, style="PrimaryButton.TButton" if format == "PDF" else "SecondaryButton.TButton",
                           command=lambda r=reports, f=format: self.export(r, f)).pack(side="left", padx=(0, 8))
        ttk.Label(area.body, text="Exports are saved under reports/pdf or reports/excel. Select a founder for a family branch report.", style="Subtitle.TLabel", wraplength=750).pack(anchor="w", pady=12)

    def loaded(self, data):
        self.members, self.periods = data

    def export(self, reports=None, format="PDF"):
        FormDialog(self.app, "Export report", [
            Field("name", "Report", choices={r: r for r in (reports or ReportService.REPORTS)}, required=True),
            Field("format", "Format", choices={"PDF": "PDF", "Excel": "Excel"}, required=True),
            Field("member_id", "Member / branch founder (optional)", choices={"All": None, **member_options(self.members)}),
            Field("period_id", "Contribution period (optional)", choices={"All": None, **options(self.periods)}),
            Field("affiliation_type", "Family / contribution affiliation", choices={"All Members": None, **AFFILIATIONS})],
            lambda values: self.app.services["reports"].export(**values),
            initial={"format": format},
            success=lambda path: messagebox.showinfo("Report created", path, parent=self))
