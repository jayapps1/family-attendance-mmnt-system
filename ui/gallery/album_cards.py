"""Selectable album cards using the gallery's existing records and managed media."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps
from ui.theme import ScrollArea, ResponsiveGrid, CardFrame, COLORS
from ui.components import display
from utils.file_manager import FileManager


class AlbumCards(ScrollArea):
    def __init__(self, parent, app, open_album):
        super().__init__(parent)
        self.app, self.open_album = app, open_album
        self.rows, self.cards, self.selection = {}, {}, None

    def set_rows(self, rows):
        self.rows = {str(index): row for index, row in enumerate(rows)}
        self.selection = None
        self.cards = {}
        for child in self.body.winfo_children():
            child.destroy()
        grid = ResponsiveGrid(self.body, minimum=245, maximum=4)
        grid.pack(fill="x")
        if not rows:
            ttk.Label(grid, text="No albums yet. Add an album to begin your family collection.",
                      style="Subtitle.TLabel", padding=16).pack(anchor="w")
            return
        for key, row in self.rows.items():
            card = grid.add(CardFrame(grid, padding=14))
            self.cards[key] = card
            image_label = ttk.Label(card, text="No cover photo", anchor="center", style="CardHelper.TLabel", padding=(0, 32))
            image_label.pack(fill="x")
            ttk.Label(card, text=row["title"], style="Field.TLabel", wraplength=210).pack(anchor="w", pady=(12, 4))
            ttk.Label(card, text=display(row.get("event_date")) or "Date not set", style="CardHelper.TLabel").pack(anchor="w")
            ttk.Label(card, text=row.get("location") or "Location not set", style="CardHelper.TLabel", wraplength=210).pack(anchor="w", pady=(3, 10))
            if row.get("description"):
                ttk.Label(card, text=row["description"][:120], style="CardHelper.TLabel", wraplength=210).pack(anchor="w", pady=(0, 10))
            ttk.Button(card, text="Open album", command=lambda k=key: self.open(k), style="GhostButton.TButton").pack(fill="x")
            def select(event=None, k=key):
                self.select(k)
            card.bind("<Button-1>", select)
            for child in card.winfo_children():
                if not isinstance(child, ttk.Button):
                    child.bind("<Button-1>", select)
            path = row.get("cover_image_path")
            if path:
                def load(path=path):
                    try:
                        with Image.open(FileManager(self.app.media_root).resolve(path)) as source:
                            return ImageOps.fit(source.convert("RGB"), (240, 130))
                    except (OSError, ValueError):
                        return None
                def render(photo, label=image_label):
                    if photo is not None and label.winfo_exists():
                        label.image = ImageTk.PhotoImage(photo)
                        label.configure(image=label.image, text="", padding=0)
                self.app.run(load, render)

    def select(self, key):
        self.selection = key
        for identity, card in self.cards.items():
            card.configure(style="SelectedCard.TFrame" if identity == key else "CardBorder.TFrame")

    def open(self, key):
        self.select(key)
        self.open_album()

    def selected(self):
        if self.selection is None:
            raise ValueError("Select an album first")
        return self.rows[self.selection]
