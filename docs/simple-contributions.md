# Simple contribution collection

Use **Contributions > Set annual amount** once for each year. Enter the year and amount; the service creates/reuses the annual type and activates the period in one transaction. Different years can have different amounts. Repeating the same setup is safe; changing an existing year's amount is blocked so recorded obligations and payments are preserved. Advanced contribution setup remains available separately.

For daily work, choose **+ RECORD CONTRIBUTION**, type a name, family number or phone, select the member, enter the amount and save. The contribution defaults to the current active annual period. Member search, contribution selection, current balance and payment entry are all in one form. Cash and today's date are prefilled; reference and remarks are optional. Receipt numbers and the receiving administrator are recorded automatically.

Selecting a member only previews the obligation. Saving the first payment creates a missing annual obligation using the configured period amount, then records the payment and audit events in one transaction. Failed validation rolls back both. Existing obligations retain their original amounts. New obligations and payments require a living, non-archived member aged 23 or older with a recorded date of birth, regardless of affiliation. Eligibility is rechecked when saving, including for existing obligations. Non-annual periods retain explicit assignment rules.

The annual register and daily dashboard include eligible members who have not paid yet, without creating database rows just by opening a screen. These prospective annual amounts contribute to the daily expected/outstanding totals; closed and prior-year reports retain recorded obligations. Closed and prior-year periods show recorded obligations only. Current expected/outstanding totals exclude ineligible members, while collected totals retain their payments. Existing archived/deceased members' recorded obligations and payment histories remain visible.

The register has family number, name, due, paid, balance and status. Select a row to record a payment or view history; double-click opens the appropriate action. Paid-in-full members have payment entry disabled. The member profile includes a contribution card, and payment history shows recalculated due/paid/balance/status alongside all installments, including reversals.

Money remains Decimal/Numeric. Overpayments report the remaining GHS balance. Each installment is a separate receipt-protected transaction. Reversal requires a reason and retains history. The receipt is generated once per form; duplicate submission is disabled and duplicate receipts are rejected. Balance previews reject stale responses when the selected member or period changes, and save revalidates the balance under a period lock.

No database migration is needed for this change. Main files: `services/simple_contribution.py`, `services/contribution_service.py`, `repositories/contribution_repository.py`, contribution UI files including `annual_setup.py` and `payment_form.py`, and `ui/family/member_profile.py`. Tests are in `tests/test_simple_contributions.py` and `tests/test_ui.py`.

Verification: the real Tkinter form test sets an annual amount of GHS 60, searches by full name, phone and family number, then saves GHS 30, GHS 20 and GHS 10. It verifies balances 30, 10 and 0, one obligation, three payment transactions, double-click protection and the final PAID IN FULL state. Service tests also verify first-payment rollback, reversal, archived-member history, affiliation, closed periods, repeated setup and a future year's GHS 80 amount. All test database changes are rolled back.

Original simplified-flow verification: **142 passed, 1 optional live-restore test skipped**. Source compilation, schema check and diff whitespace checks passed. Three simplified screens were opened with zero callback errors; the single-form payment layout was visually inspected. No test payments or members were retained.

The subsequent eligibility correction and dedicated period/payment pages are covered in [Contribution eligibility](contribution-eligibility.md).
