import tkinter as tk
from tkinter import ttk
import qrcode
from PIL import ImageTk


def show_setup(app, ticket):
    dialog = tk.Toplevel(app)
    dialog.title("Authenticator setup")
    dialog.geometry("540x660")
    dialog.transient(app)
    dialog.grab_set()
    ttk.Label(dialog, text="Scan with Google Authenticator", font=("Segoe UI", 16, "bold")).pack(pady=12)
    image = ImageTk.PhotoImage(qrcode.make(ticket.uri).resize((300, 300)))
    label = ttk.Label(dialog, image=image)
    label.image = image
    label.pack()
    ttk.Label(dialog, text="Or enter this setup key manually:").pack(pady=(10, 2))
    key = ttk.Entry(dialog, width=50)
    key.insert(0, ticket.secret)
    key.configure(state="readonly")
    key.pack()
    ttk.Label(dialog, text="Enter the 6-digit code to finish setup").pack(pady=10)
    code = ttk.Entry(dialog, show="*")
    code.pack()
    def confirm():
        entered = code.get()
        code.delete(0, "end")
        button.configure(state="disabled")
        def done(codes):
            dialog.destroy()
            recovery = tk.Toplevel(app)
            recovery.title("Save your recovery codes")
            recovery.geometry("560x480")
            recovery.transient(app)
            recovery.grab_set()
            ttk.Label(recovery, text="Shown once. Store these codes somewhere secure.").pack(pady=12)
            text = tk.Text(recovery, height=14, width=48)
            text.pack(padx=16, pady=8)
            text.insert("1.0", "\n".join(codes))
            text.configure(state="disabled")
            ttk.Label(recovery, text="Each code works once. Wait for the next authenticator code before signing in.",
                      wraplength=480).pack(pady=8)
            def close():
                recovery.destroy()
                app.refresh() if app.identity else app.show_login()
            ttk.Button(recovery, text="I have saved my codes", command=close).pack(pady=8)
            recovery.protocol("WM_DELETE_WINDOW", close)
        app.run(lambda: app.auth.confirm_setup(ticket.token, entered), done,
                lambda: button.configure(state="normal") if dialog.winfo_exists() else None)
    button = ttk.Button(dialog, text="Verify and finish", command=confirm)
    button.pack(pady=16)
