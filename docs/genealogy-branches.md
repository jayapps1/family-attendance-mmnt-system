# Genealogy and family branches

## Profile workflows

Open a member's profile from the Family Register or by clicking a relative or tree
node. The Relationships tab now opens first.

- **Add Child**: choose to create a new member or link an existing member. The
  current profile member is fixed as the parent. Father/Mother is suggested from
  that member's sex; you can explicitly choose Guardian or another parent type.
  An optional second existing parent has its own explicit relationship type.
- **Add Parent**: choose an existing parent or create one using the normal member
  fields, including profile-photo upload. A sex-based suggestion never replaces
  a relationship type that you explicitly selected.
- **Add Spouse**: opens the existing marriage workflow with the current member
  fixed as the first spouse. Marriage history remains separate from genealogy.

New-member creation, both parent links, and their audit entries share one outer
database transaction. If either relationship is rejected, the new member is
rolled back and its newly prepared photo is removed.

The relationship summary and clickable sections show recorded parents,
guardians, spouses, children, siblings, grandparents, grandchildren, deeper
ancestors/descendants, wards, and all applicable branches. Empty sections are
omitted; summary counts still show zero where appropriate.

## Direct links and derived relationships

Only FATHER, MOTHER and GUARDIAN are stored in family_relationships. There are
no stored grandmother, sibling, cousin or branch-membership rows.

FATHER/MOTHER links define biological lineage. GUARDIAN links are displayed
separately and do not create biological ancestors, siblings or branch membership.
Cycle validation still checks all direct links, including guardians.

Ancestor/descendant traversal is iterative, has no fixed generation limit,
removes duplicate people, and excludes the queried person. Generation distance
uses the shortest known biological path. Gender supplies labels such as
grandmother, grandson and great-great-granddaughter. Shared biological parents
derive siblings, including half-siblings. Both parents being shared does not
produce duplicate siblings.

RelationshipService also derives biological aunt/uncle, niece/nephew and cousin
labels using a nearest common ancestor. The result describes member A's
relationship **to** member B. These labels are not inferred through marriage.

The service rejects self-links, duplicate parent-child pairs, cycles, and a
second father or mother for the same child. Multiple guardians are allowed.
Existing links can be explicitly edited or removed from **Relationships**;
removal is audited, keeps the members, and immediately affects derived lineage.
Existing conflicting legacy records are not silently rewritten.

## Branches

Use **Family branches** in the sidebar to create, search, edit or open a branch.
A new or edited branch requires an existing founding member. The existing branch
table already contains all required fields; no migration was needed.

A branch contains its founder (generation 0) and biological descendants. New
children appear automatically. No manual member assignments or duplicated
membership records are introduced. Spouses and guardians are not automatically
lineage members.

Branch details show direct children, descendant count, maximum descendant
generation, living/deceased counts, total lineage members, and generation-grouped
members. Living/deceased counts include the founder; UNKNOWN living status
contributes to total members but neither living nor deceased counts.

Search branch members by family number, name, phone or residence. Double-click a
member to open their profile. **View branch tree** includes only the founder and
descendants. Spouses outside the lineage appear separately in branch details.

Profiles show every applicable branch, including inactive branches marked as
such. The Family Register's optional branch filter combines with its existing
text search and Active/Archived filter. Branch lineage itself retains archived
and deceased family members.

Legacy branches with no founder remain in the list and are marked for editing;
they are not deleted or assigned a guessed founder.

## Tree diagram

The Family Tree sidebar entry lets you choose a member. The diagram draws one
node per person, with parent-child connections and openable profiles. Known
co-parents outside the selected biological lineage may be shown and are labelled
as such. They do not become branch descendants.

Separate tabs provide ancestor, descendant, parent, guardian, sibling and spouse
lists with keyboard-openable rows. The generation diagram uses a layered layout
that keeps parents above children and aligns known co-parents where possible.
With multiple ancestry paths, visual layout levels need not equal the shortest
generation distances shown in the lists.

## Service interfaces

RelationshipService provides:

- get_parents, get_father, get_mother, get_guardians, get_children, get_siblings
- get_grandparents, get_grandchildren, get_ancestors, get_descendants
- get_generation_distance(ancestor_id, descendant_id)
- get_relationship_between(member_a_id, member_b_id)
- save / add_parent_child_relationship, validate_relationship, would_create_cycle
- remove_relationship and atomic link_relative

Ancestor and descendant rows include generation and relationship_label.
get_generation_distance returns None when no directed biological path exists.

BranchService provides save, list, details, get_member_branches and
get_branch_members. The latter returns entries containing member and generation.
FamilyService.list accepts an optional branch_id; existing calls remain valid.

## Verification

The test suite passed 120 tests; the unrelated opt-in standalone restore-server
test was skipped. Database-backed tests use rollback transactions. Tests cover
the Akosua/Ama/Abena/Kwame example, both relationship directions, 1,200 generations,
duplicate ancestry paths, parent limits, cycles, guardians, collateral relatives,
atomic member/photo rollback, dynamic branch inheritance, overlapping branches,
spouse exclusion, search and UI workflows.

All main pages were opened in a synthetic-data desktop preview with no callback
errors. Profile, add-child form, tree, branch list, branch details and register
filter layouts were visually inspected. Alembic check detected no new upgrade
operations. Existing records and migrations were preserved.
