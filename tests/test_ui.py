"""Opt-in withdrawn-window Tk smoke tests (no application data writes)."""
import os
import gc
import time
from decimal import Decimal
from datetime import date
import pytest

pytestmark = pytest.mark.skipif(os.getenv("FAMILY_RUN_UI_TESTS") != "1", reason="Requires a desktop Tk session")


class StubService:
    def list(self, *args, **kwargs): return []
    def types(self): return []
    def branches(self): return []
    def periods(self): return []
    def obligations(self, *args, **kwargs): return []
    def register_rows(self, *args, **kwargs): return []
    def daily_summary(self, *args, **kwargs): return dict(self.summary(), total_members=0)
    def albums(self): return []
    def history(self): return []
    def marriages(self): return []
    def payment_history(self, *args): return []
    def summary(self, *args, **kwargs):
        return {"expected_total": Decimal("0"), "collected": Decimal("0"), "outstanding": Decimal("0"),
                "PAID": 0, "PARTIALLY_PAID": 0, "UNPAID": 0}


def drain(app):
    # Tk objects must be finalized on the UI thread, including withdrawn-window tests.
    gc.collect()
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
    gc_was_enabled = gc.isenabled()
    gc.disable()
    patcher = pytest.MonkeyPatch()
    patcher.setenv("GOOGLE_DRIVE_BACKUP_DIR", "")
    patcher.setattr(Application, "schedule_backup", lambda self: None)
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
        gc.collect()
        if gc_was_enabled:
            gc.enable()


