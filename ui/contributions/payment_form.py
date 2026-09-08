from datetime import date
from decimal import Decimal, InvalidOperation
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from models import PaymentMethod
from ui.components import FormDialog, enum_options, member_options, display
from ui.theme import COLORS, SectionCard, ScrollArea, StatusBadge


def preferred_period(periods):
    return next((p for p in periods if p.get('year') == date.today().year and p.get('frequency') == 'ANNUAL'), periods[0] if periods else None)


def quick_payment(app, member_id=None, success=None, period_id=None):
    def loaded(data):
        members, periods = data
        active = [p for p in periods if p['status'] == 'ACTIVE']
        if not active:
            messagebox.showinfo('Annual contribution setup', 'Set the annual contribution year and amount first.', parent=app)
            from ui.contributions.annual_setup import annual_setup
            annual_setup(app)
            return
        RecordContributionForm(app, members, active, member_id=member_id, period_id=period_id, success=success)
    app.run(lambda: (app.services['family'].list(), app.services['contributions'].periods()), loaded)


def payment_form(app, obligation, success=None):
    quick_payment(app, obligation['family_member_id'], success, obligation['contribution_period_id'])


class RecordContributionForm(FormDialog):
    """One screen: searchable member, live balance, and payment fields."""
    def __init__(self, app, members, periods, *, member_id=None, period_id=None, success=None):
        tk.Toplevel.__init__(self, app)
        self.app, self.members, self.periods = app, members, periods
        self.title('Record Contribution'); self.geometry('800x740'); self.minsize(680,600)
        self.configure(background=COLORS['background']); self.transient(app); self.grab_set()
        self.inputs = {}; self.version = 0; self.preview = None; self.saving = False
        self.receipt = 'R-' + uuid.uuid4().hex
        self.success = success
        self.people = member_options(members)
        self.period_options = {p['title'] + (f" ({p['year']})" if p.get('year') and str(p['year']) not in p['title'] else '') +
                               (' | ' + str(p['id'])[:8] if sum(q['title'] == p['title'] for q in periods) > 1 else ''): p['id'] for p in periods}
        ttk.Label(self, text='Record Contribution', style='Page.TLabel', padding=(24,16)).pack(anchor='w')
        area = ScrollArea(self); area.pack(fill='both', expand=True, padx=24)
        selection = SectionCard(area.body, 'Member and contribution'); selection.pack(fill='x', pady=(0,12))
        ttk.Label(selection.body, text='Member *  -  Type a name, family number or phone, then select a match.', style='CardHelper.TLabel').pack(anchor='w')
        member = ttk.Combobox(selection.body, values=list(self.people))
        member.pack(fill='x', pady=(4,10)); self.inputs['member_id'] = member
        ttk.Label(selection.body, text='Contribution *', style='CardHelper.TLabel').pack(anchor='w')
        period = ttk.Combobox(selection.body, values=list(self.period_options), state='readonly')
        period.pack(fill='x', pady=4); self.inputs['period_id'] = period
        chosen = period_id or preferred_period(periods)['id']
        period.set(next((label for label, identity in self.period_options.items() if identity == chosen), next(iter(self.period_options))))
        if member_id:
            member.set(next((label for label, identity in self.people.items() if identity == member_id), ''))
        summary = SectionCard(area.body, 'Contribution balance'); summary.pack(fill='x', pady=(0,12))
        self.member_info = ttk.Label(summary.body, style='CardHelper.TLabel'); self.member_info.pack(anchor='w')
        values = ttk.Frame(summary.body, style='Card.TFrame'); values.pack(fill='x', pady=8)
        for index, (key,label) in enumerate((('_amount_due','Amount due'),('_total_paid','Already paid'),('_outstanding','Balance before payment'))):
            values.columnconfigure(index, weight=1)
            ttk.Label(values, text=label, style='CardHelper.TLabel').grid(row=0,column=index,sticky='w')
            widget = ttk.Label(values, text='--', style='CardTitle.TLabel')
            widget.grid(row=1,column=index,sticky='w',pady=6)
            widget.get = lambda w=widget: str(w.cget('text'))
            self.inputs[key] = widget
        self.badge = StatusBadge(summary.body, 'Select a member', tone='info'); self.badge.pack(anchor='w')
        payment = SectionCard(area.body, 'Payment'); payment.pack(fill='x')
        for col in (0,1): payment.body.columnconfigure(col,weight=1)
        for index,(key,label,initial) in enumerate((('amount_paid','Amount received (GHS) *',''),('payment_method','Payment method *','Cash'),
                ('payment_date','Payment date *',date.today().isoformat()),('reference','Reference (optional)',''))):
            row,col=divmod(index,2)
            ttk.Label(payment.body,text=label,style='CardHelper.TLabel').grid(row=row*2,column=col,sticky='w',padx=(0,12),pady=(8,4))
            widget = ttk.Combobox(payment.body,values=list(enum_options(PaymentMethod)),state='readonly') if key == 'payment_method' else ttk.Entry(payment.body)
            widget.grid(row=row*2+1,column=col,sticky='ew',padx=(0,12))
            if key == 'payment_method': widget.set(initial)
            else: widget.insert(0,initial)
            self.inputs[key] = widget
        ttk.Label(payment.body,text='Remarks (optional)',style='CardHelper.TLabel').grid(row=4,column=0,sticky='w',pady=(10,4))
        self.inputs['remarks'] = ttk.Entry(payment.body); self.inputs['remarks'].grid(row=5,column=0,columnspan=2,sticky='ew')
        controls = ttk.Frame(self,padding=(24,14)); controls.pack(fill='x')
        self.button = ttk.Button(controls,text='Save Payment',style='PrimaryButton.TButton',command=self.submit,state='disabled')
        self.button.pack(side='right'); ttk.Button(controls,text='Cancel',command=self.destroy).pack(side='right',padx=8)
        member.bind('<<ComboboxSelected>>',lambda e:self.load_balance())
        period.bind('<<ComboboxSelected>>',lambda e:self.load_balance())
        member.bind('<KeyRelease>',self.search)
        member.bind('<Return>',self.choose_match)
        self.bind('<Escape>',lambda e:self.destroy())
        self.load_balance()

    def search(self,event=None):
        if event and event.keysym in ('Up','Down','Return','Escape','Tab'): return
        term = self.inputs['member_id'].get().casefold().strip()
        by_id = {m['id']:m for m in self.members}
        matches = [label for label,identity in self.people.items() if term in ' '.join(str(by_id[identity].get(k) or '')
                   for k in ('family_number','first_name','middle_name','last_name','phone_number')).casefold().replace('  ',' ')]
        self.inputs['member_id'].configure(values=matches)
        self.load_balance()

    def choose_match(self,event=None):
        values = self.inputs['member_id'].cget('values')
        if values:
            self.inputs['member_id'].set(values[0]); self.load_balance()
        return 'break'

    def selection(self):
        return self.people.get(self.inputs['member_id'].get()), self.period_options.get(self.inputs['period_id'].get())

    def load_balance(self):
        self.version += 1; version = self.version
        self.preview = None; self.button.configure(state='disabled')
        for key in ('_amount_due','_total_paid','_outstanding'): self.inputs[key].configure(text='--')
        self.badge.set('Select a member', 'info'); self.member_info.configure(text='')
        member, period = self.selection()
        if member is None or period is None: return
        def loaded(row):
            if not self.winfo_exists() or version != self.version: return
            self.preview = row
            for key in ('amount_due','total_paid','outstanding'): self.inputs['_'+key].configure(text=display(row[key]))
            self.member_info.configure(text=row['family_number'] + ' | ' + display(row['affiliation_type']))
            self.badge.set('PAID IN FULL' if row['outstanding'] == 0 else row['status'], 'success' if row['outstanding'] == 0 else None)
            if not row['can_pay'] and row['outstanding'] > 0: self.badge.set('Payment unavailable for this member / period', 'warning')
            self.button.configure(state='normal' if row['can_pay'] and not self.saving else 'disabled')
        self.app.run(lambda:self.app.services['contributions'].payment_preview(period,member),loaded)

    def submit(self):
        if self.saving or not self.preview or not self.preview['can_pay']: return
        try:
            amount=Decimal(self.inputs['amount_paid'].get().strip())
            paid_on=date.fromisoformat(self.inputs['payment_date'].get().strip())
            method=enum_options(PaymentMethod)[self.inputs['payment_method'].get()]
        except (ValueError,InvalidOperation,KeyError):
            messagebox.showerror('Check payment','Enter an amount, payment method and date (YYYY-MM-DD).',parent=self); return
        member,period=self.selection()
        reference=self.inputs['reference'].get().strip() or None
        remarks=self.inputs['remarks'].get().strip() or None
        self.saving=True; self.button.configure(state='disabled')
        def done(result):
            self.destroy()
            self.app.last_contribution_result=result['summary']
            (self.success or (lambda _:self.app.refresh()))(result)
        def failed():
            if self.winfo_exists(): self.saving=False; self.load_balance()
        self.app.run(lambda:self.app.services['contributions'].record_contribution(member,period,amount,method,
            payment_date=paid_on,reference=reference,remarks=remarks,receipt_number=self.receipt),done,failed)
