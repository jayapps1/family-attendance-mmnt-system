from tkinter import filedialog
from ui.components import Screen, Field, FormDialog, TableView


class GalleryScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Gallery")
        self.button("Add album", self.album)
        self.button("Edit album", lambda: self.album(self.albums.selected()))
        self.button("Open album", self.load_items)
        self.button("Delete empty album",self.delete,variant="Danger")
        self.button("Upload file", self.upload)
        self.button("View file", self.view)
        from ui.gallery.album_cards import AlbumCards
        from tkinter import ttk
        panes = ttk.Panedwindow(self, orient="vertical")
        panes.pack(fill="both", expand=True)
        self.albums = AlbumCards(panes, app, self.load_items)
        self.albums.canvas.configure(height=200)
        panes.add(self.albums, weight=1)
        files = ttk.Frame(panes)
        panes.add(files, weight=1)
        ttk.Label(files, text="Album files", style="Page.TLabel", font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(8, 10))
        self.items = TableView(files, ("title", "file_path", "uploaded_at"))
        self.items.tree.configure(height=3)
        self.items.pack(fill="both", expand=True)
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

    def delete(self):
        from tkinter import messagebox
        row=self.albums.selected()
        if messagebox.askyesno('Delete empty album','Delete "'+row['title']+'"? Only an empty album can be deleted; media files are preserved.',parent=self):
            self.app.run(lambda:self.app.services['gallery'].delete_empty_album(row['id']),lambda _:self.app.refresh())
