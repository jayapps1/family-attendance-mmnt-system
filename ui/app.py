"""One Tk root, one background work queue, and service-backed navigation."""
from concurrent.futures import ThreadPoolExecutor
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy.exc import SQLAlchemyError
from config.settings import BASE_DIR, MEDIA_ROOT, BACKUP_ROOT, SESSION_TIMEOUT_MINUTES
from config.database import SessionLocal, DATABASE_URL
from services.auth_service import AuthService
from services.family_service import FamilyService
from services.relationship_service import RelationshipService
from services.meeting_service import MeetingService
from services.attendance_service import AttendanceService
from services.contribution_service import ContributionService
from services.gallery_service import GalleryService
from services.history_service import HistoryService
from services.admin_service import AdminService
from services.audit_service import AuditService
from services.settings_service import SettingsService
from services.report_service import ReportService
from services.backup_service import BackupService
from utils.security import encryption_box


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Family Management")
        self.geometry("1380x820")
        self.minsize(1100, 680)
        self.media_root = MEDIA_ROOT
        self.identity, self.screen, self.screen_factory = None, None, None
        self.services, self.generation, self.pending = {}, 0, []
        self.timeout_minutes = SESSION_TIMEOUT_MINUTES
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="family-work")
        self.auth = AuthService(SessionLocal, lambda create=False: encryption_box(BASE_DIR / ".env", allow_create=create))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=28)
        style.configure("TButton", padding=(10, 6))
        self.sidebar = ttk.Frame(self, padding=12, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.content = ttk.Frame(self)
        self.content.pack(side="top", fill="both", expand=True)
        self.status = tk.StringVar(value="Starting...")
        ttk.Label(self, textvariable=self.status, padding=8).pack(side="bottom", fill="x")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind_all("<KeyPress>", self.activity, add="+")
        self.bind_all("<ButtonPress>", self.activity, add="+")
        self.after(80, self.poll)
        self.after(1000, self.check_timeout)
        self.show_login()

    def show_login(self):
        from ui.auth.login_window import LoginView
        self.identity = None
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        self.show(lambda app: ttk.Label(app.content, text="Checking administrator setup...", padding=30))
        self.run(self.auth.needs_bootstrap, lambda needed: self.show(lambda app: LoginView(app, needed)))

    def show(self, factory):
        self.generation += 1
        if self.screen is not None:
            self.screen.destroy()
        self.screen_factory = factory
        self.screen = factory(self)
        self.screen.pack(fill="both", expand=True)

    def refresh(self):
        if self.screen_factory:
            self.show(self.screen_factory)

    def run(self, work, success=None, failure=None, *, session_wide=False):
        if self.identity and self.identity.expired(self.timeout_minutes):
            self.logout()
            return
        generation = ("session", self.identity) if session_wide else self.generation
        self.status.set("Working...")
        # No Tk calls happen in worker functions or future callbacks.
        future = self.executor.submit(work)
        self.pending.append((future, generation, success, failure))

    def callback_is_current(self, scope):
        if isinstance(scope, tuple):
            return scope[1] is self.identity and self.identity is not None
        return scope == self.generation

    def poll(self):
        batch, self.pending = self.pending, []
        for future, generation, success, failure in batch:
            if not future.done():
                self.pending.append((future, generation, success, failure))
                continue
            if future.cancelled():
                continue
            try:
                result = future.result()
                if self.callback_is_current(generation) and success:
                    success(result)
            except Exception as exc:
                logging.error("Operation failed (%s)", type(exc).__name__)
                if self.callback_is_current(generation):
                    message = "Database operation failed. Check the connection and migrations." if isinstance(exc, SQLAlchemyError) else str(exc)
                    messagebox.showerror("Unable to complete operation", message, parent=self)
                    if failure:
                        failure()
            if getattr(self, "_closing", False):
                return
        self.status.set("Working..." if self.pending else "Ready")
        self.after(80, self.poll)

    def signed_in(self, identity):
        self.identity = identity
        context = (SessionLocal, identity.user_id)
        self.services = {
            "family": FamilyService(*context), "relationships": RelationshipService(*context),
            "meetings": MeetingService(*context), "attendance": AttendanceService(*context),
            "contributions": ContributionService(*context), "gallery": GalleryService(*context, MEDIA_ROOT),
            "history": HistoryService(*context, MEDIA_ROOT), "admins": AdminService(*context),
            "audit": AuditService(*context), "settings": SettingsService(*context),
            "reports": ReportService(*context, BASE_DIR / "reports"),
            "backup": BackupService(*context, DATABASE_URL, MEDIA_ROOT, BACKUP_ROOT),
        }
        from ui.dashboard.dashboard import Dashboard
        from ui.family.family_register import FamilyRegister
        from ui.meetings.meeting_list import MeetingList
        from ui.attendance.attendance_screen import AttendanceScreen
        from ui.contributions.contribution_dashboard import ContributionDashboard
        from ui.gallery.gallery_screen import GalleryScreen
        from ui.history.history_screen import HistoryScreen
        from ui.reports.reports_screen import ReportsScreen
        from ui.admins.admin_list import AdminList
        from ui.audit.audit_log_screen import AuditScreen
        from ui.settings.settings_screen import SettingsScreen
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        ttk.Label(self.sidebar, text="FAMILY\nMANAGEMENT", font=("Segoe UI", 15, "bold")).pack(pady=(8, 24))
        ttk.Label(self.sidebar, text=identity.username).pack(pady=(0, 16))
        for label, screen in [("Dashboard", Dashboard), ("Family register", FamilyRegister), ("Meetings", MeetingList),
                              ("Attendance", AttendanceScreen), ("Contributions", ContributionDashboard),
                              ("Gallery", GalleryScreen), ("Family history", HistoryScreen), ("Reports", ReportsScreen),
                              ("Administrators", AdminList), ("Audit log", AuditScreen), ("Settings / backup", SettingsScreen)]:
            ttk.Button(self.sidebar, text=label, command=lambda cls=screen: self.show(cls)).pack(fill="x", pady=3)
        ttk.Button(self.sidebar, text="Sign out", command=self.logout).pack(fill="x", pady=20)
        self.show(Dashboard)
        self.run(self.services["settings"].list, self.apply_settings, session_wide=True)

    def apply_settings(self, rows):
        values = {row["setting_key"]: row["setting_value"] for row in rows}
        self.timeout_minutes = int(values.get("session_timeout_minutes", SESSION_TIMEOUT_MINUTES))
        self.title(values.get("family_name") or "Family Management")
        self.backup_frequency = values.get("backup_frequency", "MANUAL")
        if self.identity and self.identity.role == "SUPER_ADMIN":
            self.schedule_backup()

    def schedule_backup(self):
        if getattr(self, "backup_timer", None):
            self.after_cancel(self.backup_timer)
        if self.identity and self.identity.role == "SUPER_ADMIN":
            service, frequency = self.services["backup"], getattr(self, "backup_frequency", "MANUAL")
            if frequency != "MANUAL":
                self.run(lambda: service.create() if service.due(frequency) else None)
        self.backup_timer = self.after(3600000, self.schedule_backup)

    def activity(self, event=None):
        if self.identity:
            if self.identity.expired(self.timeout_minutes):
                self.logout()
            else:
                self.identity.touch()

    def check_timeout(self):
        if self.identity and self.identity.expired(self.timeout_minutes):
            self.logout()
        self.after(1000, self.check_timeout)

    def logout(self):
        identity = self.identity
        if identity is None:
            return
        self.identity = None
        self.auth.pending.clear()
        self.generation += 1
        for future, _, _, _ in self.pending:
            future.cancel()
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        self.show(lambda app: ttk.Label(app.content, text="Signing out...", padding=30))
        self.run(lambda: self.auth.logout(identity), lambda _: self.show_login(), self.show_login)

    def close(self):
        if any(not item[0].done() for item in self.pending):
            messagebox.showinfo("Work in progress", "Please wait for the current operation to finish.", parent=self)
            return
        if self.identity:
            identity = self.identity
            self.identity = None
            self.run(lambda: self.auth.logout(identity), lambda _: self.finish_close(), self.finish_close)
        else:
            self.finish_close()

    def finish_close(self):
        self._closing = True
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()
