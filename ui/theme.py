"""Central native ttk theme. Presentation only; no domain or database logic."""
import tkinter as tk
from tkinter import ttk

COLORS = {
    "primary": "#17324D", "primary_dark": "#102436",
    "accent": "#1F7A76", "accent_hover": "#17645F", "accent_soft": "#E8F4F2",
    "gold": "#D6A84B", "gold_hover": "#BF9138",
    "background": "#F4F7FA", "surface": "#FFFFFF", "surface_alt": "#EDF2F6",
    "text": "#18212B", "text_secondary": "#62707D", "muted": "#87939D", "border": "#D7E0E7",
    "success": "#2E8B57", "success_bg": "#E9F6EF",
    "warning": "#D79028", "warning_bg": "#FFF5E5",
    "danger": "#C84C4C", "danger_bg": "#FCECEC",
    "info": "#3478B8", "info_bg": "#EAF3FB", "disabled": "#ADB7C0",
    "sidebar_text": "#DCE6ED", "alternate": "#F8FAFC", "selection": "#DCEFED",
    # Darker foregrounds keep small badge/button text readable on pale surfaces.
    "success_text": "#22663F", "warning_text": "#85530F", "danger_text": "#A73535",
}
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
FONTS = {
    "app": ("Segoe UI Semibold", 23), "page": ("Segoe UI Semibold", 21),
    "section": ("Segoe UI Semibold", 14), "body": ("Segoe UI", 10),
    "label": ("Segoe UI Semibold", 10), "small": ("Segoe UI", 9),
    "stat": ("Segoe UI Semibold", 24), "reading": ("Segoe UI", 11),
}
STATUS_TONES = {
    "PAID": "success", "PRESENT": "success", "COMPLETED": "success", "ACTIVE": "success",
    "LIVING": "success", "LOGIN": "success", "ONGOING": "accent", "ADMIN": "info",
    "PARTIALLY_PAID": "warning", "PERMISSION": "warning", "LATE": "warning",
    "SCHEDULED": "warning", "DRAFT": "info", "PENDING": "warning",
    "UNPAID": "danger", "ABSENT": "danger", "CANCELLED": "danger", "REVERSED": "danger",
    "FAILED_LOGIN": "danger", "REVERSE_PAYMENT": "danger", "EXCUSED": "info",
    "SUPER_ADMIN": "gold", "INACTIVE": "muted", "DECEASED": "muted", "CLOSED": "muted",
}
PAGE_HELP = {
    "Family branches": "Explore each founder's lineage, across every generation.",
    "Family tree": "Follow biological parent-child connections through your family history.",
    "Dashboard": "A clear view of your family, meetings and contributions.",
    "Family register": "Keep generations connected through accurate, lasting records.",
    "Relationships and marriages": "Connect family members and preserve your shared lineage.",
    "Meetings": "Plan gatherings and keep every important detail together.",
    "Attendance": "Record participation, permissions and attendance history.",
    "Contributions": "Manage contribution periods with confidence and clarity.",
    "Contribution register": "Track each member's obligation, payments and outstanding balance.",
    "Payment history": "A complete record of installments and reversals.",
    "Gallery": "A home for the moments your family wants to remember.",
    "Family history": "Preserve the stories that connect one generation to the next.",
    "Reports": "Turn your family records into clear, shareable documents.",
    "Administrators": "Manage the people entrusted with your family's records.",
    "Audit log - recent 500 entries": "A transparent record of important application activity.",
    "Settings and backups": "Personalize your workspace and protect your records.",
}


def status_tone(status: str) -> str:
    if status in STATUS_TONES:
        return STATUS_TONES[status]
    if status.startswith("CREATE"):
        return "success"
    if status.startswith("UPDATE"):
        return "info"
    if status.startswith("ARCHIVE"):
        return "warning"
    return "info"