def test_screens_and_typed_form(monkeypatch, desktop):
    from services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "needs_bootstrap", lambda self: True)
    from ui.app import Application
    from ui.dashboard.dashboard import Dashboard
    from ui.family.family_register import FamilyRegister, RelationshipScreen
    from ui.family.branch_screen import BranchScreen
    from ui.family.family_tree import FamilyTreeScreen
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
        app.services = {name: StubService() for name in ("family", "branches", "relationships", "meetings", "attendance",
            "contributions", "gallery", "history", "admins", "audit", "settings")}
        for screen in (Dashboard, FamilyRegister, RelationshipScreen, BranchScreen, FamilyTreeScreen, MeetingList, AttendanceScreen,
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


def test_real_service_screens(db, monkeypatch, desktop, tmp_path):
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
    finance.set_period_status(period["id"], "ACTIVE")
    monkeypatch.setattr(app_module, "SessionLocal", context[0])
    monkeypatch.setattr(AuthService, "needs_bootstrap", lambda self: False)
    errors = []
    monkeypatch.setattr("ui.app.messagebox.showerror", lambda *args, **kwargs: errors.append(args))
    app = desktop
    original_media_root = app.media_root
    app.media_root = tmp_path / "media"
    try:
        drain(app)
        app.signed_in(AuthSession(context[1], "UI tester", "SUPER_ADMIN", uuid.uuid4()))
        drain(app)
        app.show(FamilyRegister)
        drain(app)
        assert any(row["id"] == member["id"] for row in app.screen.grid.rows.values())
        # Exercise the restyled, grouped form through its actual Save button.
        from ui.family.member_form import member_form
        from ui.components import FormDialog
        import tkinter as tk
        member_form(app, member)
        form = next(w for w in app.winfo_children() if isinstance(w, FormDialog))
        form.inputs["current_residence"].insert(0, "UI form verification")
        from PIL import Image
        from utils.profile_image import prepare_portrait
        form.inputs["profile_image_path"].accept(prepare_portrait(Image.new("RGB", (400, 600), "teal")))
        form.button.invoke()
        drain(app)
        updated = next(row for row in app.screen.grid.rows.values() if row["id"] == member["id"])
        assert updated["current_residence"] == "UI form verification"
        assert (app.media_root / updated["profile_image_path"]).is_file()
        key = next(key for key, row in app.screen.grid.rows.items() if row["id"] == member["id"])
        app.screen.grid.tree.selection_set(key)
        app.screen.profile()
        drain(app)
        profile = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        from tkinter import ttk
        notebook = next(w for w in profile.winfo_children() if isinstance(w, ttk.Notebook))
        assert len(notebook.tabs()) == 5
        profile.destroy()
        app.show(lambda a: ContributionRegister(a, period["id"]))
        drain(app)
        app.screen.grid.tree.selection_set(next(k for k,r in app.screen.grid.rows.items() if r["family_member_id"] == member["id"]))
        from ui.contributions.payment_form import payment_form
        payment_form(app, app.screen.grid.selected())
        drain(app)
        form = next(w for w in app.winfo_children() if isinstance(w, FormDialog))
        form.inputs["amount_paid"].insert(0, "35.00")
        form.button.invoke()
        drain(app)
        app.screen.grid.tree.selection_set(next(k for k,r in app.screen.grid.rows.items() if r["family_member_id"] == member["id"]))
        assert app.screen.grid.selected()["outstanding"] == Decimal("40.00")
        app.screen.history()
        drain(app)
        app.screen.grid.tree.selection_set("0")
        app.screen.reverse()
        form = next(w for w in app.winfo_children() if isinstance(w, FormDialog))
        assert form.button.cget("style") == "DangerButton.TButton"
        form.inputs["reason"].insert("1.0", "UI reversal verification")
        form.button.invoke()
        drain(app)
        assert next(iter(app.screen.grid.rows.values()))["is_reversed"]
        assert finance.summary(period["id"])["outstanding"] == Decimal("75.00")
        assert not errors
    finally:
        app.media_root = original_media_root
        app.identity = None


def test_portrait_editor_and_restore_confirmation(monkeypatch, desktop):
    from PIL import Image
    from ui.family.photo_picker import PortraitEditor
    from ui.settings.restore_dialog import RestoreDialog
    from ui.components import Screen
    app = desktop
    drain(app)
    portraits = []
    editor = PortraitEditor(app, Image.new("RGB", (600, 800), "blue"), portraits.append)
    editor.zoom.set(2)
    editor.size.set("1024")
    editor.rotate()
    editor.apply()
    assert portraits[0].size == 1024
    app.grab_release()
    errors, notices, calls = [], [], []
    monkeypatch.setattr("ui.settings.restore_dialog.messagebox.showerror", lambda *a, **kw: errors.append(a))
    monkeypatch.setattr("ui.settings.restore_dialog.messagebox.showinfo", lambda *a, **kw: notices.append(a))
    class Restore:
        def restore(self, *args):
            calls.append(args)
            return {"safety_backup": "test-safety.zip"}
    preview = dict(path="test.zip", name="test.zip", sha256="test-hash", created_at="Test date", media_count=1, size=1024)
    dialog = RestoreDialog(app, Restore(), preview)
    dialog.button.invoke()
    assert errors and not calls
    dialog.confirmation.insert(0, "RESTORE")
    dialog.button.invoke()
    assert app.maintenance
    screen = app.screen
    app.show(lambda a: Screen(a, "Should not navigate"))
    assert app.screen is screen
    drain(app)
    assert calls == [("test.zip", "test-hash", "RESTORE")]
    assert not app.maintenance
    assert notices


def test_profile_relationship_workflows_and_branches(db, monkeypatch, desktop, tmp_path):
    import uuid
    import tkinter as tk
    from tkinter import ttk
    from services.auth_service import AuthSession
    from services.family_service import FamilyService
    from tests.service_helpers import service_context
    from ui.family.relative_form import build_relative_form
    from ui.family.branch_screen import BranchScreen, branch_form, show_branch_details, BranchDetails
    from ui.family.family_register import FamilyRegister
    from ui.components import member_options
    import ui.app as app_module
    context = service_context(db)
    family = FamilyService(*context)
    mother = family.create(first_name="UI mother", last_name="Genealogy", sex="FEMALE")
    monkeypatch.setattr(app_module, "SessionLocal", context[0])
    errors = []
    monkeypatch.setattr("ui.app.messagebox.showerror", lambda *a, **kw: errors.append(a))
    app = desktop
    original_media = app.media_root
    app.media_root = tmp_path / "media"
    try:
        app.signed_in(AuthSession(context[1], "UI genealogy", "SUPER_ADMIN", uuid.uuid4()))
        drain(app)
        saved = []
        form = build_relative_form(app, mother, "child", family.list(), True, saved.append)
        assert str(form.inputs["_context"].cget("state")) == "readonly"
        assert form.inputs["_relationship"].get() == "Mother"
        form.inputs["first_name"].insert(0, "UI child")
        form.inputs["last_name"].insert(0, "Genealogy")
        form.inputs["sex"].set("Male")
        form.button.invoke()
        drain(app)
        assert len(saved) == 1
        child = saved[0]
        assert app.services["relationships"].get_mother(child["id"])["id"] == mother["id"]
        parent = build_relative_form(app, child, "parent", family.list(), True, lambda _: None)
        parent.inputs["sex"].set("Female")
        parent.inputs["sex"].event_generate("<<ComboboxSelected>>")
        assert parent.inputs["_relationship"].get() == "Mother"
        parent.inputs["_relationship"].set("Guardian")
        parent.inputs["_relationship"].event_generate("<<ComboboxSelected>>")
        parent.inputs["sex"].set("Male")
        parent.inputs["sex"].event_generate("<<ComboboxSelected>>")
        assert parent.inputs["_relationship"].get() == "Guardian"
        parent.destroy()
        app.nav_buttons["branches"].invoke()
        drain(app)
        assert isinstance(app.screen, BranchScreen)
        form = branch_form(app, family.list())
        branch_name = "UI branch " + str(mother["id"])
        form.inputs["name"].insert(0, branch_name)
        form.inputs["founding_member_id"].set(next(iter(member_options([mother]))))
        form.button.invoke()
        drain(app)
        branch = next(r for r in app.screen.grid.rows.values() if r["name"] == branch_name)
        assert branch["descendant_count"] == 1
        show_branch_details(app, branch["id"])
        drain(app)
        details = next(w for w in app.winfo_children() if isinstance(w, BranchDetails))
        assert len(details.rows) == 2
        details.tree.selection_set(str(child["id"]))
        details.open_member()
        drain(app)
        profiles = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "Member profile"]
        assert profiles
        profile = profiles[0]
        notebook = next(w for w in profile.winfo_children() if isinstance(w, ttk.Notebook))
        assert notebook.index(notebook.select()) == 1
        for window in [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]:
            window.destroy()
        app.show(FamilyRegister)
        drain(app)
        app.screen.branch.set(branch_name)
        app.screen.load()
        drain(app)
        assert {r["id"] for r in app.screen.grid.rows.values()} == {mother["id"], child["id"]}
        assert not errors
    finally:
        app.media_root = original_media
        app.identity = None
        for window in [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]:
            window.destroy()


