# Member photos, Google Drive backups and restore

## Member photos

Open **Family register > Add member** or **Edit**. In **Profile / notes**, choose
**Upload / resize photo**. Select a JPG, PNG, WebP or GIF, then adjust zoom,
horizontal/vertical position, rotation, and output size (256, 512 or 1024 pixels).
The preview shows the square portrait that will be saved.

**Use this photo** accepts the crop into the form. **Save member** stores the
prepared JPEG and the member record. Cancelling the form writes no new photo.
The source image is unchanged, EXIF orientation is applied, and the saved JPEG
does not retain EXIF metadata. Images above 30 megapixels are rejected to keep
processing manageable. Removing a photo removes its member reference; older media
is retained for backup/recovery.

## Google Drive destination

This computer is configured to use:

- Web folder: [family mamanagement backup](https://drive.google.com/drive/folders/1G_WIA9t2frW7Lr8TN035LXhPK12Mv0ZE)
- Google Drive desktop folder: `G:/My Drive/family mamanagement backup`
- Local backup folder: `backups/`

The device-specific location is stored as `GOOGLE_DRIVE_BACKUP_DIR` in the
untracked `.env`. On another computer, choose **Settings > Google Drive folder**
and select the corresponding folder inside Google Drive for desktop.

**Back up database and media** creates and checksum-verifies a local ZIP, then
copies and checksum-verifies the ZIP in the Drive desktop folder. Google Drive
for desktop uploads it to the cloud. The app distinguishes a verified desktop
copy from cloud completion: check Google's sync indicator for upload completion.
This uses the existing signed-in Drive desktop application, without new OAuth
credentials or API dependencies.
[Google's sync documentation](https://support.google.com/drive/answer/10838124?hl=en)

If Drive is unavailable, the local ZIP remains safe and the app reports that the
Drive copy is pending. **Sync backups to Drive** verifies/copies all local backup
ZIPs without overwriting a different file with the same name. Scheduled backup
checks retry local copies while a super administrator is signed in. Scheduling
requires the app and Drive for desktop to be running.

The backup dated 8 September 2026, 06:36 UTC was copied and verified by listing
the specified cloud folder. It is stored as
`family_20260908_063619_e1959f28.zip`.

## Restore the latest backup

Only an active, enrolled super administrator can restore.

1. Open **Settings > Restore latest backup**.
2. The app finds the latest timestamped backup locally or in the configured
   Drive desktop folder. A newer Drive backup is copied locally and validated.
3. Review its name, timestamp, size and media count.
4. Close other Family Management windows and database tools.
5. Type **RESTORE** and click **Restore this backup**.

Restoring replaces the current database, including changes made after the backup.
A verified safety backup of the current database/media is created before changes.
Its Drive copy is attempted too; Drive being offline does not discard the local
safety archive.

The app rejects malformed archives, duplicate/unsafe paths, checksum mismatches,
changed backup files and database versions that differ from this application's
migration head. PostgreSQL restore uses a single transaction and exits on error.
[PostgreSQL restore documentation](https://www.postgresql.org/docs/current/app-pgrestore.html)

Media is staged before replacement. A normal database restore failure puts the
previous media files back. Newer unreferenced media is retained rather than
deleted. Navigation and new operations are blocked in the restoring window;
after success, sign in again. A restore audit entry is added when available.

The original `.env` is not included or overwritten. Preserve its
`APP_ENCRYPTION_KEY` separately: authenticator secrets from the backup require
the matching key.

After a machine crash or failed media rollback, the recovery journal
`backups/restore-in-progress.json` and private `.family-restore-*` staging folder
are retained for review. Another restore is blocked until that recovery state is
resolved. These files and all backups/media are excluded from Git.

This implementation does not make independently running applications cooperate
with a global maintenance lock. Close all other clients before restoring and do
not reopen them until it completes.

## Validation

Tests cover portrait cropping and output sizes, original-file preservation,
member/photo save cleanup, Drive copy verification and collisions, offline Drive,
downloading a newer Drive backup, invalid archives, restore confirmation, backup
changes, media rollback and retained recovery journals.

UI checks exercise member saves with an uploaded portrait, the crop editor,
restore confirmation, and blocked navigation during restore. Screenshots were
reviewed with synthetic records.

A separate opt-in test starts a disposable PostgreSQL cluster, performs a real
database/media backup and restore, verifies the restored data and safety archive,
and stops the temporary server. It never restores into the live application
database.
