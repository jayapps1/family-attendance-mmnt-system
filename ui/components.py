"""Reusable ttk tables and typed forms; no database access."""
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import (COLORS, FONTS, PAGE_HELP, CardFrame, SectionCard, StatusBadge, ScrollArea, style_text)


def display(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"GHS {value:,.2f}"
    if isinstance(value, str) and value in {"LINEAGE_MEMBER", "MARRIED_IN"}:
        from utils.family_labels import affiliation_label
        return affiliation_label(value)
    return str(value)


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"
    choices: dict | None = None
    required: bool = False
    section: str = ""


class FormDialog(tk.Toplevel):
    def __init__(self, app, title, fields, save, initial=None, success=None, *, save_label="Save", button_style="PrimaryButton.TButton"):
        super().__init__(app)
        self.app, self.fields, self.save, self.success = app, fields, save, success
        self.title(title)
        self.transient(app)
        self.configure(background=COLORS["background"])
        columns = 2 if len(fields) > 5 else 1
        self.geometry("820x720" if columns == 2 else "580x650")
        self.minsize(720 if columns == 2 else 480, 420)
        header = ttk.Frame(self, padding=(24, 20))
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Page.TLabel").pack(anchor="w")
        ttk.Label(header, text="Fields marked * are required.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))
        area = ScrollArea(self)
        area.pack(fill="both", expand=True, padx=24)
        self.inputs = {}
        groups = {}
        for field in fields:
            groups.setdefault(field.section or "Details", []).append(field)
        for title, group in groups.items():
            card = SectionCard(area.body, title, padding=20)
            card.pack(fill="x", pady=(0, 16))
            for column in range(columns):
                card.body.columnconfigure(column, weight=1, uniform="fields")
            position = 0
            for field in group:
                span = columns if field.kind in ("multiline", "photo") else 1
                if span == columns and position % columns:
                    position += columns - position % columns
                row, column = divmod(position, columns)
                cell = ttk.Frame(card.body, style="Card.TFrame", padding=(0, 0, 12 if columns == 2 else 0, 14))
                cell.grid(row=row, column=column, columnspan=span, sticky="nsew")
                label = ttk.Frame(cell, style="Card.TFrame")
                label.pack(fill="x", pady=(0, 6))
                ttk.Label(label, text=field.label, style="Field.TLabel").pack(side="left")
                if field.required:
                    tk.Label(label, text=" *", foreground=COLORS["danger"], background=COLORS["surface"], font=FONTS["label"]).pack(side="left")
                value = (initial or {}).get(field.name)
                value_text = str(value) if isinstance(value, Decimal) else display(value)
                if field.kind == 'display':
                    widget = ttk.Label(cell, text=value_text, style='Card.TLabel', wraplength=330)
                    widget.get = lambda w=widget: str(w.cget('text'))
                elif field.kind == "photo":
                    from ui.family.photo_picker import PhotoPicker
                    widget = PhotoPicker(cell, app, value)
                elif field.kind == "multiline":
                    widget = tk.Text(cell, height=5, wrap="word", width=30)
                    style_text(widget)
                    widget.insert("1.0", value_text)
                elif field.kind == "bool":
                    variable = tk.BooleanVar(value=bool(value))
                    widget = ttk.Checkbutton(cell, text=field.label, variable=variable)
                    widget.variable = variable
                elif field.choices is not None:
                    widget = ttk.Combobox(cell, values=list(field.choices), state="readonly", width=20)
                    widget.set(next((label for label, option in field.choices.items() if option == value), ""))
                else:
                    widget = ttk.Entry(cell, show="*" if field.kind == "secret" else "", width=22)
                    widget.insert(0, value_text)
                widget.pack(fill="x")
                self.inputs[field.name] = widget
                position += span
        controls = CardFrame(self, padding=(24, 16))
        controls.pack(fill="x", pady=(12, 0))
        self.button = ttk.Button(controls, text=save_label, command=self.submit, style=button_style)
        self.button.pack(side="right")
        ttk.Button(controls, text="Cancel", command=self.destroy, style="SecondaryButton.TButton").pack(side="right", padx=8)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

    def values(self):
        result = {}
        for field in self.fields:
            widget = self.inputs[field.name]
            if field.kind == "photo":
                value = widget.get()
            elif field.kind == "bool":
                value = widget.variable.get()
            else:
                value = widget.get("1.0", "end-1c").strip() if field.kind == "multiline" else widget.get().strip()
                if field.required and not value:
                    raise ValueError(field.label + " is required")
                if field.choices is not None:
                    value = field.choices.get(value)
                elif not value:
                    value = None
                elif field.kind == "date":
                    value = date.fromisoformat(value)
                elif field.kind == "time":
                    value = time.fromisoformat(value)
                elif field.kind == "int":
                    value = int(value)
                elif field.kind == "money":
                    value = Decimal(value)
            result[field.name] = value
        return result

    def submit(self):
        try:
            values = self.values()
        except (ValueError, InvalidOperation) as exc:
            messagebox.showerror("Check form", str(exc) + "\nDates: YYYY-MM-DD. Times: HH:MM.", parent=self)
            return
        self.button.configure(state="disabled")
        def done(result):
            if self.winfo_exists():
                self.destroy()
            if self.success:
                self.success(result)
            else:
                self.app.refresh()
        def failed():
            if self.winfo_exists():
                self.button.configure(state="normal")
        self.app.run(lambda: self.save(values), done, failed)


class TableView(ttk.Frame):
    def __init__(self, parent, columns, *, selectmode="browse"):
        super().__init__(parent, style="Card.TFrame", padding=1)
        self.columns, self.rows = columns, {}
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode=selectmode)
        labels = {"affiliation_type": "Affiliation", "family_number": "Family No.", "phone_number": "Phone", "current_residence": "Residence",
                  "full_name": "Name", "amount_per_member": "Per member", "is_active": "Active", "totp_enabled": "Enrolled", "amount_due": "Amount due",
                  "amount_paid": "Amount paid", "total_paid": "Amount paid", "outstanding": "Balance"}
        for column in columns:
            self.tree.heading(column, text=labels.get(column, column.replace("_", " ").title()))
            self.tree.column(column, width=160 if column in {"title", "member", "email", "full_name"} else 130,
                             minwidth=85, anchor="e" if column in {"amount_due", "amount_paid", "total_paid", "outstanding"} else "w")
        vertical = ttk.Scrollbar(self, command=self.tree.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.empty = ttk.Label(self, text="No records to display. Use the actions above to get started.", style="CardHelper.TLabel", anchor="center")
        footer = CardFrame(self, padding=(12, 8))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.count = ttk.Label(footer, text="0 records", style="CardHelper.TLabel")
        self.count.pack(side="left")
        self.badge = StatusBadge(footer, "")
        self.affiliation_badge = StatusBadge(footer, "")
        self.tree.tag_configure("even", background=COLORS["surface"])
        self.tree.tag_configure("odd", background=COLORS["alternate"])
        self.tree.bind("<<TreeviewSelect>>", self._selection)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for index, row in enumerate(rows):
            key = str(index)
            self.rows[key] = row
            values = []
            for column in self.columns:
                value = row.get(column)
                if column == "full_name":
                    value = " ".join(str(row.get(k) or "") for k in ("first_name", "middle_name", "last_name")).strip()
                elif column == "is_active":
                    value = "ACTIVE" if value else "INACTIVE"
                elif column == "is_reversed":
                    value = "REVERSED" if value else "VALID"
                elif column == "totp_enabled":
                    value = "VERIFIED" if value else "PENDING"
                values.append(display(value))
            self.tree.insert("", "end", iid=key, values=values, tags=("odd" if index % 2 else "even",))
        self.count.configure(text=f"{len(self.rows):,} record" + ("" if len(self.rows) == 1 else "s"))
        self.badge.pack_forget()
        self.affiliation_badge.pack_forget()
        if self.rows:
            self.empty.grid_forget()
        else:
            self.empty.grid(row=0, column=0, pady=(60, 0), sticky="n")

    def _selection(self, event=None):
        if not self.tree.selection():
            self.badge.pack_forget()
            self.affiliation_badge.pack_forget()
            return
        row = self.selected()
        self.affiliation_badge.pack_forget()
        if row.get('affiliation_type'):
            self.affiliation_badge.set(display(row['affiliation_type']), 'info' if row['affiliation_type'] == 'LINEAGE_MEMBER' else 'gold')
            self.affiliation_badge.pack(side='right', padx=6)
        status = "REVERSED" if row.get("is_reversed") else row.get("status") or row.get("living_status") or row.get("role") or row.get("action")
        if status:
            self.badge.set(str(status))
            self.badge.pack(side="right")

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError("Select a row first")
        return self.rows[selected[0]]

    def selections(self):
        return [self.rows[key] for key in self.tree.selection()]


class ActionBar(ttk.Frame):
    """Wrap existing packed controls into grid rows when space is limited."""
    def __init__(self, parent):
        super().__init__(parent)
        self._layout = None
        self.bind("<Configure>", lambda e: self.after_idle(self.reflow))

    def reflow(self):
        if not self.winfo_exists() or self.winfo_width() < 100:
            return
        children = self.winfo_children()
        signature = (self.winfo_width(), tuple((str(w), w.winfo_reqwidth()) for w in children))
        if signature == self._layout:
            return
        self._layout = signature
        for child in children:
            child.pack_forget()
            child.grid_forget()
        row = column = used = 0
        for child in children:
            width = child.winfo_reqwidth() + 8
            if used and used + width > self.winfo_width():
                row, column, used = row + 1, 0, 0
            child.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 8))
            used, column = used + width, column + 1


