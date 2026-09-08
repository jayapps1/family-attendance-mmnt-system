from tkinter import filedialog
from ui.components import Screen, Field, FormDialog


class GalleryScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Gallery")
        self.button("Add album", self.album)
        self.button("Edit album", lambda: self.album(self.albums.selected()))
        self.button("Open album", self.load_items)
        self.button("Upload file", self.upload)
        self.button("View file", self.view)
        self.albums = self.table(("title", "event_date", "location", "description"))
        self.items = self.table(("title", "file_path", "uploaded_at"))
        app.run(app.services["gallery"].albums, self.albums.set_rows)

    def album(self, row=None):
        FormDialog(self.app, "Album", [Field("title", "Title", required=True),
            Field("description", "Description", "multiline"), Field("event_date", "Event date", "date"),
            Field("location", "Location")],
            lambda values: self.app.services["gallery"].save_album(**values, identity=row["id"] if row else None), initial=row)

    def load_items(self):
        identity = self.albums.selected()["id"]
        self.app.run(lambda: self.app.services["gallery"].items(identity), self.items.set_rows)

    def upload(self):
        identity = self.albums.selected()["id"]
        source = filedialog.askopenfilename(parent=self)
        if source:
            FormDialog(self.app, "Upload gallery item", [Field("title", "Title", required=True),
                Field("description", "Description", "multiline")],
                lambda values: self.app.services["gallery"].upload(identity, source, **values),
                success=lambda _: self.load_items())

    def view(self):
        from ui.gallery.photo_viewer import show_file
        show_file(self.app, self.items.selected()["file_path"])
