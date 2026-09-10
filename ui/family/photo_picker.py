"""Portrait upload, crop, rotation and size controls for member forms."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from io import BytesIO
from PIL import Image, ImageTk
from ui.theme import CardFrame, SectionCard, COLORS
from utils.file_manager import FileManager
from utils.profile_image import PreparedPhoto, load_portrait, crop_portrait, prepare_portrait


class PhotoPicker(ttk.Frame):
    def __init__(self, parent, app, value=None):
        super().__init__(parent, style="Card.TFrame")
        self.app, self.value = app, value
        self.preview = ttk.Label(self, text="No profile photo", style="CardHelper.TLabel", anchor="center")
        self.preview.pack(side="left", padx=(0, 18))
        controls = ttk.Frame(self, style="Card.TFrame")
        controls.pack(side="left", fill="x", expand=True)
        ttk.Label(controls, text="Upload a portrait and adjust its crop and size.", style="CardHelper.TLabel", wraplength=320).pack(anchor="w", pady=(0, 8))
        ttk.Button(controls, text="Upload / resize photo", style="PrimaryButton.TButton", command=self.choose).pack(anchor="w")
        ttk.Button(controls, text="Remove photo", style="GhostButton.TButton", command=self.remove).pack(anchor="w", pady=(6, 0))
        self.render()

    def get(self):
        return self.value

    def remove(self):
        self.value = None
        self.render()

    def render(self):
        try:
            if isinstance(self.value, PreparedPhoto):
                source = Image.open(BytesIO(self.value.data))
            elif self.value:
                source = Image.open(FileManager(self.app.media_root).resolve(self.value))
            else:
                self.preview.configure(image="", text="No profile photo")
                self.preview.image = None
                return
            with source:
                image = source.copy()
                image.thumbnail((110, 110))
                self.preview.image = ImageTk.PhotoImage(image)
            self.preview.configure(image=self.preview.image, text="")
        except (OSError, ValueError) as exc:
            from utils.logger import log_exception
            log_exception("Portrait preview unavailable", exc)
            self.preview.configure(image="", text="Photo unavailable")

    def choose(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a member photo",
                                         filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if not path:
            return
        try:
            image = load_portrait(path)
        except ValueError as exc:
            messagebox.showerror("Profile photo", str(exc), parent=self)
            return
        PortraitEditor(self.winfo_toplevel(), image, self.accept)

    def accept(self, photo):
        self.value = photo
        self.render()


class PortraitEditor(tk.Toplevel):
    def __init__(self, parent, image, accept):
        super().__init__(parent)
        self.source, self.accept, self._timer = image, accept, None
        self.title("Adjust profile photo")
        self.geometry("620x750")
        self.minsize(560, 700)
        self.configure(background=COLORS["background"])
        self.transient(parent)
        self.grab_set()
        card = SectionCard(self, "Make the portrait fit", "Adjust the crop, then choose the saved image size. Your original photo stays unchanged.")
        card.pack(fill="both", expand=True, padx=24, pady=24)
        self.preview = ttk.Label(card.body, style="Card.TLabel", anchor="center")
        self.preview.pack(fill="x", pady=(0, 12))
        self.zoom, self.horizontal, self.vertical = tk.DoubleVar(value=1), tk.DoubleVar(value=.5), tk.DoubleVar(value=.5)
        for label, variable, start, stop in (("Zoom", self.zoom, 1, 3), ("Horizontal position", self.horizontal, 0, 1), ("Vertical position", self.vertical, 0, 1)):
            row = ttk.Frame(card.body, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=20, style="Card.TLabel").pack(side="left")
            ttk.Scale(row, from_=start, to=stop, variable=variable, command=self.queue_preview).pack(side="left", fill="x", expand=True)
        row = ttk.Frame(card.body, style="Card.TFrame")
        row.pack(fill="x", pady=12)
        ttk.Label(row, text="Saved size (pixels)", style="Field.TLabel").pack(side="left")
        self.size = ttk.Combobox(row, values=("256", "512", "1024"), state="readonly", width=8)
        self.size.set("512")
        self.size.pack(side="left", padx=12)
        ttk.Button(row, text="Rotate 90 degrees", command=self.rotate).pack(side="right")
        actions = CardFrame(self, padding=(24, 14))
        actions.pack(fill="x")
        ttk.Button(actions, text="Use this photo", command=self.apply, style="PrimaryButton.TButton").pack(side="right")
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self.destroy())
        self.render()

    def settings(self):
        return dict(size=int(self.size.get()), zoom=self.zoom.get(), horizontal=self.horizontal.get(), vertical=self.vertical.get())

    def queue_preview(self, _=None):
        if self._timer:
            self.after_cancel(self._timer)
        self._timer = self.after(40, self.render)

    def render(self):
        self._timer = None
        photo = crop_portrait(self.source, **dict(self.settings(), size=256))
        self.preview.image = ImageTk.PhotoImage(photo)
        self.preview.configure(image=self.preview.image)

    def rotate(self):
        self.source = self.source.transpose(Image.Transpose.ROTATE_270)
        self.render()

    def apply(self):
        self.accept(prepare_portrait(self.source, **self.settings()))
        self.destroy()

    def destroy(self):
        if self._timer:
            self.after_cancel(self._timer)
            self._timer = None
        parent = self.master
        super().destroy()
        if parent.winfo_exists():
            parent.grab_set()