def apply_theme(root):
    c, style = COLORS, ttk.Style(root)
    style.theme_use("clam")
    root.configure(background=c["background"])
    root.option_add("*TCombobox*Listbox.background", c["surface"])
    root.option_add("*TCombobox*Listbox.foreground", c["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", c["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", c["primary"])
    style.configure(".", font=FONTS["body"], background=c["background"], foreground=c["text"])
    for name, bg in (("TFrame", "background"), ("Card.TFrame", "surface"),
                     ("Header.TFrame", "surface"), ("Sidebar.TFrame", "primary_dark")):
        style.configure(name, background=c[bg])
    style.configure("CardBorder.TFrame", background=c["surface"], borderwidth=1, relief="solid", bordercolor=c["border"])
    style.configure("SelectedCard.TFrame", background=c["surface"], borderwidth=2, relief="solid", bordercolor=c["accent"])
    style.configure("TLabel", background=c["background"], foreground=c["text"])
    for name, font, fg, bg in (
        ("Page.TLabel", "page", "primary", "background"), ("Subtitle.TLabel", "body", "text_secondary", "background"),
        ("Card.TLabel", "body", "text", "surface"), ("CardTitle.TLabel", "section", "primary", "surface"),
        ("CardHelper.TLabel", "small", "text_secondary", "surface"), ("Field.TLabel", "label", "text", "surface"),
        ("Stat.TLabel", "stat", "primary", "surface"), ("Header.TLabel", "label", "primary", "surface"),
        ("HeaderHelper.TLabel", "small", "text_secondary", "surface"),
        ("Brand.TLabel", "section", "surface", "primary_dark"),
        ("Sidebar.TLabel", "small", "sidebar_text", "primary_dark"),
        ("SidebarGroup.TLabel", "small", "gold", "primary_dark"),
    ):
        style.configure(name, font=FONTS[font], foreground=c[fg], background=c[bg])
    variants = {
        "PrimaryButton": ("accent", "surface", "accent_hover"),
        "SecondaryButton": ("surface_alt", "primary", "border"),
        "SuccessButton": ("success_text", "surface", "success"),
        "WarningButton": ("warning_bg", "warning_text", "gold"),
        "DangerButton": ("danger_text", "surface", "danger"),
        "GhostButton": ("surface", "primary", "accent_soft"),
    }
    for variant, (bg, fg, hover) in variants.items():
        name = variant + ".TButton"
        style.configure(name, background=c[bg], foreground=c[fg], font=FONTS["label"],
                        padding=(14, 9), borderwidth=0, focusthickness=2, focuscolor=c["gold"])
        style.map(name, background=[("disabled", c["surface_alt"]), ("pressed", c[hover]), ("active", c[hover])],
                  foreground=[("disabled", c["text_secondary"])])
    style.configure("TButton", **style.configure("SecondaryButton.TButton"))
    style.map("TButton", **style.map("SecondaryButton.TButton"))
    for name, bg in (("Nav.TButton", "primary_dark"), ("Selected.Nav.TButton", "accent")):
        style.configure(name, background=c[bg], foreground=c["sidebar_text"], anchor="w",
                        font=FONTS["body"], padding=(16, 9), borderwidth=0, focusthickness=1, focuscolor=c["gold"])
        style.map(name, background=[("active", c["primary"] if bg == "primary_dark" else c["accent_hover"])],
                  foreground=[("active", c["surface"])])
    style.configure("Treeview", background=c["surface"], fieldbackground=c["surface"], foreground=c["text"],
                    rowheight=34, borderwidth=0, font=FONTS["body"])
    style.configure("Treeview.Heading", background=c["surface_alt"], foreground=c["primary"],
                    font=FONTS["label"], padding=(12, 12), relief="flat", borderwidth=0)
    style.map("Treeview", background=[("selected", c["selection"])], foreground=[("selected", c["primary"])])
    style.map("Treeview.Heading", background=[("active", c["border"])])
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=c["surface"], foreground=c["text"], padding=(10, 8),
                        bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"],
                        selectbackground=c["selection"], selectforeground=c["primary"],
                        arrowcolor=c["primary"], background=c["surface"])
        style.map(name, bordercolor=[("focus", c["accent"])],
                  fieldbackground=[("disabled", c["surface_alt"]), ("readonly", c["surface"])],
                  foreground=[("disabled", c["text_secondary"]), ("readonly", c["text"])])
    style.configure("TCheckbutton", background=c["surface"], foreground=c["text"], padding=(0, 5))
    style.map("TCheckbutton", background=[("active", c["surface"])], indicatorbackground=[("selected", c["accent"])])
    style.configure("TNotebook", background=c["background"], borderwidth=0, tabmargins=(0, 0, 0, 8))
    style.configure("TNotebook.Tab", padding=(20, 10), background=c["surface_alt"], foreground=c["text_secondary"])
    style.map("TNotebook.Tab", background=[("selected", c["surface"])], foreground=[("selected", c["accent"])])
    for name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(name, background=c["border"], troughcolor=c["background"], borderwidth=0,
                        arrowcolor=c["text_secondary"], arrowsize=12)
        style.map(name, background=[("active", c["disabled"])])
    style.configure("TSeparator", background=c["border"])
    style.configure("Horizontal.TScale", background=c["accent"], troughcolor=c["surface_alt"], bordercolor=c["border"], lightcolor=c["accent"], darkcolor=c["accent"], borderwidth=0)
    style.map("Horizontal.TScale", background=[("active", c["accent_hover"])])
    style.configure("TProgressbar", background=c["accent"], troughcolor=c["accent_soft"], borderwidth=0)
    return style


def style_text(widget, *, reading=False):
    widget.configure(background=COLORS["surface"], foreground=COLORS["text"],
                     insertbackground=COLORS["accent"], selectbackground=COLORS["selection"],
                     selectforeground=COLORS["primary"], relief="flat", borderwidth=0,
                     highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
                     font=FONTS["reading" if reading else "body"], padx=12, pady=10,
                     spacing1=3, spacing3=5)


class CardFrame(ttk.Frame):
    def __init__(self, parent, *, padding=20, **kwargs):
        super().__init__(parent, style="CardBorder.TFrame", padding=padding, **kwargs)


class SectionCard(CardFrame):
    def __init__(self, parent, title, subtitle=None, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 6))
        if subtitle:
            label = ttk.Label(self, text=subtitle, style="CardHelper.TLabel", wraplength=500)
            label.pack(anchor="w", pady=(0, 12))
            self.bind("<Configure>", lambda e: label.configure(wraplength=max(120, e.width-40)), add="+")
        self.body = ttk.Frame(self, style="Card.TFrame")
        self.body.pack(fill="both", expand=True)


