from tkinter import ttk, messagebox
from ui.components import Field, FormDialog
from ui.auth.authenticator_setup import show_setup


class LoginView(ttk.Frame):
    def __init__(self, app, bootstrap=False):
        super().__init__(app.content, padding=40)
        self.app = app
        from ui.theme import CardFrame, COLORS
        panel = CardFrame(self, padding=40)
        panel.pack(expand=True)
        import tkinter as tk
        tk.Frame(panel, background=COLORS["gold"], height=4).pack(fill="x", pady=(0, 24))
        ttk.Label(panel, text="FAMILY MANAGEMENT", style="CardHelper.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Welcome home", style="CardTitle.TLabel", font=("Segoe UI Semibold", 28)).pack(anchor="w", pady=(10, 8))
        ttk.Label(panel, text="Your family records, thoughtfully connected.", style="CardHelper.TLabel").pack(anchor="w", pady=(0, 24))
        ttk.Label(panel, text="Create the first administrator" if bootstrap else "Sign in with your authenticator", style="Field.TLabel").pack(anchor="w", pady=(0, 16))
        if bootstrap:
            ttk.Button(panel, text="Set up first administrator", style="PrimaryButton.TButton", command=self.bootstrap).pack(pady=12)
            return
        ttk.Label(panel, text="Username or email", style="Field.TLabel").pack(anchor="w")
        self.identifier = ttk.Entry(panel, width=40)
        self.identifier.pack(pady=6)
        ttk.Label(panel, text="Authenticator or recovery code", style="Field.TLabel").pack(anchor="w")
        self.code = ttk.Entry(panel, width=40, show="*")
        self.code.pack(pady=6)
        import tkinter as tk
        self.recovery = tk.BooleanVar()
        ttk.Checkbutton(panel, text="Use a recovery code", variable=self.recovery).pack(anchor="w")
        self.signin = ttk.Button(panel, text="Sign in", style="PrimaryButton.TButton", command=self.login)
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
        def open_form(initial):
            username_choices = {initial["username"]: initial["username"]} if initial else None
            email_choices = {initial["email"]: initial["email"]} if initial.get("email") else None
            FormDialog(self.app, "First administrator",
                       [Field("username", "Username", choices=username_choices, required=True),
                        Field("email", "Email", choices=email_choices)],
                       lambda values: self.app.auth.prepare_setup(**values), initial=initial,
                       success=lambda ticket: show_setup(self.app, ticket))
        self.app.run(self.app.auth.bootstrap_profile, open_form)
