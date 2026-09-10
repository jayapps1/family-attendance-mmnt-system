from utils.family_labels import AFFILIATIONS
from tkinter import ttk, messagebox, filedialog
from ui.components import Screen, Field, FormDialog, member_options, TableView
from ui.family.member_form import member_form
from ui.family.member_profile import show_profile, open_profile
from ui.family.relationship_form import relationship_form, marriage_form
from ui.family.family_tree import show_tree


class FamilyRegister(Screen):
    def __init__(self, app):
        super().__init__(app, "Family register")
        self.search = ttk.Entry(self.toolbar, width=18)
        self.search.pack(side="left", padx=(0, 6))
        self.active = ttk.Combobox(self.toolbar, values=["All", "Active", "Archived"], state="readonly", width=10)
        self.active.set("Active")
        self.active.pack(side="left", padx=(0, 6))
        self.branch = ttk.Combobox(self.toolbar, values=["All branches"], state="readonly", width=24)
        self.branch.set("All branches")
        self.branch.pack(side="left", padx=(0, 6))
        self.branch_ids = {"All branches": None}
        self.branch.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.affiliation = ttk.Combobox(self.toolbar, values=['All Members', *AFFILIATIONS], state='readonly', width=21)
        self.affiliation.set('All Members')
        self.affiliation.pack(side='left', padx=6)
        self.affiliation.bind('<<ComboboxSelected>>', lambda e: self.load())
        self.living = ttk.Combobox(self.toolbar,values=['All living states','LIVING','DECEASED','UNKNOWN'],state='readonly',width=18)
        self.living.set('All living states'); self.living.pack(side='left',padx=6)
        self.living.bind('<<ComboboxSelected>>',lambda e:self.load())
        self.button("Search", self.load)
        self.button("Add member", lambda: member_form(app))
        self.button("Edit", lambda: member_form(app, self.grid.selected()))
        self.button("Profile", self.profile)
        self.button("Tree", self.tree)
        self.button("Photo", self.photo)
        self.button("Archive / restore", self.archive)
        self.button("Relationships", lambda: app.show(RelationshipScreen))
        if app.identity and app.identity.role == 'SUPER_ADMIN':
            self.button('Advanced: Delete permanently', self.delete_permanently, variant='Danger')
        self.grid = self.table(("family_number", "full_name", "affiliation_type", "sex", "age", "phone_number",
                                "current_residence", "living_status", "is_active"))
        app.run(app.services["family"].branches, self.loaded_branches)
        self.load()

    def loaded_branches(self, rows):
        self.branch_ids = {"All branches": None, **{r["name"]: r["id"] for r in rows}}
        self.branch.configure(values=list(self.branch_ids))

    def load(self):
        search = self.search.get()
        active = {"All": None, "Active": True, "Archived": False}[self.active.get()]
        branch_id = self.branch_ids.get(self.branch.get())
        affiliation = AFFILIATIONS.get(self.affiliation.get())
        living_status = None if self.living.get() == "All living states" else self.living.get()
        self.app.run(lambda: self.app.services["family"].list(search, active, branch_id=branch_id, affiliation_type=affiliation, living_status=living_status), self.grid.set_rows)

    def archive(self):
        row = self.grid.selected()
        if messagebox.askyesno("Confirm", "Archive this member?" if row["is_active"] else "Restore this member?", parent=self):
            self.app.run(lambda: self.app.services["family"].archive(row["id"], row["is_active"]), lambda _: self.load())

    def delete_permanently(self):
        row = self.grid.selected()
        if messagebox.askyesno('Permanent deletion', 'Permanently delete ' + row['first_name'] + ' ' + row['last_name'] +
                '? This cannot be undone. Any linked records, including audit history, will block deletion. Archive is the normal option.', parent=self):
            self.app.run(lambda: self.app.services['family'].delete_permanently(row['id']), lambda _: self.load())

    def profile(self):
        open_profile(self.app, self.grid.selected()["id"])

    def photo(self):
        row = self.grid.selected()
        source = filedialog.askopenfilename(parent=self, filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if source:
            self.app.run(lambda: self.app.services["family"].upload_photo(row["id"], source, self.app.media_root),
                         lambda _: self.load())

    def tree(self):
        row = self.grid.selected()
        self.app.run(lambda: self.app.services["relationships"].tree(row["id"]), lambda data: show_tree(self.app, data))


class RelationshipScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Relationships and marriages")
        self.members = []
        self.button("Family register", lambda: app.show(FamilyRegister))
        self.button("Add parent / child", lambda: relationship_form(app, self.members))
        self.button("Edit relationship", lambda: relationship_form(app, self.members, self.relationships.selected()))
        self.button("Add marriage", lambda: marriage_form(app, self.members))
        self.button("Edit marriage", lambda: marriage_form(app, self.members, self.marriages.selected()))
        from ui.family.marriage_details import open_marriage, add_child, delete_marriage
        self.button("View couple", lambda: open_marriage(app, self.marriages.selected()['id']))
        self.button("Add child to couple", lambda: add_child(app, self.marriages.selected()))
        self.button("Delete marriage", lambda: delete_marriage(app, self.marriages.selected()), variant="Danger")
        self.button("Add branch", self.branch)
        self.button("Remove relationship", self.remove, variant="Danger")
        panes = ttk.Panedwindow(self, orient="vertical")
        panes.pack(fill="both", expand=True)
        self.relationships = TableView(panes, ("parent", "child", "relationship_type"))
        self.marriages = TableView(panes, ("couple_name", "status", "marriage_date", "child_count"))
        for table in (self.relationships, self.marriages):
            table.tree.configure(height=4)
            panes.add(table, weight=1)
        app.run(lambda: (app.services["family"].list(), app.services["relationships"].list(),
                         app.services["relationships"].marriages()), self.render)

    def render(self, data):
        self.members, relationships, marriages = data
        labels = {value: key for key, value in member_options(self.members).items()}
        self.relationships.set_rows([dict(r, parent=labels[r["parent_id"]], child=labels[r["child_id"]]) for r in relationships])
        self.marriages.set_rows(marriages)

    def remove(self):
        row = self.relationships.selected()
        if messagebox.askyesno("Remove relationship", f"Remove {row['parent']} as {row['relationship_type'].lower()} of {row['child']}? Both members remain. Derived genealogy and branch membership will update.", parent=self):
            self.app.run(lambda: self.app.services["relationships"].remove_relationship(row["id"]), lambda _: self.app.refresh())

    def branch(self):
        from ui.family.branch_screen import branch_form
        branch_form(self.app, self.members)
