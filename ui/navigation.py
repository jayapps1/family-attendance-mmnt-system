"""Shared navigation for existing frames and detail windows; never creates a root."""
import tkinter as tk
from tkinter import ttk


def navigation_buttons(parent, app, back=None):
    controls = ttk.Frame(parent)
    ttk.Button(controls, text='Back', command=back or app.back, style='SecondaryButton.TButton').pack(side='left', padx=(0,8))
    ttk.Button(controls, text='Home', command=app.home, style='PrimaryButton.TButton').pack(side='left')
    return controls


def dialog_navigation(dialog, app):
    parents = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel) and w is not dialog and w.winfo_exists()]
    origin = parents[-1] if parents else app
    dialog.transient(origin)
    def back():
        dialog.destroy()
        if origin.winfo_exists(): origin.lift()
    navigation_buttons(dialog, app, back).pack(anchor='e',padx=24,pady=(12,0))
