import tkinter as tk
from tkinter import ttk
from collections import defaultdict


def show_tree(app, data):
    dialog = tk.Toplevel(app)
    dialog.title("Family tree")
    dialog.geometry("900x650")
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=12, pady=12)
    root = data["member"]
    for key in ("ancestors", "descendants", "spouses", "siblings"):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=key.title())
        tree = ttk.Treeview(frame, columns=("number",), show="tree headings")
        tree.heading("#0", text="Family member")
        tree.heading("number", text="Family number")
        scrollbar = ttk.Scrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        def label(member):
            return f'{member["first_name"]} {member["last_name"]}'
        if key in ("spouses", "siblings"):
            for row in data[key]:
                tree.insert("", "end", text=label(row), values=(row["family_number"],))
            continue
        members = {r["id"]: r for r in data[key]}
        members[root["id"]] = root
        edges = defaultdict(list)
        for edge in data["edges"]:
            a, b = edge["parent_id"], edge["child_id"]
            if key == "ancestors":
                a, b = b, a
            if a in members and b in members:
                edges[a].append(b)
        node = tree.insert("", "end", text=label(root), values=(root["family_number"],), open=True)
        pending, expanded = [(root["id"], node)], set()
        while pending:
            identity, parent = pending.pop()
            if identity in expanded:
                continue
            expanded.add(identity)
            for child in edges[identity]:
                row = members[child]
                entry = tree.insert(parent, "end", text=label(row), values=(row["family_number"],))
                pending.append((child, entry))
