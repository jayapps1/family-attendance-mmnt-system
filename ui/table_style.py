"""One column-order and alignment policy for every application Treeview."""
MONEY = {'amount_due','amount_paid','total_paid','outstanding','amount_per_member','default_amount','amount','expected_total','collected'}
NUMBERS = {'age','child_count','descendant_count','generation','count','total_members'}
CATEGORIES = {'sex','status','living_status','marital_status','affiliation_type','payment_method','is_active','is_reversed','totp_enabled','role','media_type','relationship_type','meeting_type','frequency','eligible_contributors','payment_status','action','eligibility_label'}
LABELS = {
    "eligible_contributors": "Eligible", "eligibility_label": "Eligibility",
    "recorded_by_name": "Recorded by",'affiliation_type':'Affiliation','family_number':'Family No.','phone_number':'Phone','current_residence':'Residence',
          'full_name':'Name','amount_per_member':'Per member','is_active':'Active','totp_enabled':'Enrolled',
          'amount_due':'Amount due','amount_paid':'Amount paid','total_paid':'Paid','outstanding':'Balance','is_reversed':'Payment status'}


def configure_columns(tree, columns):
    for column in columns:
        numeric = column in MONEY | NUMBERS
        dated = column.endswith(('_date','_at','_time')) or column in {'date','year'}
        categorical = column in CATEGORIES
        anchor = 'e' if numeric else 'center' if categorical or dated else 'w'
        width = 130 if numeric or dated else 150 if categorical else 210
        if column == 'eligibility_label': width=310
        if column.endswith('_at'): width=190
        if column in {'family_number','number','phone_number'}: width=135
        if column in {'couple_name','parent','child','member','full_name','name','title','description','file_path','email'}: width=230
        tree.heading(column, text=LABELS.get(column,column.replace('_',' ').title()), anchor=anchor)
        tree.column(column,width=width,minwidth=110,anchor=anchor,stretch=not (numeric or dated or categorical))


def empty_message(columns):
    if 'receipt_number' in columns: return 'No payments recorded for this member.'
    if 'couple_name' in columns: return 'No marriage records found.'
    if 'family_number' in columns or 'full_name' in columns: return 'No members match these filters.'
    if 'username' in columns: return 'No administrator records found.'
    return 'No records found. Use the actions above to add or select records.'
