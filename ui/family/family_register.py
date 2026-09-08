from tkinter import ttk, messagebox, filedialog
from ui.components import Screen, Field, FormDialog, member_options
from ui.family.member_form import member_form
from ui.family.member_profile import show_profile
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
        self.button("Search", self.load)
        self.button("Add", lambda: member_form(app))
        self.button("Edit", lambda: member_form(app, self.grid.selected()))
        self.button("Profile", self.profile)
        self.button("Tree", self.tree)
        self.button("Photo", self.photo)
        self.button("Archive / restore", self.archive)
        self.button("Relationships", lambda: app.show(RelationshipScreen))
        self.grid = self.table(("family_number", "first_name", "last_name", "age", "phone_number",
                                "current_residence", "living_status", "is_active"))
        self.load()

    def load(self):
        search = self.search.get()
        active = {"All": None, "Active": True, "Archived": False}[self.active.get()]
        self.app.run(lambda: self.app.services["family"].list(search, active), self.grid.set_rows)

    def archive(self):
        row = self.grid.selected()
        if messagebox.askyesno("Confirm", "Archive this member?" if row["is_active"] else "Restore this member?", parent=self):
            self.app.run(lambda: self.app.services["family"].archive(row["id"], row["is_active"]), lambda _: self.load())

    def profile(self):
        row = self.grid.selected()
        self.app.run(lambda: (self.app.services["attendance"].summary(member_id=row["id"]),
                             self.app.services["contributions"].obligations(member_id=row["id"])),
                     lambda result: show_profile(self.app, row, *result))

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
        self.button("Add branch", self.branch)
        self.relationships = self.table(("parent", "child", "relationship_type"))
        self.marriages = self.table(("spouse_one", "spouse_two", "status", "marriage_date"))
        app.run(lambda: (app.services["family"].list(), app.services["relationships"].list(),
                         app.services["relationships"].marriages()), self.render)

    def render(self, data):
        self.members, relationships, marriages = data
        labels = {value: key for key, value in member_options(self.members).items()}
        self.relationships.set_rows([dict(r, parent=labels[r["parent_id"]], child=labels[r["child_id"]]) for r in relationships])
        self.marriages.set_rows([dict(r, spouse_one=labels[r["spouse_one_id"]], spouse_two=labels[r["spouse_two_id"]]) for r in marriages])

    def branch(self):
        FormDialog(self.app, "Family branch", [
            Field("name", "Branch name", required=True),
            Field("founding_member_id", "Founding member", choices=member_options(self.members)),
            Field("description", "Description", "multiline")],
            lambda values: self.app.services["family"].create_branch(**values))
