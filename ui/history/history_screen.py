from tkinter import filedialog, ttk
from models import MediaType
from ui.components import Screen, Field, FormDialog, enum_options, TableView


class HistoryScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Family history")
        self.button("Add story", self.edit)
        self.button("Edit story", lambda: self.edit(self.grid.selected()))
        self.button("Read story", self.read)
        self.button("List attachments", self.attachments)
        self.button("Attach media", self.upload)
        self.button("View attachment", self.view)
        panes = ttk.Panedwindow(self, orient="vertical")
        panes.pack(fill="both", expand=True)
        self.grid = TableView(panes, ("title", "historical_period", "author", "summary"))
        self.grid.tree.configure(height=4)
        panes.add(self.grid, weight=1)
        attachments = ttk.Frame(panes)
        panes.add(attachments, weight=1)
        ttk.Label(attachments, text="Story attachments", style="Page.TLabel", font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(4, 12))
        self.media = TableView(attachments, ("title", "media_type", "file_path"))
        self.media.tree.configure(height=3)
        self.media.pack(fill="both", expand=True)
        app.run(app.services["history"].list, self.grid.set_rows)

    def edit(self, row=None):
        FormDialog(self.app, "Family history", [
            Field("title", "Title", required=True), Field("summary", "Summary", "multiline"),
            Field("content", "Story", "multiline", required=True),
            Field("historical_period", "Historical period"), Field("author", "Author")],
            lambda values: self.app.services["history"].save(**values, identity=row["id"] if row else None), initial=row)

    def read(self):
        row = self.grid.selected()
        self.show_text(row["title"], row["content"])

    def attachments(self):
        identity = self.grid.selected()["id"]
        self.app.run(lambda: self.app.services["history"].media(identity), self.media.set_rows)

    def upload(self):
        identity = self.grid.selected()["id"]
        source = filedialog.askopenfilename(parent=self)
        if source:
            FormDialog(self.app, "Attach media", [
                Field("title", "Title", required=True),
                Field("media_type", "Media type", choices=enum_options(MediaType), required=True),
                Field("description", "Description", "multiline")],
                lambda values: self.app.services["history"].upload(identity, source, **values),
                success=lambda _: self.attachments())

    def view(self):
        from ui.gallery.photo_viewer import show_file
        show_file(self.app, self.media.selected()["file_path"])