def test_couple_child_form_and_details(db, monkeypatch, desktop, tmp_path):
    import uuid
    import tkinter as tk
    from services.auth_service import AuthSession
    from tests.test_marriage_workflow import setup_couple
    from tests.service_helpers import service_context
    from services.family_service import FamilyService
    from services.relationship_service import RelationshipService
    from ui.family.marriage_details import child_form, show_marriage
    from ui.components import member_options
    import ui.app as app_module
    context = service_context(db)
    family, links = FamilyService(*context), RelationshipService(*context)
    james = family.create(first_name='James', last_name='Appiah-Gyachie', sex='MALE')
    agnes = family.create(first_name='Agnes', last_name='Ampoful', sex='FEMALE')
    marriage = links.save_marriage(james['id'], agnes['id'])
    monkeypatch.setattr(app_module, 'SessionLocal', context[0])
    errors = []
    monkeypatch.setattr('ui.app.messagebox.showerror', lambda *a, **kw: errors.append(a))
    confirmations = []
    monkeypatch.setattr('ui.family.marriage_details.messagebox.askyesno', lambda *a, **kw: confirmations.append(a) or True)
    app = desktop
    original_media = app.media_root
    app.media_root = tmp_path / 'media'
    try:
        app.signed_in(AuthSession(context[1], 'Couple UI', 'SUPER_ADMIN', uuid.uuid4()))
        drain(app)
        saved = []
        row = links.get_marriage(marriage['id'])
        form = child_form(app, row, family.list(), True, saved.append)
        assert str(form.inputs['_spouse_one'].cget('state')) == 'readonly'
        assert form.inputs['spouse_one_type'].get() == 'Father'
        assert form.inputs['spouse_two_type'].get() == 'Mother'
        form.inputs['first_name'].insert(0, 'Michael')
        form.inputs['last_name'].insert(0, 'Appiah-Gyachie')
        form.inputs['sex'].set('Male')
        form.button.invoke()
        drain(app)
        assert len(saved) == 1
        assert links.get_marriage(row['id'])['child_count'] == 1
        details = show_marriage(app, links.get_marriage(row['id']))
        app.update()
        assert details.winfo_exists()
        details.destroy()
        child = family.create(first_name='Janet', last_name='Appiah-Gyachie', sex='FEMALE')
        links.save(james['id'], child['id'], 'FATHER')
        form = child_form(app, row, family.list(), False, saved.append)
        form.inputs['existing_id'].set(next(iter(member_options([child]))))
        form.button.invoke()
        drain(app)
        assert confirmations and len(saved) == 2
        assert links.get_marriage(row['id'])['child_count'] == 2
        assert not errors
    finally:
        app.media_root = original_media
        app.identity = None
        for window in [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]:
            window.destroy()


