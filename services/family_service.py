from datetime import date
from models import FamilyMember, FamilyBranch, Sex, MaritalStatus, LivingStatus
from repositories.family_repository import FamilyRepository
from repositories.base import Repository
from services.base import Service, snapshot
from services.settings_service import SettingsService
from utils.date_utils import age_on
from utils.validators import required, dates, ValidationError


class FamilyService(Service):
    FIELDS = {"first_name", "middle_name", "last_name", "sex", "date_of_birth", "phone_number",
              "current_residence", "marital_status", "living_status", "date_of_death",
              "profile_image_path", "notes"}

    def _validate(self, values):
        unknown = set(values) - self.FIELDS
        if unknown:
            raise ValidationError("Unsupported member fields")
        for key in ("first_name", "last_name"):
            values[key] = required(values.get(key), key.replace("_", " "), 100)
        for key, kind in (("sex", Sex), ("marital_status", MaritalStatus), ("living_status", LivingStatus)):
            if key in values:
                values[key] = kind(values[key])
        born, died = values.get("date_of_birth"), values.get("date_of_death")
        dates(born, died)
        if born and born > date.today() or died and died > date.today():
            raise ValidationError("Birth/death dates cannot be in the future")
        if died and values.get("living_status") is not LivingStatus.DECEASED:
            raise ValidationError("A death date requires deceased status")
        if values.get("profile_image_path"):
            from utils.file_manager import relative_media_path
            values["profile_image_path"] = relative_media_path(values["profile_image_path"])
        return values

    def list(self, search="", active=None):
        with self.transaction() as session:
            rows = FamilyRepository(session).search(search, active)
            return [dict(snapshot(row), age=age_on(row.date_of_birth, row.date_of_death)) for row in rows]

    def create(self, **values):
        values = self._validate(values)
        with self.transaction() as session:
            repo = FamilyRepository(session)
            repo.lock_domain("family_numbers")
            prefix = SettingsService.value(session, "family_number_prefix", "FAM")
            existing = repo.list()
            numbers = [int(row.family_number[len(prefix)+1:]) for row in existing
                       if row.family_number.startswith(prefix + "-") and row.family_number[len(prefix)+1:].isdigit()]
            number = max(numbers, default=0) + 1
            row = repo.add(FamilyMember(family_number=f"{prefix}-{number:06d}", **values))
            self.audit(session, "CREATE_MEMBER", row)
            return snapshot(row)

    def update(self, identity, **changes):
        with self.transaction() as session:
            row = FamilyRepository(session).get(identity, lock=True)
            values = {key: getattr(row, key) for key in self.FIELDS}
            values.update(changes)
            for key, value in self._validate(values).items():
                setattr(row, key, value)
            session.flush()
            self.audit(session, "UPDATE_MEMBER", row)
            return snapshot(row)

    def archive(self, identity, archived=True):
        with self.transaction() as session:
            row = FamilyRepository(session).get(identity, lock=True)
            row.is_active = not archived
            self.audit(session, "ARCHIVE_MEMBER" if archived else "RESTORE_MEMBER", row)

    def branches(self):
        with self.transaction() as session:
            return [snapshot(row) for row in Repository(session, FamilyBranch).list()]

    def create_branch(self, name, founding_member_id=None, description=None):
        with self.transaction() as session:
            if founding_member_id:
                FamilyRepository(session).get(founding_member_id)
            row = Repository(session, FamilyBranch).add(FamilyBranch(
                name=required(name, "Branch name", 150), founding_member_id=founding_member_id,
                description=description))
            self.audit(session, "CREATE_BRANCH", row)
            return snapshot(row)

    def upload_photo(self, identity, source, media_root):
        from pathlib import Path
        from utils.file_manager import FileManager
        from PIL import Image
        if Path(source).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            raise ValidationError("Choose a supported profile image")
        with Image.open(source) as image:
            image.verify()
        files, relative = FileManager(media_root), None
        try:
            with self.transaction() as session:
                row = FamilyRepository(session).get(identity, lock=True)
                relative = files.import_file(Path(source), "members")
                row.profile_image_path = relative
                self.audit(session, "UPDATE_MEMBER", row, "Updated profile image")
                return snapshot(row)
        except Exception:
            if relative:
                files.discard_import(relative)
            raise
