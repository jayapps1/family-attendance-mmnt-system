from models import RelationshipType, MarriageStatus
from ui.components import Field, FormDialog, member_options, enum_options


def relationship_form(app, members, row=None):
    choices = member_options(members)
    FormDialog(app, "Parent / child relationship", [
        Field("parent_id", "Parent or guardian", choices=choices, required=True),
        Field("child_id", "Child", choices=choices, required=True),
        Field("relationship_type", "Relationship", choices=enum_options(RelationshipType), required=True)],
        lambda values: app.services["relationships"].save(**values, identity=row["id"] if row else None), initial=row)


def marriage_form(app, members, row=None, *, current=None, success=None):
    choices = member_options(members)
    form = FormDialog(app, "Marriage", [
        Field("spouse_one_id", "First spouse", choices=member_options([current]) if current else choices, required=True),
        Field("spouse_two_id", "Second spouse", choices=choices, required=True),
        Field("status", "Status", choices=enum_options(MarriageStatus), required=True),
        Field("marriage_date", "Marriage date", "date"), Field("marriage_location", "Location"),
        Field("notes", "Notes", "multiline")],
        lambda values: app.services["relationships"].save_marriage(**values, identity=row["id"] if row else None),
        initial=row or {"status": "MARRIED", "spouse_one_id": current["id"] if current else None}, success=success)

    if row is None:
        from tkinter import ttk, messagebox
        def create_spouse():
            label = form.inputs['spouse_one_id'].get()
            identity = (member_options([current]) if current else choices).get(label)
            if identity is None:
                messagebox.showerror('Select spouse', 'Select the first spouse before creating their new spouse.', parent=form)
                return
            person = next(r for r in members if r['id'] == identity)
            form.destroy()
            new_spouse_form(app, person, success)
        ttk.Button(form, text='Create a new spouse instead', command=create_spouse).pack(pady=(0,12))
    return form


def new_spouse_form(app, current, success=None):
    from ui.family.member_form import member_fields
    fields = [Field('_current', 'Existing spouse', choices=member_options([current]), required=True, section='Marriage')]
    fields += member_fields()
    fields += [Field('_status', 'Marriage status', choices=enum_options(MarriageStatus), required=True, section='Marriage'),
               Field('_date', 'Marriage date', 'date', section='Marriage'), Field('_location', 'Marriage location', section='Marriage')]
    def save(values):
        values = dict(values); values.pop('_current')
        options = dict(status=values.pop('_status'), marriage_date=values.pop('_date'), marriage_location=values.pop('_location'))
        return app.services['relationships'].create_spouse_and_marriage(current['id'], values, media_root=app.media_root, **options)
    return FormDialog(app, 'Create spouse and marriage', fields, save,
        initial={'_current': current['id'], '_status': 'MARRIED', 'marital_status': 'MARRIED', 'living_status': 'LIVING', 'affiliation_type': 'MARRIED_IN'},
        success=success, save_label='Save spouse and marriage')
