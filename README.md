# Family Attendance and Management

Python/ttk desktop application for family records, genealogy, meetings, attendance,
contributions, gallery, family history, administrator access, reports and backups.

## Start on this computer

From PowerShell in the project directory:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe main.py
```

The existing PostgreSQL connection is read from `.env`. Do not replace a working
`.env` with `.env.example`. For a new installation, create a virtual environment,
install `requirements.txt`, copy `.env.example` to `.env`, configure PostgreSQL,
and apply Alembic migrations before starting.

## First administrator and sign-in

The first launch offers initial administrator setup only while no account has
completed authenticator enrollment. Choose a username, scan the QR code with
Google Authenticator or another TOTP app, and enter its six-digit code.

The encryption key is generated locally in the ignored `.env` file during first
setup. Keep a secure separate copy of `APP_ENCRYPTION_KEY`: losing or replacing it
makes existing authenticator secrets unreadable. All installations sharing the
database must use the same key.

Save the recovery codes displayed after enrollment. They are shown once, are
stored only as hashes, and each works once. QR images remain in memory. After
setup, wait for the next authenticator code before signing in: a code cannot be
reused. Five failed attempts temporarily lock the account for 15 minutes.

There is no public registration or password field. Signed-in administrators can
enroll other administrators. Super administrators manage roles, account activity,
authenticator resets, settings and backups. Resetting enrollment invalidates
previous recovery codes. An expired pending enrollment can be restarted by a
super administrator. Initial setup can be resumed if it was interrupted.

## Workflows

- **Family register:** search/filter, add/edit, archive/restore, upload profile
  photos, inspect member profiles, and explore multi-generation family trees.
  Relationships and marriages reference actual members; ancestry cycles and
  duplicate parent/child links are rejected. Branch reports use a founding
  member and all descendants.
- **Meetings / attendance:** create and update meetings, record or revise one
  attendance record per member/meeting, provide permission reasons, and view
  history and summaries. Present and late count as attended. Percentages use
  recorded attendance; missing records are not silently converted to absences.
  Cancelled meetings are excluded from member attendance history.
- **Contributions:** create configurable types and periods, explicitly select
  eligible members, activate a period, record installments, and review balances.
  Amounts are in GHS and are never fixed to 60. Period amounts are snapshots;
  later type defaults do not change obligations. Only active, non-deceased
  members can be assigned. Archived members' existing financial history remains.
  Payments require an active period. Closed periods cannot receive new payments,
  but incorrect payments may still be reversed with a reason.
- **Gallery / history:** create albums and stories, import attachments into
  managed media folders, and view images or open other files with their default
  application. Database rows store relative paths, not binary files.
- **Reports:** export family, branch, genealogy, meeting, attendance, contribution
  and payment reports as PDF or Excel under `reports/pdf` and `reports/excel`.
- **Settings / backup:** configure organization information, numbering prefix,
  session timeout, report headers/footers and backup frequency. Backups contain
  a PostgreSQL custom-format dump, managed media, and a verified SHA-256 manifest.
  They do not include `.env`; preserve the encryption key separately.

A single Tk root owns navigation. A background worker handles database and
export/backup work; UI code calls services, services own transactions and audit
events, and repositories own queries. Financial and genealogy writes use
database locks to serialize competing updates.

## Backups

PostgreSQL client tools are discovered on PATH or under the Windows PostgreSQL
installation directory. Set `PG_DUMP_PATH` in `.env` if necessary. The client
must support the server version. `pg_dump` receives its password through its
process environment, never a command-line argument.

Daily/weekly/monthly backups run while a super administrator is signed in and
the application is running. The schedule checks hourly; monthly means 30 days.
This is not an operating-system background scheduler. No destructive restore
operation is implemented. Backups should also be copied to your managed off-device
storage. Concurrent media changes from another application instance are not an
atomic snapshot with PostgreSQL.

## Validation

```powershell
.\.venv\Scripts\python.exe -m compileall -q models repositories services ui utils main.py
$env:FAMILY_RUN_DB_TESTS = "1"
$env:FAMILY_RUN_UI_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m alembic check
```

Database tests use outer transactions and roll back fixture data. They do not
reset the database or replace Alembic with `create_all`. UI tests use withdrawn
Tk windows and require a desktop session. Without the opt-in variables these
integration tests are skipped. The backup unit test substitutes a fake
`pg_dump`. Additional opt-in checks are available:

```powershell
$env:FAMILY_RUN_MIGRATION_TESTS = "1"
$env:FAMILY_RUN_BACKUP_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_migrations.py tests/test_live_backup.py -q
```

The migration check creates and removes a uniquely named disposable PostgreSQL
schema and exercises fresh installation plus downgrade/re-upgrade of the new
phases. The live backup check runs installed `pg_dump`, verifies the backup
manifest and confirms that `pg_restore --list` can read the archive. It does not
restore anything into the application database.

Financial history and audit logs have no delete UI. Application permissions do
not replace PostgreSQL account permissions; protect the database and local
configuration using appropriate operating-system access controls.
