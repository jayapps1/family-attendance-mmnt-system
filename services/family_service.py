from datetime import date
from models import FamilyMember, FamilyBranch, Sex, MaritalStatus, LivingStatus, FamilyAffiliationType
from repositories.family_repository import FamilyRepository
from repositories.base import Repository
from services.base import Service, snapshot
from services.settings_service import SettingsService
from utils.date_utils import age_on
from utils.validators import required, dates, ValidationError


class FamilyService(Service):
    FIELDS = {"first_name", "middle_name", "last_name", "sex", "date_of_birth", "phone_number",
              "current_residence", "marital_status", "living_status", "date_of_death",
              "profile_image_path", "notes", "affiliation_type"}

    def _validate(self, values):
        unknown = set(values) - self.FIELDS
        if unknown:
            raise ValidationError("Unsupported member fields")
        for key in ("first_name", "last_name"):
            values[key] = required(values.get(key), key.replace("_", " "), 100)
        for key, kind in (("affiliation_type", FamilyAffiliationType), ("sex", Sex), ("marital_status", MaritalStatus), ("living_status", LivingStatus)):
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

    def list(self, search="", active=None, branch_id=None, affiliation_type=None, living_status=None):
        with self.transaction() as session:
            rows = FamilyRepository(session).search(search, active, affiliation_type, living_status)
            if branch_id is not None:
                from services.relationship_service import RelationshipService
                branch = Repository(session, FamilyBranch).get(branch_id)
                if branch.founding_member_id is None:
                    raise ValidationError("This branch needs a founding member.")
                ids = {branch.founding_member_id} | set(RelationshipService.graph(session).depths(branch.founding_member_id))
                rows = [row for row in rows if row.id in ids]
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
            old_affiliation = row.affiliation_type
            values = {key: getattr(row, key) for key in self.FIELDS}
            values.update(changes)
            for key, value in self._validate(values).items():
                setattr(row, key, value)
            session.flush()
            self.audit(session, "UPDATE_MEMBER", row)
            if old_affiliation != row.affiliation_type:
                self.audit(session, "UPDATE_AFFILIATION", row)
            return snapshot(row)

    def archive(self, identity, archived=True):
        with self.transaction() as session:
            row = FamilyRepository(session).get(identity, lock=True)
            row.is_active = not archived
            self.audit(session, "ARCHIVE_MEMBER" if archived else "RESTORE_MEMBER", row)

    def branches(self):
        with self.transaction() as session:
            return [snapshot(row) for row in Repository(session, FamilyBranch).list()]

    def create_branch(self, name, founding_member_id=None, description=None, is_active=True):
        from services.branch_service import BranchService
        return BranchService(self.sessions, self.actor_id).save(name, founding_member_id, description, is_active)

    def get_branch_members(self, branch_id, search=""):
        from services.branch_service import BranchService
        return BranchService(self.sessions, self.actor_id).get_branch_members(branch_id, search)

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

    def save_with_photo(self, values, media_root, identity=None):
        """Save a prepared portrait and the member together; remove new media on failure."""
        from utils.profile_image import PreparedPhoto
        from utils.file_manager import FileManager
        import uuid
        values = dict(values)
        photo = values.get("profile_image_path")
        relative = None
        files = FileManager(media_root)
        try:
            if isinstance(photo, PreparedPhoto):
                relative = "members/" + uuid.uuid4().hex + ".jpg"
                target = files.resolve(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(photo.data)
                values["profile_image_path"] = relative
            return self.update(identity, **values) if identity else self.create(**values)
        except Exception:
            if relative:
                files.discard_import(relative)
            raise

    def delete_permanently(self, identity):
        from sqlalchemy import select, exists
        from models import AuditLog
        from models.base import Base
        with self.transaction(super_admin=True) as session:
            repo = FamilyRepository(session)
            repo.lock_domain('genealogy')
            row = repo.get(identity, lock=True)
            blocked = session.scalar(select(exists().where(AuditLog.entity_type == 'family_members', AuditLog.entity_id == identity)))
            for table in Base.metadata.tables.values():
                for column in table.columns:
                    if any(fk.target_fullname == 'family_members.id' for fk in column.foreign_keys):
                        blocked = blocked or session.scalar(select(exists().where(column == identity)))
            if blocked:
                raise ValidationError('This member cannot be permanently deleted because historical records are linked to them. Archive the member instead.')
            self.audit(session, 'DELETE_MEMBER', row, 'Permanently deleted unreferenced member')
            session.delete(row)
