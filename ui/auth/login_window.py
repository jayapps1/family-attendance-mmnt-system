from tkinter import ttk, messagebox
from ui.components import Field, FormDialog
from ui.auth.authenticator_setup import show_setup


class LoginView(ttk.Frame):
    def __init__(self, app, bootstrap=False):
        super().__init__(app.content, padding=40)
        self.app = app
        panel = ttk.Frame(self, padding=24)
        panel.pack(expand=True)
        ttk.Label(panel, text="Family Management", font=("Segoe UI", 26, "bold")).pack(pady=12)
        ttk.Label(panel, text="Create the first administrator" if bootstrap else "Sign in with your authenticator").pack(pady=8)
        if bootstrap:
            ttk.Button(panel, text="Set up first administrator", command=self.bootstrap).pack(pady=12)
            return
        ttk.Label(panel, text="Username or email").pack(anchor="w")
        self.identifier = ttk.Entry(panel, width=40)
        self.identifier.pack(pady=6)
        ttk.Label(panel, text="Authenticator or recovery code").pack(anchor="w")
        self.code = ttk.Entry(panel, width=40, show="*")
        self.code.pack(pady=6)
        import tkinter as tk
        self.recovery = tk.BooleanVar()
        ttk.Checkbutton(panel, text="Use a recovery code", variable=self.recovery).pack(anchor="w")
        self.signin = ttk.Button(panel, text="Sign in", command=self.login)
        self.signin.pack(fill="x", pady=16)
        self.code.bind("<Return>", lambda e: self.login())
        self.identifier.focus_set()

    def login(self):
        identifier, code, recovery = self.identifier.get(), self.code.get(), self.recovery.get()
        self.signin.configure(state="disabled")
        self.code.delete(0, "end")
        self.app.run(lambda: self.app.auth.login(identifier, code, recovery=recovery),
                     self.app.signed_in, lambda: self.signin.configure(state="normal") if self.winfo_exists() else None)

    def bootstrap(self):
        FormDialog(self.app, "First administrator",
                   [Field("username", "Username", required=True), Field("email", "Email")],
                   lambda values: self.app.auth.prepare_setup(**values),
                   success=lambda ticket: show_setup(self.app, ticket))