class StatusBadge(tk.Label):
    def __init__(self, parent, text="", tone=None, **kwargs):
        super().__init__(parent, font=FONTS["small"], padx=9, pady=4, **kwargs)
        self.set(text, tone)

    def set(self, text, tone=None):
        tone = tone or status_tone(text)
        backgrounds = {"accent": "accent_soft", "gold": "warning_bg", "muted": "surface_alt"}
        foregrounds = {"success": "success_text", "warning": "warning_text", "danger": "danger_text",
                       "gold": "primary", "muted": "text_secondary"}
        self.configure(text=text.replace("_", " "), background=COLORS[backgrounds.get(tone, tone+"_bg")],
                       foreground=COLORS[foregrounds.get(tone, tone)])


class StatCard(CardFrame):
    def __init__(self, parent, label, value="--", *, tone="accent", helper=""):
        super().__init__(parent, padding=(18, 16))
        tk.Frame(self, background=COLORS[tone], height=3).pack(fill="x", pady=(0, 12))
        ttk.Label(self, text=label, style="CardHelper.TLabel").pack(anchor="w")
        self.value = ttk.Label(self, text=value, style="Stat.TLabel")
        self.value.pack(anchor="w", pady=(4, 2))
        self.helper = ttk.Label(self, text=helper, style="CardHelper.TLabel")
        self.helper.pack(anchor="w")
        self.bind("<Configure>", self._fit)

    def _fit(self, event):
        from tkinter.font import Font
        width = max(100, event.width - 36)
        size = FONTS["stat"][1]
        while size > 15 and Font(self, family=FONTS["stat"][0], size=size).measure(self.value.cget("text")) > width:
            size -= 1
        self.value.configure(font=(FONTS["stat"][0], size))

    def set(self, value, helper=None):
        self.value.configure(text=str(value))
        if helper is not None:
            self.helper.configure(text=helper)
        self._fit(type("Size", (), {"width": self.winfo_width()})())


class ResponsiveGrid(ttk.Frame):
    def __init__(self, parent, *, minimum=220, maximum=4):
        super().__init__(parent)
        self.minimum, self.maximum, self.items, self._columns = minimum, maximum, [], 0
        self.bind("<Configure>", self.reflow)

    def add(self, widget):
        self.items.append(widget)
        self._columns = 0
        self.after_idle(self.reflow)
        return widget

    def reflow(self, event=None):
        if not self.winfo_exists():
            return
        count = max(1, min(self.maximum, max(self.winfo_width(), self.minimum)//self.minimum))
        if count == self._columns:
            return
        for column in range(self.maximum):
            self.columnconfigure(column, weight=1 if column < count else 0, uniform="cards")
        for index, widget in enumerate(self.items):
            widget.grid(row=index//count, column=index%count, sticky="nsew", padx=(0, 12), pady=(0, 12))
        self._columns = count


class ScrollArea(ttk.Frame):
    def __init__(self, parent, *, sidebar=False):
        super().__init__(parent, style="Sidebar.TFrame" if sidebar else "TFrame")
        self.canvas = tk.Canvas(self, background=COLORS["primary_dark" if sidebar else "background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.body = ttk.Frame(self.canvas, style="Sidebar.TFrame" if sidebar else "TFrame")
        window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-int(e.delta/120), "units"))
        self.bind("<Enter>", self._bind_wheel)
        self.after_idle(self._bind_wheel)

    def _bind_wheel(self, event=None):
        def bind_children(widget):
            # Keep native scrolling inside tables and text editors.
            if not isinstance(widget, (ttk.Treeview, tk.Text, ttk.Combobox)) and not getattr(widget, "_card_wheel_bound", False):
                widget.bind("<MouseWheel>", self._wheel, add="+")
                widget._card_wheel_bound = True
                widget.bind("<FocusIn>", self._reveal_focus, add="+")
            for child in widget.winfo_children():
                bind_children(child)
        bind_children(self.body)

    def _reveal_focus(self, event):
        widget = event.widget
        top = widget.winfo_rooty() - self.body.winfo_rooty()
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        height = max(1, self.body.winfo_height())
        if top < visible_top:
            self.canvas.yview_moveto(max(0, top - 12) / height)
        elif top + widget.winfo_height() > visible_bottom:
            self.canvas.yview_moveto((top + widget.winfo_height() + 12 - self.canvas.winfo_height()) / height)

    def _wheel(self, event):
        self.canvas.yview_scroll(-int(event.delta/120), "units")
        return "break"
