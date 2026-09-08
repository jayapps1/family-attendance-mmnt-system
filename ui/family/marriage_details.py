import tkinter as tk
from tkinter import ttk, messagebox
from ui.components import Field, FormDialog, member_options
from ui.theme import COLORS, SectionCard, ScrollArea
from ui.family.member_form import member_fields
from ui.family.relationship_form import marriage_form


def delete_marriage(app, row, success=None):
    if messagebox.askyesno('Delete marriage', row['couple_name'] +
            '\nDelete only this marriage relationship? Neither member nor any children will be deleted. Parent-child links remain.', parent=app):
        app.run(lambda: app.services['relationships'].delete_marriage(row['id']), success or (lambda _: app.refresh()))


def add_child(app, row, success=None):
    if row['status'] in ('DIVORCED', 'WIDOWED') and not messagebox.askyesno(
            'Historical marriage', 'This marriage is ' + row['status'].lower() + '. Add a child to this couple?', parent=app):
        return
    chooser = tk.Toplevel(app)
    chooser.title('Add child to couple')
    ttk.Label(chooser, text=row['couple_name'], padding=20).pack()
    def choose(new):
        chooser.destroy()
        app.run(app.services['family'].list, lambda members: child_form(app, row, members, new, success))
    ttk.Button(chooser, text='Create new child', style='PrimaryButton.TButton', command=lambda: choose(True)).pack(fill='x', padx=20, pady=8)
    ttk.Button(chooser, text='Link existing child', command=lambda: choose(False)).pack(fill='x', padx=20, pady=(0,20))


def child_form(app, row, members, new=True, success=None):
    roles = {r.title(): r for r in ('FATHER', 'MOTHER', 'GUARDIAN')}
    fields, initial = [], {'marital_status': 'SINGLE', 'living_status': 'LIVING', 'affiliation_type': 'LINEAGE_MEMBER'}
    for key in ('spouse_one', 'spouse_two'):
        person = row[key]
        fields.extend([Field('_' + key, 'Parent', choices=member_options([person]), required=True, section='Couple'),
                       Field(key + '_type', 'Parent role', choices=roles, required=True, section='Couple')])
        initial['_' + key] = person['id']
        initial[key + '_type'] = 'FATHER' if person['sex'] == 'MALE' else 'MOTHER'
    fields.append(Field('birth_order', 'Birth order within this couple', 'int', required=True, section='Couple'))
    initial['birth_order'] = row['child_count'] + 1
    fields += member_fields() if new else [Field('existing_id', 'Existing child', choices=member_options(
        [m for m in members if m['id'] not in (row['spouse_one_id'], row['spouse_two_id'])]), required=True)]
    def save(values):
        values = dict(values)
        options = {k: values.pop(k) for k in ('spouse_one_type', 'spouse_two_type', 'birth_order')}
        values.pop('_spouse_one'); values.pop('_spouse_two')
        options['confirmed_links'] = values.pop('confirmed_links', None)
        if new:
            options['new_member'] = values
        else:
            options['existing_id'] = values['existing_id']
        return app.services['relationships'].add_child_to_marriage(row['id'], media_root=app.media_root, **options)
    def saved(result):
        if result.get('order_warning'):
            messagebox.showwarning('Review child order', result['order_warning'], parent=app)
        (success or (lambda _: app.refresh()))(result)
    class ChildDialog(FormDialog):
        def submit(self):
            if new:
                return super().submit()
            try:
                values = self.values()
            except ValueError as exc:
                messagebox.showerror('Check form', str(exc), parent=self)
                return
            self.button.configure(state='disabled')
            def checked(links):
                if not self.winfo_exists():
                    return
                self.button.configure(state='normal')
                if len(links) == 2:
                    messagebox.showinfo('Child already linked', 'This member is already registered as a child of this couple.', parent=self)
                    return
                if links:
                    link = links[0]
                    key = 'spouse_one' if link['parent_id'] == row['spouse_one_id'] else 'spouse_two'
                    person = row[key]
                    if not messagebox.askyesno('Complete parent links', person['first_name'] + ' is already linked as ' +
                            link['relationship_type'].lower() + '. Keep this role and add the missing parent link?', parent=self):
                        return
                    values[key + '_type'] = link['relationship_type']
                    values['confirmed_links'] = [(str(link['id']), link['relationship_type'])]
                self.button.configure(state='disabled')
                def done(result):
                    self.destroy()
                    saved(result)
                app.run(lambda: save(values), done, lambda: self.button.configure(state='normal') if self.winfo_exists() else None)
            app.run(lambda: app.services['relationships'].child_links_for_marriage(row['id'], values['existing_id']),
                    checked, lambda: self.button.configure(state='normal') if self.winfo_exists() else None)
    form = ChildDialog(app, 'Add child to ' + row['couple_name'], fields, save, initial=initial, success=saved, save_label='Save child and parent links')
    from utils.family_labels import ordinal
    hint = ttk.Label(form, text=ordinal(initial['birth_order']), style='Subtitle.TLabel')
    hint.pack(pady=(0,8))
    def position_hint(event=None):
        try:
            hint.configure(text=ordinal(int(form.inputs['birth_order'].get())))
        except ValueError:
            hint.configure(text='Enter a positive whole-number birth order.')
    form.inputs['birth_order'].bind('<KeyRelease>', position_hint)
    return form


