from ui.components import Screen


class AuditScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Audit log - recent 500 entries")
        self.button("Refresh", app.refresh)
        self.grid = self.table(("created_at", "action", "entity_type", "entity_id", "user_id", "description", "computer_name"))
        app.run(app.services["audit"].history, self.grid.set_rows)
