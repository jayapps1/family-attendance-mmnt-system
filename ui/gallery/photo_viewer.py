import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from utils.file_manager import FileManager


def show_file(app, relative):
    path = FileManager(app.media_root).resolve(relative)
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        with Image.open(path) as source:
            source.thumbnail((1000, 700))
            photo = ImageTk.PhotoImage(source.copy())
        dialog = tk.Toplevel(app)
        dialog.title(path.name)
        label = ttk.Label(dialog, image=photo)
        label.image = photo
        label.pack()
    elif messagebox.askyesno("Open file", "Open this media file in its default application?", parent=app):
        os.startfile(path)
