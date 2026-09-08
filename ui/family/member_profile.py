import tkinter as tk
from tkinter import ttk
from ui.components import display


def show_profile(app, member, attendance, contributions):
    dialog = tk.Toplevel(app)
    dialog.title("Member profile")
    dialog.geometry("760x600")
    text = tk.Text(dialog, wrap="word", padx=20, pady=20)
    text.pack(fill="both", expand=True)
    lines = [f"{key.replace('_', ' ').title()}: {display(value)}" for key, value in member.items() if key != "id"]
    lines += ["", "Attendance (recorded meetings)", *[f"{key}: {value}" for key, value in attendance.items()],
              "", "Contribution history"]
    lines += [f'{row["status"]}: Due GHS {row["amount_due"]} | Paid {row["total_paid"]} | Balance {row["outstanding"]}'
              for row in contributions]
    text.insert("1.0", "\n".join(lines))
    text.configure(state="disabled")
    if member.get("profile_image_path"):
        from ui.gallery.photo_viewer import show_file
        ttk.Button(dialog, text="View profile image", command=lambda: show_file(app, member["profile_image_path"])).pack(pady=8)
