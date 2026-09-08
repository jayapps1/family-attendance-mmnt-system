from decimal import Decimal
from tkinter import ttk
from ui.components import Screen, display
from ui.theme import ScrollArea, ResponsiveGrid, StatCard, SectionCard, StatusBadge


class Dashboard(Screen):
    def __init__(self, app):
        super().__init__(app, "Dashboard")
        area = ScrollArea(self)
        area.pack(fill="both", expand=True)
        hero = SectionCard(area.body, "Your family. One connected record.",
                           "Preserve your shared story, stay organized and keep every generation connected.")
        hero.pack(fill="x", pady=(0, 18))
        ttk.Label(hero.body, text="FAMILY OVERVIEW", style="CardHelper.TLabel").pack(anchor="w")
        grid = ResponsiveGrid(area.body, minimum=240, maximum=4)
        grid.pack(fill="x")
        self.cards = {}
        for key, label, tone, helper in (
            ("members", "Total family members", "primary", "All registered records"),
            ("living", "Living members", "accent", "Members marked living"),
            ("meetings", "Meetings", "primary", "Planned and past gatherings"),
            ("attendance", "Attendance", "accent", "Based on recorded attendance"),
            ("active", "Active contributions", "gold", "Open contribution periods"),
            ("collected", "Amount collected", "success", "Across active periods"),
            ("outstanding", "Outstanding contributions", "warning", "Across active periods"),
            ("gallery", "Gallery items", "gold", "Memories in your collection"),
        ):
            self.cards[key] = grid.add(StatCard(grid, label, tone=tone, helper=helper))
        self.periods = SectionCard(area.body, "Active contribution periods",
                                  "Payment totals are calculated from valid, non-reversed transactions.")
        self.periods.pack(fill="x", pady=(6, 0))
        app.run(self.load, self.render)

    def load(self):
        family = self.app.services["family"].list()
        meetings = self.app.services["meetings"].list()
        periods = self.app.services["contributions"].periods()
        active = [p for p in periods if p["status"] == "ACTIVE"]
        summaries = [(p, self.app.services["contributions"].summary(p["id"])) for p in active]
        attendance = self.app.services["attendance"].summary()
        albums = self.app.services["gallery"].albums()
        gallery_count = sum(len(self.app.services["gallery"].items(album["id"])) for album in albums)
        return family, meetings, summaries, attendance, gallery_count

    def render(self, data):
        family, meetings, summaries, attendance, gallery = data
        values = {
            "members": f"{len(family):,}", "living": f'{sum(row["living_status"] == "LIVING" for row in family):,}',
            "meetings": f"{len(meetings):,}", "attendance": f'{attendance.get("attendance_percentage", 0):g}%',
            "active": len(summaries), "gallery": f"{gallery:,}",
            "collected": display(sum((summary["collected"] for _, summary in summaries), Decimal("0"))),
            "outstanding": display(sum((summary["outstanding"] for _, summary in summaries), Decimal("0"))),
        }
        for key, value in values.items():
            self.cards[key].set(value)
        for widget in self.periods.body.winfo_children():
            widget.destroy()
        if not summaries:
            ttk.Label(self.periods.body, text="No active contribution periods. Create or activate a period in Contributions.",
                      style="CardHelper.TLabel").pack(anchor="w", pady=10)
        for period, summary in summaries:
            row = ttk.Frame(self.periods.body, style="Card.TFrame", padding=(0, 12))
            row.pack(fill="x")
            ttk.Label(row, text=period["title"], style="Field.TLabel").pack(side="left")
            StatusBadge(row, "ACTIVE").pack(side="left", padx=12)
            ttk.Label(row, text=display(summary["collected"]) + " collected", style="Card.TLabel").pack(side="right")
            details = f'Expected {display(summary["expected_total"])}   |   Outstanding {display(summary["outstanding"])}'
            ttk.Label(self.periods.body, text=details, style="CardHelper.TLabel").pack(anchor="w", pady=(0, 8))
