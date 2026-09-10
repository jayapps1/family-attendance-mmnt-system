from datetime import date
from tkinter import ttk
from models import PaymentMethod
from ui.components import Screen, Field, FormDialog, enum_options, show_details, display
from ui.theme import ResponsiveGrid, StatCard
from ui.contributions.payment_form import quick_payment, preferred_period


class RecentPayments(Screen):
    def __init__(self, app):
        super().__init__(app,"Recent Payments",back=self.back)
        ttk.Label(self.page_header,text="View recently recorded family contribution payments.",style="Subtitle.TLabel").pack(anchor="w")
        self.button("+ Record Contribution",lambda:quick_payment(app),variant="Primary")
        self.button("View payment",self.view)
        self.reverse_button=self.button("Reverse payment",self.reverse,variant="Danger")
        self.cards={}
        cards=ResponsiveGrid(self,minimum=150,maximum=5);cards.pack(fill="x",pady=8)
        for key,label in (("payments_today","Payments today"),("collected_today","Collected today"),("payments_month","Payments this month"),("collected_month","Collected this month"),("current_collected","Current period collected")):
            card=cards.add(StatCard(cards,label))
            card.configure(padding=(12,10))
            card.helper.pack_forget()
            for widget in card.winfo_children():
                if isinstance(widget,ttk.Label) and widget is not card.value:
                    widget.configure(wraplength=104)
            self.cards[key]=card
        ttk.Label(self,text="Collection totals exclude reversals. Search filters apply to the transaction table.",style="Subtitle.TLabel").pack(anchor="w",pady=(0,8))
        filters=ttk.Frame(self);filters.pack(fill="x",pady=8)
        self.inputs={}
        for index,(key,label,values) in enumerate((("search","Member / receipt",None),("period","Period",["All Periods"]),("method","Method",["All Methods",*enum_options(PaymentMethod)]),("status","Status",["All","VALID","REVERSED"]),("date","Date YYYY-MM-DD",None))):
            filters.columnconfigure(index,weight=1,uniform="filters")
            ttk.Label(filters,text=label,style="Subtitle.TLabel").grid(row=0,column=index,sticky="w")
            widget=ttk.Combobox(filters,values=values,state="readonly",width=15) if values else ttk.Entry(filters,width=15)
            widget.grid(row=1,column=index,sticky="ew",padx=(0,8),pady=6)
            if values:widget.set(values[0])
            self.inputs[key]=widget
        ttk.Button(filters,text="Search",command=self.load).grid(row=2,column=3,sticky="ew",padx=4)
        ttk.Button(filters,text="Clear",command=self.clear).grid(row=2,column=4,sticky="ew",padx=4)
        self.grid=self.table(("payment_date","receipt_number","family_number","member","period","amount_paid","payment_method","recorded_by_name","payment_status","action"))
        self.grid.empty.configure(text="No contribution payments have been recorded yet.")
        self.grid.tree.column('family_number',anchor='center');self.grid.tree.heading('family_number',anchor='center')
        self.grid.tree.bind('<Double-1>',lambda e:self.view())
        self.grid.tree.bind('<Return>',lambda e:self.view())
        self.grid.tree.bind('<<TreeviewSelect>>',lambda e:self.selection(),add='+')
        self.first=ttk.Button(self,text="Record First Contribution",style="PrimaryButton.TButton",command=lambda:quick_payment(app))
        self.periods={"All Periods":None}
        app.run(app.services['contributions'].periods,self.loaded)

    def back(self):
        from ui.contributions.contribution_dashboard import ContributionDashboard
        self.app.show(ContributionDashboard,remember=False)

    def loaded(self,rows):
        self.periods={"All Periods":None,**{r['title']+' | '+str(r['id'])[:8]:r['id'] for r in rows}}
        self.inputs['period'].configure(values=list(self.periods))
        current=preferred_period([r for r in rows if r['status']=='ACTIVE'])
        self.app.run(lambda:self.app.services['contributions'].payment_summary(current['id'] if current else None),
                     lambda values:[self.cards[k].set(display(v)) for k,v in values.items()])
        self.load()

    def load(self):
        values={k:w.get() for k,w in self.inputs.items()}
        day=date.fromisoformat(values['date']) if values['date'] else None
        self.app.run(lambda:self.app.services['contributions'].recent_payments(
            self.periods.get(values['period']),limit=None,search=values['search'],
            method=enum_options(PaymentMethod).get(values['method']),status=None if values['status']=='All' else values['status'],payment_date=day),self.render)

    def render(self,rows):
        self.grid.set_rows(rows)
        filtered = self.inputs['search'].get() or self.inputs['date'].get() or self.inputs['period'].get()!='All Periods' or self.inputs['method'].get()!='All Methods' or self.inputs['status'].get()!='All'
        self.grid.empty.configure(text='No payments match these filters.' if filtered else 'No contribution payments have been recorded yet.')
        self.reverse_button.configure(state='disabled')
        if rows:self.first.pack_forget()
        else:self.first.pack(anchor='w',pady=8)

    def clear(self):
        for key,widget in self.inputs.items():
            if key in ('search','date'):widget.delete(0,'end')
            else:widget.set({'period':'All Periods','method':'All Methods','status':'All'}[key])
        self.load()

    def selection(self):
        if self.grid.tree.selection():
            self.reverse_button.configure(state='disabled' if self.grid.selected()['is_reversed'] else 'normal')

    def view(self):
        row=self.grid.selected()
        keys=('member','family_number','contribution','period','amount_paid','payment_method','payment_date','reference','receipt_number','received_by_name','recorded_by_name','remarks','payment_status')
        if row['is_reversed']:keys+=('reversed_by_name','reversed_at','reversal_reason')
        show_details(self,'Payment details',{k:row[k] for k in keys})

    def reverse(self):
        row=self.grid.selected()
        if row['is_reversed']:raise ValueError('This payment is already reversed.')
        FormDialog(self.app,f"Reverse GHS {row['amount_paid']:,.2f} - {row['member']}",
            [Field('reason','Confirm reversal: reason required','multiline',required=True)],
            lambda values:self.app.services['contributions'].reverse_payment(row['id'],values['reason']),
            save_label='Reverse payment',button_style='DangerButton.TButton')
