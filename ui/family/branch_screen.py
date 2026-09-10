import tkinter as tk
from tkinter import ttk
from ui.components import Screen, Field, FormDialog, member_options
from ui.theme import COLORS, SectionCard, ResponsiveGrid, StatCard, ScrollArea


def branch_form(app, members, row=None):
    return FormDialog(app, "Edit branch" if row else "Create branch", [
        Field("name", "Branch name", required=True),
        Field("founding_member_id", "Founder / root member", choices=member_options(members), required=True),
        Field("description", "Description", "multiline"), Field("is_active", "Active", "bool")],
        lambda values: app.services["branches"].save(**values, identity=row["id"] if row else None),
        initial=row or {"is_active": True}, save_label="Save branch")


class BranchScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Family branches")
        self.members = []
        self.search = ttk.Entry(self.toolbar, width=22)
        self.search.pack(side="left")
        self.search.bind("<Return>", lambda e: self.load())
        self.button("Search", self.load)
        self.button("Create branch", lambda: branch_form(app, self.members))
        self.button("Edit branch", lambda: branch_form(app, self.members, self.grid.selected()))
        self.button("Open branch", lambda: show_branch_details(app, self.grid.selected()["id"]))
        self.button("View branch tree", self.tree)
        self.grid = self.table(("name", "founder", "descendant_count", "status", "description"))
        self.grid.tree.bind("<Double-1>", lambda e: show_branch_details(app, self.grid.selected()["id"]) if self.grid.tree.selection() else None)
        app.run(app.services["family"].list, lambda rows: setattr(self, "members", rows))
        self.load()

    def load(self):
        search = self.search.get()
        self.app.run(lambda: self.app.services["branches"].list(search), self.grid.set_rows)

    def tree(self):
        from ui.family.family_tree import show_tree
        identity = self.grid.selected()["id"]
        self.app.run(lambda: self.app.services["branches"].details(identity),
                     lambda data: show_tree(self.app, data["tree"], descendants_only=True))


def show_branch_details(app, branch_id):
    app.run(lambda: app.services["branches"].details(branch_id), lambda data: BranchDetails(app, data))


class BranchDetails(tk.Toplevel):
    def __init__(self, app, data):
        super().__init__(app)
        self.app, self.data = app, data
        from ui.navigation import dialog_navigation
        dialog_navigation(self,app)
        self.title(data["branch"]["name"])
        self.geometry("1060x780")
        self.minsize(850, 640)
        self.configure(background=COLORS["background"])
        area = ScrollArea(self)
        area.pack(fill="both", expand=True, padx=24, pady=24)
        card = SectionCard(area.body, data["branch"]["name"],
                           "Founder: " + data["founder"]["first_name"] + " " + data["founder"]["last_name"])
        card.pack(fill="x", pady=(0, 12))
        ttk.Label(card.body, text=data["branch"].get("description") or "Biological lineage from the founding member.",
                  style="Card.TLabel", wraplength=900).pack(anchor="w")
        from ui.family.family_tree import show_tree
        ttk.Button(card.body, text="View branch tree", style="PrimaryButton.TButton",
                   command=lambda: show_tree(app, data["tree"], descendants_only=True)).pack(anchor="w", pady=(12, 0))
        grid = ResponsiveGrid(area.body, minimum=210, maximum=3)
        grid.pack(fill="x")
        for key, title in (("direct_children", "Direct children"), ("descendants", "Total descendants"),
                           ("generations", "Descendant generations"), ("living", "Living members"),
                           ("deceased", "Deceased members"), ("lineage_members", "Lineage members"), ("married_in_members", "Married-in members"), ("total_associated_members", "Associated members")):
            grid.add(StatCard(grid, title, data.get(key, 0)))
        members = SectionCard(area.body, "Branch members by generation",
                              "Double-click a member to open their profile. Founder is generation 0.")
        members.pack(fill="both", expand=True)
        self.search = ttk.Entry(members.body)
        self.search.pack(fill="x", pady=(0, 8))
        self.search.bind("<KeyRelease>", lambda e: self.render())
        ttk.Label(members.body, text="Search family number, name, phone or residence", style="CardHelper.TLabel").pack(anchor="w", pady=(0, 8))
        frame = ttk.Frame(members.body, style="Card.TFrame")
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("number", "status"), show="tree headings", height=10)
        from ui.table_style import configure_columns
        configure_columns(self.tree,('number','status'))
        self.tree.heading('#0',text='Generation / member',anchor='w')
        self.tree.column('#0',width=380,minwidth=230,anchor='w')
        scroll = ttk.Scrollbar(frame,command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set)
        self.tree.grid(row=0,column=0,sticky='nsew'); scroll.grid(row=0,column=1,sticky='ns')
        horizontal.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
        self.tree.bind("<Double-1>", self.open_member)
        self.tree.bind("<Return>", self.open_member)
        self.count = ttk.Label(members.body, style="CardHelper.TLabel")
        self.count.pack(anchor="w", pady=10)
        spouses = SectionCard(area.body, "Spouses outside the lineage", "Marriage history does not add someone to biological branch membership.")
        spouses.pack(fill="x", pady=(12, 0))
        from ui.family.member_profile import open_profile
        for row in data["spouses"]:
            ttk.Button(spouses.body, text=row["first_name"] + " " + row["last_name"] + "  |  " + row["family_number"],
                       style="GhostButton.TButton", command=lambda r=row: open_profile(app, r["id"])).pack(anchor="w")
        if not data["spouses"]:
            ttk.Label(spouses.body, text="No spouses outside this lineage recorded.", style="CardHelper.TLabel").pack(anchor="w")
        self.render()

    def render(self):
        self.tree.delete(*self.tree.get_children())
        self.rows, groups = {}, set()
        term = self.search.get().casefold().strip()
        for row in self.data["members"]:
            text = " ".join(str(row.get(k) or "") for k in ("family_number", "first_name", "middle_name", "last_name", "phone_number", "current_residence"))
            if term and term not in text.casefold():
                continue
            generation = row["generation"]
            group = "g" + str(generation)
            if group not in groups:
                self.tree.insert("", "end", iid=group, text="Founder" if generation == 0 else f"Generation {generation}", open=True)
                groups.add(group)
            key = str(row["id"])
            self.rows[key] = row
            self.tree.insert(group, "end", iid=key, text=" ".join(filter(None, (row["first_name"], row.get("middle_name"), row["last_name"]))),
                             values=(row["family_number"], row["living_status"]))
        self.count.configure(text=f"{len(self.rows)} of {len(self.data['members'])} lineage members")

    def open_member(self, event=None):
        from ui.family.member_profile import open_profile
        selected = self.tree.selection()
        if selected and selected[0] in self.rows:
            open_profile(self.app, self.rows[selected[0]]["id"])
