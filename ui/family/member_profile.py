import tkinter as tk
from tkinter import ttk
from ui.components import display, TableView
from ui.theme import COLORS, CardFrame, SectionCard, ScrollArea, StatusBadge, ResponsiveGrid, StatCard, status_tone


def show_profile(app, member, attendance, contributions, relationships=None, marriages=None, branches=None):
    dialog = tk.Toplevel(app)
    dialog.title("Member profile")
    dialog.geometry("980x740")
    dialog.minsize(800, 580)
    dialog.configure(background=COLORS["background"])
    header = CardFrame(dialog, padding=24)
    header.pack(fill="x", padx=24, pady=20)
    photo_area = ttk.Frame(header, style="Card.TFrame")
    photo_area.pack(side="left", padx=(0, 24))
    initials = "".join(member.get(k, "")[:1] for k in ("first_name", "last_name"))
    portrait = tk.Label(photo_area, text=initials, background=COLORS["accent_soft"], foreground=COLORS["accent"],
                        font=("Segoe UI Semibold", 28), width=4, height=2)
    portrait.pack()
    information = ttk.Frame(header, style="Card.TFrame")
    information.pack(side="left", fill="both", expand=True)
    name = " ".join(filter(None, (member.get("first_name"), member.get("middle_name"), member.get("last_name"))))
    ttk.Label(information, text=name, style="CardTitle.TLabel", wraplength=650).pack(anchor="w")
    ttk.Label(information, text=member.get("family_number", "Family member"), style="CardHelper.TLabel").pack(anchor="w", pady=6)
    StatusBadge(information, member.get("living_status", "LIVING")).pack(anchor="w")
    from utils.family_labels import affiliation_label
    StatusBadge(information, affiliation_label(member.get('affiliation_type')), tone='info' if member.get('affiliation_type') == 'LINEAGE_MEMBER' else 'warning').pack(anchor='w', pady=4)
    if member.get('birth_position'):
        ttk.Label(information, text='Birth position: ' + member['birth_position'], style='CardHelper.TLabel', wraplength=650).pack(anchor='w')
    if member.get("profile_image_path"):
        from ui.gallery.photo_viewer import show_file
        from PIL import Image, ImageTk
        from utils.file_manager import FileManager
        try:
            with Image.open(FileManager(app.media_root).resolve(member["profile_image_path"])) as source:
                source.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(source.copy())
            portrait.configure(image=photo, text="", width=100, height=100)
            portrait.image = photo
        except (OSError, ValueError):
            portrait.configure(text=initials)
        ttk.Button(information, text="View profile image", command=lambda: show_file(app, member["profile_image_path"]), style="GhostButton.TButton").pack(anchor="w", pady=(8, 0))
    actions = ttk.Frame(dialog)
    actions.pack(fill="x", padx=24, pady=(0, 12))
    def refreshed(_):
        if dialog.winfo_exists():
            dialog.destroy()
        app.refresh()
        open_profile(app, member["id"])
    def relative(direction):
        from ui.family.relative_form import relative_form
        app.run(app.services["family"].list,
                lambda rows: relative_form(app, member, direction, rows, refreshed) if dialog.winfo_exists() else None)
    def spouse():
        from ui.family.relationship_form import marriage_form
        app.run(app.services["family"].list,
                lambda rows: marriage_form(app, rows, current=member, success=refreshed) if dialog.winfo_exists() else None)
    ttk.Button(actions, text="Add Child", style="PrimaryButton.TButton", command=lambda: relative("child")).pack(side="left", padx=(0, 8))
    ttk.Button(actions, text="Add Parent", command=lambda: relative("parent")).pack(side="left", padx=(0, 8))
    ttk.Button(actions, text="Add Spouse", command=spouse).pack(side="left")
    tabs = ttk.Notebook(dialog)
    tabs.pack(fill="both", expand=True, padx=24, pady=(0, 24))
    def page(title):
        area = ScrollArea(tabs)
        tabs.add(area, text=title)
        return area.body
    details = page("Personal details")
    card = SectionCard(details, "Member information")
    card.pack(fill="x")
    for index, (key, value) in enumerate((k, v) for k, v in member.items() if k not in ("id", "profile_image_path")):
        ttk.Label(card.body, text=key.replace("_", " ").title(), style="CardHelper.TLabel").grid(row=index, column=0, sticky="nw", padx=(0, 24), pady=5)
        ttk.Label(card.body, text=display(value) or "--", style="Card.TLabel", wraplength=550).grid(row=index, column=1, sticky="w", pady=5)
    family = page("Relationships")
    relationships = relationships or {}
    summary = SectionCard(family, "Family relationships")
    summary.pack(fill="x", pady=(0, 12))
    for key, label in (("parents", "Parents"), ("spouses", "Spouses")):
        if key == "spouses" and member.get("affiliation_type") == "MARRIED_IN":
            label = "Joined through marriage to"
        values = [(label if key == "spouses" else r.get("relationship_label", label)) + ": " + r["first_name"] + " " + r["last_name"] for r in relationships.get(key, [])]
        ttk.Label(summary.body, text="; ".join(values) or label + ": not recorded", style="Card.TLabel", wraplength=740).pack(anchor="w", pady=(0, 6))
    counts = "    ".join(f"{key.title()}: {len(relationships.get(key, []))}" for key in ("children", "siblings", "grandparents", "grandchildren"))
    ttk.Label(summary.body, text=counts, style="Card.TLabel", wraplength=740).pack(anchor="w")
    branch_card = SectionCard(family, "Family branches", "Membership follows biological descent from each founder.")
    branch_card.pack(fill="x", pady=(0, 12))
    for branch in branches or []:
        from ui.family.branch_screen import show_branch_details
        ttk.Button(branch_card.body, text=branch["name"] + (" (inactive)" if not branch["is_active"] else ""),
                   style="GhostButton.TButton", command=lambda b=branch: show_branch_details(app, b["id"])).pack(anchor="w", pady=2)
    if not branches:
        ttk.Label(branch_card.body, text="No branch lineage recorded yet.", style="CardHelper.TLabel").pack(anchor="w")
    for key in ("parents", "guardians", "spouses", "children", "siblings", "grandparents", "grandchildren", "ancestors", "descendants", "wards"):
        rows = relationships.get(key, [])
        if not rows:
            continue
        section = SectionCard(family, key.title())
        section.pack(fill="x", pady=(0, 12))
        for row in rows:
            name = " ".join(filter(None, (row.get("first_name"), row.get("middle_name"), row.get("last_name"))))
            text = (row.get("relationship_label", "") + ": " if row.get("relationship_label") else "") + name + "  |  " + row.get("family_number", "")
            if key in ("children", "siblings") and row.get("birth_position"):
                text += " | " + row["birth_position"]
            ttk.Button(section.body, text=text, style="GhostButton.TButton", command=lambda r=row: open_profile(app, r["id"])).pack(anchor="w", pady=2)
    marriage_page = page("Marriages")
    for row in marriages or []:
        section = SectionCard(marriage_page, row.get("status", "Marriage").replace("_", " ").title())
        section.pack(fill="x", pady=(0, 12))
        from ui.family.marriage_details import open_marriage, add_child
        ttk.Label(section.body, text=row.get('couple_name', 'Couple') + f" | {row.get('child_count', 0)} shared children", style='Card.TLabel').pack(anchor='w')
        ttk.Button(section.body, text='View couple / edit / delete', command=lambda r=row: open_marriage(app, r['id'])).pack(anchor='w', pady=4)
        ttk.Button(section.body, text='Add Child', style='PrimaryButton.TButton', command=lambda r=row: add_child(app, r, refreshed)).pack(anchor='w', pady=4)
    if not marriages:
        ttk.Label(marriage_page, text="No marriage records yet.", style="Subtitle.TLabel").pack(anchor="w", pady=16)
    participation = page("Attendance")
    grid = ResponsiveGrid(participation, minimum=240, maximum=3)
    grid.pack(fill="x")
    for key, value in attendance.items():
        grid.add(StatCard(grid, key.replace("_", " ").title(), display(value) + ("%" if "percentage" in key else ""), tone=status_tone(key.upper())))
    finances = ttk.Frame(tabs)
    tabs.add(finances, text="Contributions")
    from ui.contributions.payment_form import quick_payment
    from ui.contributions.contribution_details import contribution_details
    financial_actions = ttk.Frame(finances)
    financial_actions.pack(fill='x', pady=8)
    ttk.Button(financial_actions, text='Record Payment', style='PrimaryButton.TButton', command=lambda: quick_payment(app, member['id'], refreshed)).pack(side='left', padx=6)
    def view_contribution():
        from tkinter import messagebox
        try:
            contribution_details(app, table.selected())
        except ValueError as exc:
            messagebox.showinfo('Select contribution', str(exc), parent=dialog)
    ttk.Button(financial_actions, text='View details / payment history', command=view_contribution).pack(side='left', padx=6)
    if contributions:
        from datetime import date
        current = next((r for r in contributions if str(date.today().year) in r.get('period','')), contributions[0])
        contribution_card = SectionCard(finances, current['period'])
        contribution_card.pack(fill='x',pady=8)
        ttk.Label(contribution_card.body,text=f"Due GHS {current['amount_due']:,.2f} | Paid GHS {current['total_paid']:,.2f} | Balance GHS {current['outstanding']:,.2f}",style='Card.TLabel').pack(anchor='w')
        StatusBadge(contribution_card.body,current['status']).pack(anchor='w',pady=4)
        from ui.contributions.payment_form import payment_form
        ttk.Button(contribution_card.body,text='PAID IN FULL' if current['outstanding'] == 0 else 'Record Payment',
                   state='disabled' if current['outstanding'] == 0 or current.get('period_status') != 'ACTIVE' else 'normal',
                   command=lambda:payment_form(app,current,refreshed)).pack(side='left',padx=4)
        def current_history():
            from ui.contributions.payment_history import PaymentHistory
            dialog.destroy(); app.show(lambda a:PaymentHistory(a,current))
        ttk.Button(contribution_card.body,text='Payment History',command=current_history).pack(side='left',padx=4)
    table = TableView(finances, ("period", "amount_due", "total_paid", "outstanding", "status"))
    table.pack(fill="both", expand=True)
    table.set_rows(contributions)
    tabs.select(1)
    return dialog


def open_profile(app, member_id):
    def load():
        tree = app.services["relationships"].tree(member_id)
        branches = app.services["branches"].get_member_branches(member_id)
        finance = app.services['contributions']
        obligations = finance.obligations(member_id=member_id)
        from ui.contributions.payment_form import preferred_period
        period = preferred_period([p for p in finance.periods() if p['status'] == 'ACTIVE' and p.get('frequency') == 'ANNUAL'])
        if period and not any(r['contribution_period_id'] == period['id'] for r in obligations):
            obligations.insert(0,finance.payment_preview(period['id'],member_id))
        return (tree["member"], app.services["attendance"].summary(member_id=member_id),
                obligations, tree,
                app.services["relationships"].marriages(member_id), branches)
    app.run(load, lambda data: show_profile(app, *data))
