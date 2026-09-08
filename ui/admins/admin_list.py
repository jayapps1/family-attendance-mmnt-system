from models import UserRole
from ui.components import Screen, Field, FormDialog, enum_options
from ui.auth.authenticator_setup import show_setup


class AdminList(Screen):
    def __init__(self, app):
        super().__init__(app, "Administrators")
        self.button("Create administrator", self.create)
        self.button("Update access", self.update)
        self.button("Restart authenticator setup", self.reset)
        self.grid = self.table(("username", "email", "phone_number", "role", "is_active", "totp_enabled", "last_login_at"))
        app.run(app.services["admins"].list, self.grid.set_rows)

    def create(self):
        roles = enum_options(UserRole) if self.app.identity.role == "SUPER_ADMIN" else {"Admin": "ADMIN"}
        actor_id = self.app.identity.user_id
        FormDialog(self.app, "Create administrator", [
            Field("username", "Username", required=True), Field("email", "Email"),
            Field("role", "Role", choices=roles, required=True)],
            lambda values: self.app.auth.prepare_setup(**values, actor_id=actor_id),
            initial={"role": "ADMIN"}, success=lambda ticket: show_setup(self.app, ticket))

    def update(self):
        row = self.grid.selected()
        FormDialog(self.app, "Administrator access", [
            Field("role", "Role", choices=enum_options(UserRole), required=True),
            Field("is_active", "Active", "bool")],
            lambda values: self.app.services["admins"].update(row["id"], **values), initial=row)

    def reset(self):
        row = self.grid.selected()
        from tkinter import messagebox
        if messagebox.askyesno("Reset authenticator", "Invalidate this administrator's current authenticator and recovery codes?", parent=self):
            actor = self.app.identity.user_id
            self.app.run(lambda: self.app.auth.prepare_setup(row["username"], actor_id=actor, reset_id=row["id"]),
                         lambda ticket: show_setup(self.app, ticket))
