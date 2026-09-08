import tkinter as tk
from tkinter import ttk
import qrcode
from PIL import ImageTk
from ui.theme import COLORS, style_text, SectionCard, ScrollArea


def show_setup(app, ticket):
    dialog = tk.Toplevel(app)
    dialog.title("Authenticator setup")
    dialog.geometry("600x760")
    dialog.configure(background=COLORS["background"])
    dialog.transient(app)
    dialog.grab_set()
    area = ScrollArea(dialog)
    area.pack(fill="both", expand=True, padx=24, pady=24)
    card = SectionCard(area.body, "Set up your authenticator", "Keep your family records protected with two-step sign-in.")
    card.pack(fill="both", expand=True)
    body = card.body
    ttk.Label(body, text="1. Scan with Google Authenticator", style="Field.TLabel").pack(pady=12)
    image = ImageTk.PhotoImage(qrcode.make(ticket.uri).resize((300, 300)))
    label = ttk.Label(body, image=image, style="Card.TLabel")
    label.image = image
    label.pack()
    ttk.Label(body, text="Or enter this setup key manually:", style="CardHelper.TLabel").pack(pady=(10, 2))
    key = ttk.Entry(body, width=50)
    key.insert(0, ticket.secret)
    key.configure(state="readonly")
    key.pack()
    def copy_key():
        app.clipboard_clear()
        app.clipboard_append(ticket.secret)
    ttk.Button(body, text="Copy setup key", style="GhostButton.TButton", command=copy_key).pack(pady=6)
    ttk.Label(body, text="2. Enter the 6-digit code to finish setup", style="Field.TLabel").pack(pady=10)
    code = ttk.Entry(body, show="*")
    code.pack()
    def confirm():
        entered = code.get()
        code.delete(0, "end")
        button.configure(state="disabled")
        def done(codes):
            dialog.destroy()
            recovery = tk.Toplevel(app)
            recovery.title("Save your recovery codes")
            recovery.geometry("600x590")
            recovery.configure(background=COLORS["background"])
            recovery.transient(app)
            recovery.grab_set()
            ttk.Label(recovery, text="Shown once. Store these codes somewhere secure.").pack(pady=12)
            text = tk.Text(recovery, height=14, width=48)
            style_text(text)
            text.pack(padx=16, pady=8)
            text.insert("1.0", "\n".join(codes))
            text.configure(state="disabled")
            ttk.Label(recovery, text="Each code works once. Wait for the next authenticator code before signing in.",
                      wraplength=480).pack(pady=8)
            def copy_codes():
                app.clipboard_clear()
                app.clipboard_append("\n".join(codes))
            ttk.Button(recovery, text="Copy recovery codes", command=copy_codes).pack(pady=4)
            def close():
                recovery.destroy()
                app.refresh() if app.identity else app.show_login()
            ttk.Button(recovery, text="I have saved my codes", style="PrimaryButton.TButton", command=close).pack(pady=8)
            recovery.protocol("WM_DELETE_WINDOW", close)
        app.run(lambda: app.auth.confirm_setup(ticket.token, entered), done,
                lambda: button.configure(state="normal") if dialog.winfo_exists() else None)
    button = ttk.Button(body, text="Verify and finish", style="PrimaryButton.TButton", command=confirm)
    button.pack(pady=16)
