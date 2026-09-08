"""Reusable ttk tables and typed forms; no database access."""
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox


def display(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value)


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"
    choices: dict | None = None
    required: bool = False


class FormDialog(tk.Toplevel):
    def __init__(self, app, title, fields, save, initial=None, success=None):
        super().__init__(app)
        self.app, self.fields, self.save, self.success = app, fields, save, success
        self.title(title)
        self.transient(app)
        self.geometry("600x650")
        self.minsize(440, 360)
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        self.inputs = {}
        for index, field in enumerate(fields):
            ttk.Label(body, text=field.label + (" *" if field.required else "")).grid(row=index*2, column=0, sticky="w", pady=(10, 3))
            value = (initial or {}).get(field.name)
            if field.kind == "multiline":
                widget = tk.Text(body, height=5, wrap="word", width=48)
                widget.insert("1.0", display(value))
            elif field.kind == "bool":
                variable = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(body, variable=variable)
                widget.variable = variable
            elif field.choices is not None:
                widget = ttk.Combobox(body, values=list(field.choices), state="readonly")
                label = next((label for label, option in field.choices.items() if option == value), "")
                widget.set(label)
            else:
                widget = ttk.Entry(body, show="*" if field.kind == "secret" else "")
                widget.insert(0, display(value))
            widget.grid(row=index*2+1, column=0, sticky="ew")
            self.inputs[field.name] = widget
        body.columnconfigure(0, weight=1)
        controls = ttk.Frame(self, padding=12)
        controls.pack(fill="x")
        self.button = ttk.Button(controls, text="Save", command=self.submit)
        self.button.pack(side="right")
        ttk.Button(controls, text="Cancel", command=self.destroy).pack(side="right", padx=8)
        self.grab_set()

    def values(self):
        result = {}
        for field in self.fields:
            widget = self.inputs[field.name]
            if field.kind == "bool":
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
        super().__init__(parent)
        self.columns, self.rows = columns, {}
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode=selectmode)
        for column in columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=150, minwidth=90)
        vertical = ttk.Scrollbar(self, command=self.tree.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for index, row in enumerate(rows):
            key = str(index)
            self.rows[key] = row
            self.tree.insert("", "end", iid=key, values=[display(row.get(c)) for c in self.columns])

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError("Select a row first")
        return self.rows[selected[0]]

    def selections(self):
        return [self.rows[key] for key in self.tree.selection()]


class Screen(ttk.Frame):
    def __init__(self, app, title):
        super().__init__(app.content, padding=20)
        self.app = app
        ttk.Label(self, text=title, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 14))
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill="x", pady=(0, 12))

    def button(self, text, command):
        def guarded():
            try:
                command()
            except (ValueError, KeyError) as exc:
                messagebox.showerror("Check selection", str(exc), parent=self)
        ttk.Button(self.toolbar, text=text, command=guarded).pack(side="left", padx=(0, 6))

    def table(self, columns, **kwargs):
        table = TableView(self, columns, **kwargs)
        table.pack(fill="both", expand=True)
        return table

    def show_text(self, title, text):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("780x560")
        widget = tk.Text(dialog, wrap="word", padx=16, pady=16)
        widget.pack(fill="both", expand=True)
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def options(rows, label="title"):
    return {str(row.get(label) or row.get("name") or "Record") + " [" + str(row["id"])[:8] + "]": row["id"] for row in rows}


def member_options(rows):
    return {f'{r["family_number"]} - {r["first_name"]} {r["last_name"]}': r["id"] for r in rows}


def enum_options(enum_class):
    return {item.value.replace("_", " ").title(): item.value for item in enum_class}
