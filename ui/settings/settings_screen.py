from tkinter import ttk, messagebox
from ui.components import Screen, Field, FormDialog
from services.settings_service import SettingsService


class SettingsScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Settings and backups")
        self.button("Set configuration", self.edit)
        self.button("Back up database and media", self.backup)
        ttk.Label(self, text="Backups include the database and media. Keep a separate secure copy of your .env encryption key.",
                  wraplength=800).pack(anchor="w", pady=10)
        self.grid = self.table(("setting_key", "setting_value", "description"))
        app.run(app.services["settings"].list, self.grid.set_rows)

    def edit(self):
        FormDialog(self.app, "Application setting", [
            Field("key", "Setting", choices={k.replace("_", " ").title(): k for k in sorted(SettingsService.KEYS)}, required=True),
            Field("value", "Value", required=True)],
            lambda values: self.app.services["settings"].set(**values), success=self.saved)

    def saved(self, _):
        def apply(rows):
            self.app.apply_settings(rows)
            self.app.refresh()
        self.app.run(self.app.services["settings"].list, apply)

    def backup(self):
        self.app.run(self.app.services["backup"].create,
                     lambda path: messagebox.showinfo("Backup verified", path, parent=self))
