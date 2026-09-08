from models import ApplicationSetting
from repositories.base import Repository
from services.base import Service, snapshot
from utils.validators import required, money, ValidationError


class SettingsService(Service):
    KEYS = {"family_name", "family_number_prefix", "default_contribution_amount",
            "session_timeout_minutes", "backup_frequency", "report_header", "report_footer",
            "organization_address", "organization_phone"}

    @staticmethod
    def value(session, key, default=""):
        rows = Repository(session, ApplicationSetting).list(ApplicationSetting.setting_key == key)
        return rows[0].setting_value if rows else default

    def list(self):
        with self.transaction() as session:
            return [snapshot(row) for row in Repository(session, ApplicationSetting).list()]

    def set(self, key, value):
        if key not in self.KEYS:
            raise ValidationError("Unknown application setting")
        value = str(value).strip()
        if key == "session_timeout_minutes" and (not value.isdigit() or not 1 <= int(value) <= 1440):
            raise ValidationError("Session timeout must be 1 to 1440 minutes")
        if key == "backup_frequency" and value not in {"MANUAL", "DAILY", "WEEKLY", "MONTHLY"}:
            raise ValidationError("Invalid backup frequency")
        if key == "default_contribution_amount":
            value = str(money(value))
        if key == "family_number_prefix":
            required(value, "Prefix", 12)
            if not value.replace("-", "").isalnum():
                raise ValidationError("Prefix must contain letters, digits or hyphens")
        with self.transaction(super_admin=True) as session:
            repo = Repository(session, ApplicationSetting)
            repo.lock_domain("settings")
            rows = repo.list(ApplicationSetting.setting_key == key)
            row = rows[0] if rows else repo.add(ApplicationSetting(setting_key=key, setting_value=value))
            row.setting_value, row.updated_by = value, self.actor_id
            session.flush()
            self.audit(session, "UPDATE_SETTING", row)
            return snapshot(row)
