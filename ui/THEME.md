# Native desktop theme

The interface uses native Tkinter/ttk with Segoe UI. No new dependencies were introduced.

## Components

`theme.py` defines the palette, spacing, font hierarchy, ttk styles, CardFrame, SectionCard, StatCard, StatusBadge, ResponsiveGrid and ScrollArea. `components.py` applies them to shared page headers, wrapping action bars, tables, typed forms and reading/detail dialogs. `gallery/album_cards.py` adds selectable album cards with asynchronously loaded thumbnails.

The shell uses a 236px navy sidebar, grouped scrollable navigation, a white header, and a minimum window size of 1100 x 760. Forms use white sections, keyboard focus indication, scrolling, and persistent Save/Cancel controls. Tables retain their original row data and selection APIs, use alternating rows, 34px row height, currency alignment and a selected-record status badge.

## Exact palette

| Token | Hex |
| --- | --- |
| primary | `#17324D` |
| primary_dark | `#102436` |
| accent | `#1F7A76` |
| accent_hover | `#17645F` |
| accent_soft | `#E8F4F2` |
| gold | `#D6A84B` |
| gold_hover | `#BF9138` |
| background | `#F4F7FA` |
| surface | `#FFFFFF` |
| surface_alt | `#EDF2F6` |
| text | `#18212B` |
| text_secondary | `#62707D` |
| muted | `#87939D` |
| border | `#D7E0E7` |
| success | `#2E8B57` |
| success_bg | `#E9F6EF` |
| warning | `#D79028` |
| warning_bg | `#FFF5E5` |
| danger | `#C84C4C` |
| danger_bg | `#FCECEC` |
| info | `#3478B8` |
| info_bg | `#EAF3FB` |
| disabled | `#ADB7C0` |
| sidebar_text | `#DCE6ED` |
| alternate | `#F8FAFC` |
| selection | `#DCEFED` |
| success_text | `#22663F` |
| warning_text | `#85530F` |
| danger_text | `#A73535` |

Darker success, warning and danger foregrounds support readable small text. Status words remain visible alongside colors. Button variants are PrimaryButton, SecondaryButton, SuccessButton, WarningButton, DangerButton and GhostButton (all `.TButton`).

## UI files changed for this redesign

- `ui/theme.py` (new), `ui/components.py`, `ui/app.py`
- `ui/dashboard/dashboard.py`
- `ui/family/family_register.py`, `member_form.py`, `member_profile.py`, `family_tree.py`
- `ui/meetings/meeting_list.py`, `ui/attendance/attendance_screen.py`
- `ui/contributions/contribution_dashboard.py`, `contribution_register.py`, `payment_form.py`, `payment_history.py`
- `ui/gallery/gallery_screen.py`, `album_cards.py` (new)
- `ui/history/history_screen.py`, `ui/reports/reports_screen.py`, `ui/settings/settings_screen.py`
- `ui/auth/login_window.py`, `authenticator_setup.py`

Administrators, audit logs, relationship forms, contribution forms and other existing dialogs inherit the shared styling. Earlier administrator/seeder changes already present in the workspace are separate from this redesign.

## Validation

- Python compilation passed.
- Full opt-in test suite: 93 passed, including PostgreSQL rollback integration tests, migrations, backup verification and UI tests.
- All 11 main sidebar routes were invoked in a visible desktop preview with synthetic records, with zero callback errors. Related relationship/register/history screens were exercised by UI tests.
- Visually inspected dashboard, register, gallery, reports, settings, administrators, audit, meetings, attendance, login, profile, member form, genealogy, meeting details, attendance summary, story reader and authenticator setup; checked the financial screen at 1100 x 760.
- Confirmed populated tables, album selection and thumbnail rendering.
- Actual Save buttons were tested against real services for member edits, payment recording and payment reversal. Test records were rolled back. Typed date/money conversion and the danger reversal button were checked.
- SHA-256 comparison against the starting workspace confirmed no changes to models, migrations, repositories, services or configuration during the UI task.

## Practical limits

No known blocking UI or technical issue remains from these checks. The genealogy viewer remains a native hierarchical tree. Tables use horizontal scrolling for wide records; smaller windows use scrolling for navigation and long content. Native confirmation/error dialogs and file pickers retain Windows styling. Status colors in tables appear on the selected-record badge, with text labels retained in every row. Large production datasets and every possible monitor/DPI configuration were not exhaustively tested. Visual previews used synthetic records; authenticator setup was previewed with a dummy key, without changing the real administrator's enrollment.
