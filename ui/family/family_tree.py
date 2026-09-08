"""A generation diagram with one node per person and openable profiles."""
import tkinter as tk
from tkinter import ttk
from collections import defaultdict, deque
from ui.theme import COLORS, FONTS
from ui.components import Screen, member_options


def generation_layout(data, descendants_only=False):
    root = data["member"]
    members = {root["id"]: root}
    for key in (("descendants",) if descendants_only else ("ancestors", "descendants", "co_parents")):
        members.update({r["id"]: r for r in data.get(key, [])})
    for spouse in data.get('associated_spouses', []):
        members.setdefault(spouse['id'], spouse)
    edges = [r for r in data["edges"] if r["parent_id"] in members and r["child_id"] in members]
    children, indegree, layers = defaultdict(set), {i: 0 for i in members}, {i: 0 for i in members}
    for row in edges:
        parent, child = row["parent_id"], row["child_id"]
        if child not in children[parent]:
            children[parent].add(child)
            indegree[child] += 1
    queue = deque(sorted((i for i in members if indegree[i] == 0), key=str))
    ordered = []
    while queue:
        parent = queue.popleft()
        ordered.append(parent)
        for child in sorted(children[parent], key=str):
            layers[child] = max(layers[child], layers[parent]+1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    for parent in reversed(ordered):
        if children[parent]:
            layers[parent] = min(layers[child] for child in children[parent]) - 1
    for spouse in data.get('associated_spouses', []):
        if spouse['spouse_anchor'] in layers:
            members[spouse['id']] = spouse
            layers[spouse['id']] = layers[spouse['spouse_anchor']]
    grouped = defaultdict(list)
    for identity, layer in layers.items():
        grouped[layer].append(identity)
    positions = {}
    widest = max((len(ids) for ids in grouped.values()), default=1)
    for layer, identities in grouped.items():
        for index, identity in enumerate(sorted(identities, key=lambda i: (data.get("child_order", {}).get(i, ("~", 0)), members[i]["family_number"]))):
            positions[identity] = (50 + (widest-len(identities))*127.5 + index*255, 55 + layer*150)
    return members, edges, positions


def show_tree(app, data, descendants_only=False):
    dialog = tk.Toplevel(app)
    dialog.title("Family tree")
    dialog.geometry("1050x740")
    dialog.minsize(760, 560)
    dialog.configure(background=COLORS["background"])
    root = data["member"]
    ttk.Label(dialog, text=root["first_name"] + " " + root["last_name"] + " - family tree", style="Page.TLabel", padding=(24, 18)).pack(anchor="w")
    ttk.Label(dialog, text="Click a person to open their profile. Lines represent biological parent-child links; guardians remain separate.",
              style="Subtitle.TLabel", wraplength=950).pack(anchor="w", padx=24, pady=(0, 12))
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Generations")
    canvas = tk.Canvas(frame, background=COLORS["background"], highlightthickness=0)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
    vertical = ttk.Scrollbar(frame, command=canvas.yview)
    canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    horizontal.grid(row=1, column=0, sticky="ew")
    vertical.grid(row=0, column=1, sticky="ns")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    members, edges, positions = generation_layout(data, descendants_only)
    drawn = set()
    pairs = set()
    for marriage in data.get('marriages', []):
        a, b = marriage['spouse_one_id'], marriage['spouse_two_id']
        pair = frozenset((a, b))
        if a not in positions or b not in positions or pair in pairs:
            continue
        xa, ya = positions[a]; xb, yb = positions[b]
        # Draw a union only between adjacent, aligned spouses to avoid crossing cards.
        if ya != yb or abs(xa-xb) != 255:
            continue
        pairs.add(pair)
        left, right = sorted((xa, xb))
        center, union_y = (left+210+right)/2, ya+44
        canvas.create_line(left+210, union_y, right, union_y, fill=COLORS['accent'], width=2)
        shared = ({r['child_id'] for r in edges if r['parent_id'] == a}
                  & {r['child_id'] for r in edges if r['parent_id'] == b})
        for child in shared:
            x, y = positions[child]
            canvas.create_line(center, union_y, center, ya+116, x+105, ya+116, x+105, y,
                               fill=COLORS['accent'], width=2, arrow='last')
            drawn.update(((a, child), (b, child)))
    for row in edges:
        if (row['parent_id'], row['child_id']) in drawn:
            continue
        x1, y1 = positions[row["parent_id"]]
        x2, y2 = positions[row["child_id"]]
        canvas.create_line(x1+105, y1+88, x1+105, y1+116, x2+105, y1+116, x2+105, y2,
                           fill=COLORS["border"], width=2, arrow="last")
    from ui.family.member_profile import open_profile
    for identity, member in members.items():
        x, y = positions[identity]
        tag = "member_" + str(identity)
        canvas.create_rectangle(x, y, x+210, y+88, fill=COLORS["accent_soft"] if identity == root["id"] else COLORS["surface"],
                                outline=COLORS["accent"] if identity == root["id"] else COLORS["border"], width=2, tags=tag)
        canvas.create_text(x+12, y+20, text=member["first_name"] + " " + member["last_name"], anchor="w",
                           width=185, font=FONTS["label"], fill=COLORS["primary"], tags=tag)
        canvas.create_text(x+12, y+48, text=member["family_number"], anchor="w", font=FONTS["small"], fill=COLORS["text_secondary"], tags=tag)
        from utils.family_labels import ordinal
        rank = data.get('child_order', {}).get(identity)
        label = ordinal(rank[1]) if rank else member.get('relationship_label', 'Selected member')
        canvas.create_text(x+12, y+70, text=label, anchor="w",
                           width=185, font=FONTS["small"], fill=COLORS["accent"], tags=tag)
        canvas.tag_bind(tag, "<Button-1>", lambda e, i=identity: open_profile(app, i))
        canvas.tag_bind(tag, "<Enter>", lambda e: canvas.configure(cursor="hand2"))
        canvas.tag_bind(tag, "<Leave>", lambda e: canvas.configure(cursor=""))
    bounds = canvas.bbox("all")
    if bounds:
        canvas.configure(scrollregion=(0, 0, bounds[2]+40, bounds[3]+40))
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta/120), "units"))
    keys = ("descendants",) if descendants_only else ("ancestors", "descendants", "parents", "guardians", "siblings", "spouses")
    for key in keys:
        table_frame = ttk.Frame(notebook)
        notebook.add(table_frame, text=key.title())
        tree = ttk.Treeview(table_frame, columns=("name", "number", "relationship", "generation"), show="headings")
        for column in ("name", "number", "relationship", "generation"):
            tree.heading(column, text=column.title())
        scroll = ttk.Scrollbar(table_frame, command=tree.yview)
        across = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=across.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        across.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        for row in data.get(key, []):
            tree.insert("", "end", iid=str(row["id"]), values=(row["first_name"] + " " + row["last_name"], row["family_number"],
                        row.get("relationship_label", ""), row.get("generation", "")))
        by_id = {str(r["id"]): r["id"] for r in data.get(key, [])}
        def selected(event=None, tree=tree, by_id=by_id):
            if tree.selection():
                open_profile(app, by_id[tree.selection()[0]])
        tree.bind("<Double-1>", selected)
        tree.bind("<Return>", selected)
    return dialog


class FamilyTreeScreen(Screen):
    def __init__(self, app):
        super().__init__(app, "Family tree")
        self.members = {}
        self.root_member = ttk.Combobox(self.toolbar, state="readonly", width=45)
        self.root_member.pack(side="left")
        self.button("Open family tree", self.open)
        ttk.Label(self, text="Select a family member to explore their ancestors and descendants.", style="Subtitle.TLabel").pack(anchor="w", pady=20)
        app.run(app.services["family"].list, self.loaded)

    def loaded(self, rows):
        self.members = member_options(rows)
        self.root_member.configure(values=list(self.members))

    def open(self):
        if self.root_member.get() not in self.members:
            raise ValueError("Select a family member first")
        identity = self.members[self.root_member.get()]
        self.app.run(lambda: self.app.services["relationships"].tree(identity), lambda data: show_tree(self.app, data))
