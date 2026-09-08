"""Opt-in withdrawn-window Tk smoke tests (no application data writes)."""
import os
import time
from decimal import Decimal
from datetime import date
import pytest

pytestmark = pytest.mark.skipif(os.getenv("FAMILY_RUN_UI_TESTS") != "1", reason="Requires a desktop Tk session")


class StubService:
    def list(self, *args, **kwargs): return []
    def types(self): return []
    def periods(self): return []
    def obligations(self, *args, **kwargs): return []
    def albums(self): return []
    def history(self): return []
    def marriages(self): return []
    def payment_history(self, *args): return []
    def summary(self, *args, **kwargs):
        return {"expected_total": Decimal("0"), "collected": Decimal("0"), "outstanding": Decimal("0"),
                "PAID": 0, "PARTIALLY_PAID": 0, "UNPAID": 0}


def drain(app):
    deadline = time.monotonic() + 5
    while app.pending and time.monotonic() < deadline:
        app.update()
        time.sleep(0.02)
    app.update()
    assert not app.pending


@pytest.fixture(scope="module")
def desktop():
    from services.auth_service import AuthService
    from ui.app import Application
    patcher = pytest.MonkeyPatch()
    patcher.setattr(AuthService, "needs_bootstrap", lambda self: True)
    app = Application()
    app.withdraw()
    drain(app)
    try:
        yield app
    finally:
        app.executor.shutdown(wait=True, cancel_futures=True)
        app.destroy()
        patcher.undo()


def test_screens_and_typed_form(monkeypatch, desktop):
    from services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "needs_bootstrap", lambda self: True)
    from ui.app import Application
    from ui.dashboard.dashboard import Dashboard
    from ui.family.family_register import FamilyRegister, RelationshipScreen
    from ui.meetings.meeting_list import MeetingList
    from ui.attendance.attendance_screen import AttendanceScreen
    from ui.contributions.contribution_dashboard import ContributionDashboard
    from ui.contributions.contribution_register import ContributionRegister
    from ui.gallery.gallery_screen import GalleryScreen
    from ui.history.history_screen import HistoryScreen
    from ui.reports.reports_screen import ReportsScreen
    from ui.admins.admin_list import AdminList
    from ui.audit.audit_log_screen import AuditScreen
    from ui.settings.settings_screen import SettingsScreen
    from ui.components import Field, FormDialog
    errors = []
    monkeypatch.setattr("ui.app.messagebox.showerror", lambda *args, **kwargs: errors.append(args))
    app = desktop
    try:
        drain(app)
        app.services = {name: StubService() for name in ("family", "relationships", "meetings", "attendance",
            "contributions", "gallery", "history", "admins", "audit", "settings")}
        for screen in (Dashboard, FamilyRegister, RelationshipScreen, MeetingList, AttendanceScreen,
                       ContributionDashboard, GalleryScreen, HistoryScreen, ReportsScreen, AdminList,
                       AuditScreen, SettingsScreen, lambda a: ContributionRegister(a, None)):
            app.show(screen)
            drain(app)
        form = FormDialog(app, "Test", [Field("amount", "Amount", "money", required=True),
                                       Field("date", "Date", "date")], lambda values: values,
                          initial={"amount": Decimal("12.30"), "date": date(2026, 9, 8)})
        assert form.values() == {"amount": Decimal("12.30"), "date": date(2026, 9, 8)}
        form.destroy()
        assert not errors
    finally:
        app.identity = None


def test_real_service_screens(db, monkeypatch, desktop):
    import uuid
    from services.auth_service import AuthService, AuthSession
    from services.family_service import FamilyService
    from services.contribution_service import ContributionService
    from tests.service_helpers import service_context
    import ui.app as app_module
    from ui.family.family_register import FamilyRegister
    from ui.contributions.contribution_register import ContributionRegister
    context = service_context(db)
    family = FamilyService(*context)
    member = family.create(first_name="UI", last_name="Integration", sex="FEMALE")
    finance = ContributionService(*context)
    kind = finance.create_type("UI " + uuid.uuid4().hex, "ANNUAL", "75")
    period = finance.create_period(kind["id"], "UI period", "75")
    finance.assign_members(period["id"], [member["id"]])
    monkeypatch.setattr(app_module, "SessionLocal", context[0])
    monkeypatch.setattr(AuthService, "needs_bootstrap", lambda self: False)
    errors = []
    monkeypatch.setattr("ui.app.messagebox.showerror", lambda *args, **kwargs: errors.append(args))
    app = desktop
    try:
        drain(app)
        app.signed_in(AuthSession(context[1], "UI tester", "SUPER_ADMIN", uuid.uuid4()))
        drain(app)
        app.show(FamilyRegister)
        drain(app)
        assert any(row["id"] == member["id"] for row in app.screen.grid.rows.values())
        app.show(lambda a: ContributionRegister(a, period["id"]))
        drain(app)
        app.screen.grid.tree.selection_set("0")
        app.screen.history()
        drain(app)
        assert not errors
    finally:
        app.identity = None