def open_marriage(app, identity):
    app.run(lambda: app.services['relationships'].get_marriage(identity), lambda row: show_marriage(app, row))


def show_marriage(app, row):
    from ui.family.member_profile import open_profile
    dialog = tk.Toplevel(app)
    dialog.title('Couple details')
    dialog.geometry('860x650')
    dialog.configure(background=COLORS['background'])
    area = ScrollArea(dialog)
    area.pack(fill='both', expand=True, padx=24, pady=24)
    card = SectionCard(area.body, row['couple_name'])
    card.pack(fill='x')
    ttk.Label(card.body, text=f"{row['status'].title()}  |  {row.get('marriage_date') or 'Date not recorded'}  |  {row.get('marriage_location') or 'Location not recorded'}", style='Card.TLabel').pack(anchor='w', pady=8)
    if row.get('notes'):
        ttk.Label(card.body, text=row['notes'], style='Card.TLabel', wraplength=720).pack(anchor='w', pady=8)
    for key in ('spouse_one', 'spouse_two'):
        person = row[key]
        ttk.Button(card.body, text=person['first_name'] + ' ' + person['last_name'] + ' | ' + person['family_number'],
                   command=lambda p=person: open_profile(app, p['id'])).pack(anchor='w', pady=4)
    def refreshed(_):
        dialog.destroy(); app.refresh(); open_marriage(app, row['id'])
    actions = ttk.Frame(card.body, style='Card.TFrame')
    actions.pack(fill='x', pady=12)
    ttk.Button(actions, text='Add Child', style='PrimaryButton.TButton', command=lambda: add_child(app, row, refreshed)).pack(side='left', padx=4)
    ttk.Button(actions, text='Edit marriage', command=lambda: app.run(app.services['family'].list,
               lambda members: marriage_form(app, members, row, success=refreshed))).pack(side='left', padx=4)
    ttk.Button(actions, text='Delete marriage', style='DangerButton.TButton', command=lambda: delete_marriage(app, row,
               lambda _: (dialog.destroy(), app.refresh()))).pack(side='left', padx=4)
    ttk.Button(actions, text='Manage Child Order', command=lambda: manage_child_order(app, row, refreshed)).pack(side='left', padx=4)
    if row.get('order_warning'):
        ttk.Label(area.body, text=row['order_warning'], style='Subtitle.TLabel', wraplength=750).pack(anchor='w', pady=8)
    children = SectionCard(area.body, f"Shared children ({row['child_count']})")
    children.pack(fill='x', pady=16)
    for child in row['children']:
        ttk.Button(children.body, text=child['birth_position'] + ': ' + child['first_name'] + ' ' + child['last_name'] + ' | ' + child['family_number'],
                   command=lambda c=child: open_profile(app, c['id'])).pack(anchor='w', pady=4)
    if not row['children']:
        ttk.Label(children.body, text='No children linked to both spouses yet.', style='Card.TLabel').pack(anchor='w')
    return dialog


def manage_child_order(app, row, success=None):
    from ui.theme import COLORS
    dialog = tk.Toplevel(app)
    dialog.title('Manage child order - ' + row['couple_name'])
    dialog.geometry('700x520')
    dialog.configure(background=COLORS['background'])
    dialog.transient(app); dialog.grab_set()
    ttk.Label(dialog, text='Move children into birth order, then save. Dates of birth are a guide; unknown dates are allowed.',
              wraplength=650, padding=16).pack(fill='x')
    children = list(row['children'])
    listing = tk.Listbox(dialog, font=('Segoe UI', 12), exportselection=False)
    listing.pack(fill='both', expand=True, padx=20, pady=8)
    warning = ttk.Label(dialog, wraplength=650, style='Subtitle.TLabel')
    warning.pack(fill='x', padx=20)
    def render(index=0):
        listing.delete(0, 'end')
        for i, child in enumerate(children, 1):
            listing.insert('end', f"{i}. {child['first_name']} {child['last_name']} | DOB: {child.get('date_of_birth') or 'Unknown'}")
        if children:
            listing.selection_set(index)
        dates = [c['date_of_birth'] for c in children if c.get('date_of_birth')]
        warning.configure(text='The recorded child order appears inconsistent with the dates of birth. Please review.' if dates != sorted(dates) else '')
    def move(delta):
        if listing.curselection():
            old = listing.curselection()[0]; new = old+delta
            if 0 <= new < len(children):
                children[old], children[new] = children[new], children[old]
                render(new)
    actions = ttk.Frame(dialog)
    actions.pack(fill='x', padx=20, pady=16)
    ttk.Button(actions, text='Move Up', command=lambda: move(-1)).pack(side='left', padx=4)
    ttk.Button(actions, text='Move Down', command=lambda: move(1)).pack(side='left', padx=4)
    def save():
        ids = [c['id'] for c in children]
        button.configure(state='disabled')
        def done(result):
            dialog.destroy()
            (success or (lambda _: app.refresh()))(result)
        app.run(lambda: app.services['relationships'].reorder_children(row['id'], ids, expected_order=[c['id'] for c in row['children']]),
                done, lambda: button.configure(state='normal') if dialog.winfo_exists() else None)
    button = ttk.Button(actions, text='Save child order', style='PrimaryButton.TButton', command=save)
    button.pack(side='right')
    render()
    return dialog
