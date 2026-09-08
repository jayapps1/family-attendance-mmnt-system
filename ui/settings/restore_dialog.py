"""A reviewed backup and explicit confirmation precede every live restore."""
import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import COLORS, SectionCard
from services.restore_service import RestoreService


def show_restore(app):
    service = RestoreService(app.services["backup"])
    app.run(service.preview_latest, lambda preview: RestoreDialog(app, service, preview))


class RestoreDialog(tk.Toplevel):
    def __init__(self, app, service, preview):
        super().__init__(app)
        self.app, self.service, self.preview_data = app, service, preview
        self.title("Restore latest backup")
        self.geometry("670x570")
        self.configure(background=COLORS["background"])
        self.transient(app)
        self.grab_set()
        card = SectionCard(self, "Restore your family records", "Review this backup before replacing the current database.")
        card.pack(fill="both", expand=True, padx=24, pady=24)
        details = (f'Backup: {preview["name"]}\nCreated: {preview["created_at"]}\n'
                   f'Media files: {preview["media_count"]}\nSize: {preview["size"] / 1024:,.1f} KB')
        ttk.Label(card.body, text=details, style="Card.TLabel", wraplength=570, justify="left").pack(anchor="w", pady=12)
        tk.Label(card.body, text="Changes made after this backup will be replaced.\n"
                 "A safety backup of your current records is created first.\n"
                 "Close other app windows and database tools before continuing.",
                 background=COLORS["warning_bg"], foreground=COLORS["warning_text"],
                 padx=14, pady=14, justify="left", wraplength=530).pack(fill="x", pady=12)
        ttk.Label(card.body, text="Keep the original .env encryption key. Sign in again after restore.",
                  style="CardHelper.TLabel", wraplength=550).pack(anchor="w", pady=(0, 12))
        ttk.Label(card.body, text="Type RESTORE to confirm", style="Field.TLabel").pack(anchor="w")
        self.confirmation = ttk.Entry(card.body)
        self.confirmation.pack(fill="x", pady=8)
        self.progress = ttk.Label(card.body, text="", style="CardHelper.TLabel")
        self.progress.pack(anchor="w", pady=8)
        self.button = ttk.Button(card.body, text="Restore this backup", style="DangerButton.TButton", command=self.submit)
        self.button.pack(side="right")
        self.cancel = ttk.Button(card.body, text="Cancel", command=self.destroy)
        self.cancel.pack(side="right", padx=8)

    def submit(self):
        if self.confirmation.get() != "RESTORE":
            messagebox.showerror("Confirm restore", "Type RESTORE exactly to continue.", parent=self)
            return
        if self.app.identity and self.app.identity.expired(self.app.timeout_minutes):
            self.app.logout()
            return
        if self.app.pending:
            messagebox.showinfo("Work in progress", "Wait for the current operation, then try again.", parent=self)
            return
        self.button.configure(state="disabled")
        self.cancel.configure(state="disabled")
        self.confirmation.configure(state="disabled")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.progress.configure(text="Creating safety backup and restoring. Please keep the app open.")
        preview = self.preview_data
        self.app.run(lambda: self.service.restore(preview["path"], preview["sha256"], "RESTORE"), self.done, self.failed)
        self.app.maintenance = True

    def failed(self):
        self.app.maintenance = False
        if self.app.identity:
            self.app.identity.touch()
        self.button.configure(state="normal")
        self.cancel.configure(state="normal")
        self.confirmation.configure(state="normal")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.progress.configure(text="Restore did not finish. Review the error before retrying.")

    def done(self, result):
        self.app.maintenance = False
        self.app.identity = None
        self.app.auth.pending.clear()
        self.destroy()
        messagebox.showinfo("Restore complete",
                            "The backup has been restored. Sign in again.\n\nSafety backup:\n" + result["safety_backup"] + ("\n\n" + "\n".join(result.get("warnings", [])) if result.get("warnings") else ""),
                            parent=self.app)
        self.app.show_login()
