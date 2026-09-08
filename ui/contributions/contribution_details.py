import tkinter as tk
from tkinter import ttk
from ui.components import display
from ui.theme import SectionCard, COLORS, StatusBadge
from ui.contributions.payment_form import payment_form


def contribution_details(app, obligation):
    def show(row):
        dialog = tk.Toplevel(app)
        dialog.title('Contribution details')
        dialog.geometry('640x530')
        dialog.configure(background=COLORS['background'])
        card = SectionCard(dialog, row['member'], row['period'])
        card.pack(fill='both', expand=True, padx=24, pady=24)
        for key in ('family_number', 'affiliation_type', 'contribution', 'amount_due', 'total_paid', 'outstanding'):
            ttk.Label(card.body, text=key.replace('_',' ').title() + ': ' + display(row[key]), style='Card.TLabel').pack(anchor='w', pady=6)
        StatusBadge(card.body, row['status']).pack(anchor='w', pady=8)
        def refreshed(_):
            dialog.destroy(); app.refresh(); contribution_details(app, row)
        ttk.Button(card.body, text='PAID IN FULL' if row['outstanding'] == 0 else 'Record Payment', state='normal' if row['can_pay'] else 'disabled', style='PrimaryButton.TButton', command=lambda: payment_form(app, row, refreshed)).pack(anchor='w', pady=8)
        def history():
            from ui.contributions.payment_history import PaymentHistory
            dialog.destroy(); app.show(lambda a: PaymentHistory(a, row))
        ttk.Button(card.body, text='Payment History', command=history).pack(anchor='w')
    app.run(lambda: app.services['contributions'].payment_preview(obligation['contribution_period_id'], obligation['family_member_id']), show)
