# Couple and child workflow

Update: union-specific birth order and member affiliation now require migration `c637915b29fc`. See [the current implementation report](union-affiliation-payments.md); the no-migration note below describes the earlier couple-only change.

Open Family register > Relationships. Select a marriage, then View couple, Add child to couple, Edit marriage, or Delete marriage. Member profiles also expose couple details and Add Child on the Marriages tab. Details show both separate member records, status, date, location, notes, and unique shared children with profile links.

Add Child offers Create new child (all regular member fields and photo preparation) or Link existing child. Both spouses are fixed and display family numbers. Father/mother roles are suggested from sex; Father, Mother, and Guardian remain selectable. A new member, photo, both links, and audits are saved atomically; failed links roll back the member and remove the new photo. Existing children get only missing links. One existing link requires confirmation and its original role is preserved; two existing links produce a friendly duplicate message. Historical divorced/widowed couples retain children and prompt before additions.

Shared children are the intersection of direct child links for both spouses, including guardian links. Biological genealogy and branch inheritance continue to exclude guardians. Children from another spouse are not included unless linked to both members of this couple. Historical marriage records for the same two people necessarily share the same child list: no per-marriage child ownership is stored.

Trees keep one node per person. Adjacent spouses at the same generation have a union connector and one descent per shared biological child. Other layouts retain direct parent-child lines to avoid crossing member cards.

## Deletion

Marriage deletion requires named confirmation and removes only the marriage record. Parent-child removal names both people and the role. Both operations are audited. Members, other parent links, attendance, and contributions remain.

Archive remains the normal member action. Advanced permanent deletion is visible only to SUPER_ADMIN and is also enforced in the service. The service locks the member and checks every schema foreign key referencing family_members, including nullable references, plus direct member audit history. Any dependency blocks deletion and recommends archive. Therefore normally created, audited members must be archived; permanent deletion is reserved for completely unreferenced imported records. Audit records are never removed. Payment reversal behavior is unchanged.

## Files changed for this request

- services/relationship_service.py: couple queries, atomic child linking, marriage deletion, tree marriage data.
- services/family_service.py: restricted permanent deletion with dependency checks.
- ui/family/marriage_details.py: couple details and new/existing child forms.
- ui/family/family_register.py: couple list/count/actions and deletion controls.
- ui/family/member_profile.py: couple cards and child actions.
- ui/family/family_tree.py: marriage union connectors.
- tests/test_marriage_workflow.py and tests/test_ui.py: service and real Tkinter workflow coverage.
- docs/marriage-workflow.md: workflow and verification notes.

No database migration is required; Alembic check reported no upgrade operations.

## Verification

Full regression suite: 124 passed, one optional standalone live-restore test skipped. A subsequent focused run includes the additional unreferenced-member deletion and nullable founder dependency cases. Compile checks and git diff --check passed.

The requested James Appiah-Gyachie / Agnes Ampoful scenario was exercised by automated PostgreSQL integration and Tkinter tests, not a manual live-data session: create couple, add Michael once, verify both parent links and both parent child lists, add Janet, delete marriage, preserve all four members and links, recreate marriage and recover two shared children, remove James-to-Michael link and preserve Michael. Tkinter tests submit the new-child form and confirm a partially linked existing child. Additional tests cover duplicates, remarriage isolation, historical status, cycles, rollback, and archive/safe deletion. Tests roll back all database changes.

Remaining limits: union drawing is conditional on adjacent aligned spouses; more complex trees use direct links. No live family records were changed, no live restore was performed, and changes have not been committed or pushed.
