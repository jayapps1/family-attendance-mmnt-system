"""Profile-first workflows for existing or newly created relatives."""
import tkinter as tk
from tkinter import ttk
from models import RelationshipType
from ui.components import Field, FormDialog, member_options, enum_options
from ui.theme import COLORS, SectionCard
from ui.family.member_form import member_fields


def suggested_type(member):
    return {"MALE": "FATHER", "FEMALE": "MOTHER"}.get(member.get("sex"), "GUARDIAN")


def relative_form(app, current, direction, members, success):
    chooser = tk.Toplevel(app)
    chooser.title("Add " + direction)
    chooser.geometry("600x320")
    chooser.configure(background=COLORS["background"])
    chooser.transient(app)
    chooser.grab_set()
    label = member_options([current]).popitem()[0]
    card = SectionCard(chooser, "Add " + direction, ("Parent: " if direction == "child" else "Child: ") + label)
    card.pack(fill="both", expand=True, padx=24, pady=24)
    def open_form(new):
        chooser.destroy()
        return build_relative_form(app, current, direction, members, new, success)
    ttk.Button(card.body, text="Create a new " + direction, style="PrimaryButton.TButton",
               command=lambda: open_form(True)).pack(fill="x", pady=10)
    ttk.Button(card.body, text="Select an existing family member",
               command=lambda: open_form(False)).pack(fill="x", pady=10)
    return chooser


def build_relative_form(app, current, direction, members, new, success):
    eligible = [row for row in members if row["id"] != current["id"]]
    choices = member_options(eligible)
    context = "Parent" if direction == "child" else "Child"
    fields = [Field("_context", context, choices=member_options([current]), required=True, section="Family connection"),
              Field("_relationship", "Parent relationship type", choices=enum_options(RelationshipType), required=True, section="Family connection")]
    initial = {"_context": current["id"], "_relationship": suggested_type(current) if direction == "child" else None,
               "marital_status": "SINGLE", "living_status": "LIVING", "affiliation_type": "LINEAGE_MEMBER"}
    if direction == "child":
        fields += [Field("_second", "Second parent (optional)", choices={"None": None, **choices}, section="Second parent"),
                   Field("_second_type", "Second parent's relationship", choices=enum_options(RelationshipType), section="Second parent")]
    if new:
        fields.extend(member_fields())
    else:
        fields.append(Field("_existing", direction.title(), choices=choices, required=True, section="Family connection"))
    def save(values):
        values = dict(values)
        values.pop("_context")
        kind = values.pop("_relationship")
        existing = values.pop("_existing", None)
        second, second_type = values.pop("_second", None), values.pop("_second_type", None)
        return app.services["relationships"].link_relative(
            current["id"], direction, kind, existing_id=existing, new_member=values if new else None,
            second_parent_id=second, second_parent_type=second_type, media_root=app.media_root)
    form = FormDialog(app, ("Create and link " if new else "Link existing ") + direction, fields, save,
                      initial=initial, success=success, save_label="Save " + direction + " relationship")
    def suggest(source, target, lookup):
        overridden = [False]
        form.inputs[target].bind("<<ComboboxSelected>>", lambda e: overridden.__setitem__(0, True))
        def changed(event=None):
            if not overridden[0]:
                member = lookup(form.inputs[source].get())
                if member:
                    form.inputs[target].set(suggested_type(member).title())
        form.inputs[source].bind("<<ComboboxSelected>>", changed, add="+")
    by_label = {label: next(r for r in eligible if r["id"] == identity) for label, identity in choices.items()}
    if direction == "parent":
        if new:
            suggest("sex", "_relationship", lambda label: {"sex": label.upper()})
        else:
            suggest("_existing", "_relationship", by_label.get)
    if direction == "child":
        suggest("_second", "_second_type", by_label.get)
    return form
