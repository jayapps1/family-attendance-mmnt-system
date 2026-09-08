from tkinter import ttk, messagebox, filedialog
from ui.components import Screen, Field, FormDialog
from services.settings_service import SettingsService


class SettingsScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Settings and backups")
        self.button("Set configuration", self.edit)
        self.button("Back up database and media", self.backup)
        self.button("Sync backups to Drive", self.sync_latest)
        self.button("Restore latest backup", self.restore, variant="Danger")
        self.button("Google Drive folder", self.drive_settings)
        from ui.theme import ResponsiveGrid, SectionCard
        categories = ResponsiveGrid(self, minimum=220, maximum=3)
        categories.pack(fill="x", pady=(0, 12))
        for title, description, key in (("Family & organization", "Name, numbering and contact details.", "family_name"),
                                        ("Reports & contributions", "Report identity and default amounts.", "report_header"),
                                        ("Security & backups", "Session timeout and backup frequency.", "session_timeout_minutes")):
            card = categories.add(SectionCard(categories, title, description))
            ttk.Button(card.body, text="Configure", command=lambda k=key: self.edit(k)).pack(anchor="w")
        from services.drive_backup import DRIVE_FOLDER_URL
        import webbrowser
        ttk.Button(self, text="Open Google Drive backups", style="GhostButton.TButton", command=lambda: webbrowser.open(DRIVE_FOLDER_URL)).pack(anchor="w", pady=(0, 8))
        ttk.Label(self, text="Backups include the database and media. Keep a separate secure copy of your .env encryption key.",
                  style="Subtitle.TLabel", wraplength=800).pack(anchor="w", pady=(0, 16))
        self.grid = self.table(("setting_key", "setting_value", "description"))
        app.run(app.services["settings"].list, self.grid.set_rows)

    def edit(self, key=None):
        FormDialog(self.app, "Application setting", [
            Field("key", "Setting", choices={k.replace("_", " ").title(): k for k in sorted(SettingsService.KEYS)}, required=True),
            Field("value", "Value", required=True)],
            lambda values: self.app.services["settings"].set(**values), success=self.saved, initial={"key": key})

    def saved(self, _):
        def apply(rows):
            self.app.apply_settings(rows)
            self.app.refresh()
        self.app.run(self.app.services["settings"].list, apply)

    def drive_settings(self):
        def choose(_):
            from pathlib import Path
            from config.settings import BASE_DIR
            from dotenv import set_key
            import os
            folder = filedialog.askdirectory(parent=self, title="Select the backup folder inside Google Drive for desktop")
            if not folder:
                return
            def save():
                service = self.app.services["backup"]
                with service.transaction(super_admin=True):
                    pass
                if not Path(folder).is_dir():
                    raise ValueError("The selected folder is unavailable.")
                set_key(str(BASE_DIR / ".env"), "GOOGLE_DRIVE_BACKUP_DIR", folder)
                os.environ["GOOGLE_DRIVE_BACKUP_DIR"] = folder
                service.drive_folder = Path(folder)
            self.app.run(save, lambda _: messagebox.showinfo("Drive folder saved", "Future backups will be copied here for Google Drive for desktop to sync:\n" + folder, parent=self))
        def authorize():
            with self.app.services["backup"].transaction(super_admin=True):
                pass
        self.app.run(authorize, choose)

    def sync_latest(self):
        service = self.app.services["backup"]
        self.app.run(service.sync_all,
                     lambda count: messagebox.showinfo("Drive copies verified", f"{count} backup(s) verified in Google Drive for desktop. Cloud upload follows its sync status.", parent=self))

    def restore(self):
        from ui.settings.restore_dialog import show_restore
        show_restore(self.app)

    def backup(self):
        self.app.run(self.app.services["backup"].create,
                     lambda path: messagebox.showinfo("Backup verified", "Verified local backup:\n" + path + ("\n\nAlso copied to Google Drive for desktop. Check its sync status for cloud upload completion." if self.app.services["backup"].drive_folder else "\n\nSet your Google Drive folder to enable a cloud copy."), parent=self))