class Screen(ttk.Frame):
    def __init__(self, app, title):
        super().__init__(app.content, padding=(24, 20))
        self.app = app
        if hasattr(app, "page_title"):
            app.page_title.set(title.split(" - ")[0])
        self.page_header = ttk.Frame(self)
        self.page_header.pack(fill="x", pady=(0, 18))
        ttk.Label(self.page_header, text=title, style="Page.TLabel").pack(anchor="w")
        if title in PAGE_HELP:
            ttk.Label(self.page_header, text=PAGE_HELP[title], style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))
        self.toolbar = ActionBar(self)
        self.toolbar.pack(fill="x", pady=(0, 8))

    def button(self, text, command, *, variant=None):
        def guarded():
            try:
                command()
            except (ValueError, KeyError) as exc:
                messagebox.showerror("Check selection", str(exc), parent=self)
        if variant is None:
            lower = text.lower()
            variant = ("Danger" if any(word in lower for word in ("reverse", "restart authenticator")) else
                       "Warning" if any(word in lower for word in ("archive", "close period")) else
                       "Primary" if lower.startswith(("add", "new", "create", "record", "upload", "generate")) else "Secondary")
        button = ttk.Button(self.toolbar, text=text, command=guarded, style=variant+"Button.TButton")
        button.pack(side="left", padx=(0, 6))
        return button

    def table(self, columns, **kwargs):
        table = TableView(self, columns, **kwargs)
        table.pack(fill="both", expand=True, pady=(0, 12))
        return table

    def show_text(self, title, text):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("820x620")
        dialog.minsize(640, 440)
        dialog.configure(background=COLORS["background"])
        card = SectionCard(dialog, title, padding=24)
        card.pack(fill="both", expand=True, padx=24, pady=24)
        widget = tk.Text(card.body, wrap="word")
        style_text(widget, reading=True)
        scrollbar = ttk.Scrollbar(card.body, command=widget.yview)
        widget.configure(yscrollcommand=scrollbar.set)
        widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        widget.insert("1.0", text)
        widget.configure(state="disabled")
        return dialog


