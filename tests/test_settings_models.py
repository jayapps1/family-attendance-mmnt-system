import uuid
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from models import ApplicationSetting, AuditLog


def test_settings_unique_and_audit_json(db):
    key = "test_" + uuid.uuid4().hex
    db.add(ApplicationSetting(setting_key=key, setting_value="Family"))
    audit = AuditLog(action="TEST", entity_type="setting", details={"key": key})
    db.add(audit)
    db.flush()
    db.refresh(audit)
    assert audit.details == {"key": key}
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(ApplicationSetting(setting_key=key, setting_value="Duplicate"))
            db.flush()
    for model in (ApplicationSetting, AuditLog):
        assert model.__tablename__ in inspect(db.connection()).get_table_names()