def test_order_affiliation_and_quick_payment_controls(db, monkeypatch, desktop, tmp_path):
    import uuid
    import tkinter as tk
    from tkinter import ttk
    from services.auth_service import AuthSession
    from tests.test_union_order_affiliation import scenario
    from services.contribution_service import ContributionService
    from ui.family.marriage_details import manage_child_order
    from ui.family.family_register import FamilyRegister
    from ui.contributions.payment_form import quick_payment
    from ui.contributions.contribution_details import contribution_details
    from ui.components import FormDialog
    import ui.app as app_module
    context, family, links, james, agnes, marriage = scenario(db)
    a = links.add_child_to_marriage(marriage['id'], new_member=dict(first_name='Older', last_name='Child', sex='MALE'))
    b = links.add_child_to_marriage(marriage['id'], new_member=dict(first_name='Younger', last_name='Child', sex='FEMALE'))
    finance = ContributionService(*context)
    kind = finance.create_type('UI quick ' + uuid.uuid4().hex, 'ANNUAL', '60')
    period = finance.create_period(kind['id'], 'Annual Contribution 2026', '60')
    obligation = finance.assign_members(period['id'], [james['id']])[0]
    finance.set_period_status(period['id'], 'ACTIVE')
    monkeypatch.setattr(app_module, 'SessionLocal', context[0])
    errors = []
    monkeypatch.setattr('ui.app.messagebox.showerror', lambda *a, **kw: errors.append(a))
    app = desktop
    def widgets(parent):
        for w in parent.winfo_children():
            yield w
            yield from widgets(w)
    try:
        app.signed_in(AuthSession(context[1], 'UI controls', 'SUPER_ADMIN', uuid.uuid4()))
        drain(app)
        results = []
        dialog = manage_child_order(app, links.get_marriage(marriage['id']), results.append)
        listing = next(w for w in widgets(dialog) if isinstance(w, tk.Listbox))
        listing.selection_clear(0, 'end'); listing.selection_set(1)
        next(w for w in widgets(dialog) if isinstance(w, ttk.Button) and w.cget('text') == 'Move Up').invoke()
        next(w for w in widgets(dialog) if isinstance(w, ttk.Button) and w.cget('text') == 'Save child order').invoke()
        drain(app)
        assert results[0]['children'][0]['id'] == b['id']
        app.show(FamilyRegister); drain(app)
        app.screen.affiliation.set('Married Into Family'); app.screen.load(); drain(app)
        assert agnes['id'] in {r['id'] for r in app.screen.grid.rows.values()}
        assert james['id'] not in {r['id'] for r in app.screen.grid.rows.values()}
        from ui.family.relationship_form import marriage_form
        new_marriages = []
        form = marriage_form(app, family.list(), current=james, success=new_marriages.append)
        next(w for w in widgets(form) if isinstance(w, ttk.Button) and w.cget('text') == 'Create a new spouse instead').invoke()
        form = next(w for w in app.winfo_children() if isinstance(w, FormDialog))
        assert form.inputs['affiliation_type'].get() == 'Married Into Family'
        form.inputs['first_name'].insert(0, 'Adwoa')
        form.inputs['last_name'].insert(0, 'UI spouse')
        form.inputs['sex'].set('Female')
        form.button.invoke(); drain(app)
        assert len(new_marriages) == 1
        assert links.get_marriage(new_marriages[0]['id'])['spouse_two']['affiliation_type'] == 'MARRIED_IN'
        quick_payment(app, james['id'], period_id=period['id'])
        drain(app)
        form = next(w for w in app.winfo_children() if isinstance(w, FormDialog))
        assert form.inputs['_outstanding'].get() == 'GHS 60.00'
        assert 'Family Lineage' in form.member_info.cget('text')
        form.inputs['amount_paid'].insert(0, '20')
        form.button.invoke(); form.button.invoke(); drain(app)
        assert finance.get_obligation(obligation['id'])['outstanding'] == Decimal('40')
        assert len(finance.payment_history(obligation['id'])) == 1
        contribution_details(app, obligation); drain(app)
        assert any(w.title() == 'Contribution details' for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        assert not errors
    finally:
        app.identity = None
        for window in [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]:
            window.destroy()


def test_simple_contribution_real_daily_workflow(db, monkeypatch, desktop):
    import uuid
    import tkinter as tk
    from services.auth_service import AuthSession
    from services.family_service import FamilyService
    from services.contribution_service import ContributionService
    from tests.service_helpers import service_context
    from ui.contributions.payment_form import quick_payment, RecordContributionForm
    from ui.contributions.annual_setup import annual_setup
    from ui.components import FormDialog
    import ui.app as app_module
    context=service_context(db)
    family,finance=FamilyService(*context),ContributionService(*context)
    james=family.create(first_name='James',last_name='Appiah-Gyachie',sex='MALE',phone_number='0542011738')
    monkeypatch.setattr(app_module,'SessionLocal',context[0])
    errors=[]
    monkeypatch.setattr('ui.app.messagebox.showerror',lambda *a,**kw:errors.append(a))
    app=desktop
    try:
        app.signed_in(AuthSession(context[1],'Simple workflow','SUPER_ADMIN',uuid.uuid4())); drain(app)
        setup=annual_setup(app)
        setup.inputs['year'].delete(0,'end'); setup.inputs['year'].insert(0,'2095')
        setup.inputs['amount_per_member'].insert(0,'60')
        setup.button.invoke(); drain(app)
        period=next(p for p in finance.periods() if p['year']==2095)
        assert finance.obligations(period['id'],james['id'])==[]
        for amount,balance in [('30','30'),('20','10'),('10','0')]:
            quick_payment(app,period_id=period['id']); drain(app)
            form=next(w for w in app.winfo_children() if isinstance(w,RecordContributionForm))
            for query in ('James Appiah-Gyachie', '0542011738', james['family_number']):
                form.inputs['member_id'].set(query); form.search()
                assert any(james['family_number'] in str(v) for v in form.inputs['member_id'].cget('values'))
            form.choose_match(); drain(app)
            assert form.preview['family_member_id']==james['id']
            form.inputs['amount_paid'].insert(0,amount)
            form.button.invoke(); form.button.invoke(); drain(app)
            assert finance.payment_preview(period['id'],james['id'])['outstanding']==Decimal(balance)
        obligation=finance.obligations(period['id'],james['id'])[0]
        assert len(finance.payment_history(obligation['id']))==3
        quick_payment(app,james['id'],period_id=period['id']); drain(app)
        form=next(w for w in app.winfo_children() if isinstance(w,RecordContributionForm))
        assert str(form.button.cget('state'))=='disabled'
        assert form.badge.cget('text')=='PAID IN FULL'
        assert not errors
    finally:
        app.identity=None
        for w in app.winfo_children():
            if isinstance(w,tk.Toplevel): w.destroy()