def show_details(parent, title, values, *, statistics=False):
    from ui.theme import ResponsiveGrid, StatCard, status_tone
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("860x640")
    dialog.configure(background=COLORS["background"])
    ttk.Label(dialog, text=title, style="Page.TLabel", padding=24).pack(anchor="w")
    area = ScrollArea(dialog)
    area.pack(fill="both", expand=True, padx=24, pady=(0, 24))
    grid = ResponsiveGrid(area.body, minimum=240, maximum=3 if statistics else 2)
    grid.pack(fill="x")
    for key, value in values.items():
        if key == "id":
            continue
        label = key.replace("_", " ").title()
        if statistics:
            tone = status_tone(key.upper())
            grid.add(StatCard(grid, label, display(value) + ("%" if "percentage" in key else ""), tone=tone if tone != "muted" else "text_secondary"))
        else:
            card = grid.add(SectionCard(grid, label))
            ttk.Label(card.body, text=display(value) or "--", wraplength=330, style="Card.TLabel").pack(anchor="w")
    return dialog


def options(rows, label="title"):
    return {str(row.get(label) or row.get("name") or "Record") + " [" + str(row["id"])[:8] + "]": row["id"] for row in rows}


def member_options(rows):
    return {f'{r["family_number"]} - {r["first_name"]} {r["last_name"]}': r["id"] for r in rows}


def enum_options(enum_class):
    return {item.value.replace("_", " ").title(): item.value for item in enum_class}
