import uuid
from sqlalchemy.orm import sessionmaker
from models import User, UserRole


def service_context(db):
    actor = User(username="svc_" + uuid.uuid4().hex, role=UserRole.SUPER_ADMIN,
                 totp_enabled=True, is_active=True)
    db.add(actor)
    db.flush()
    factory = sessionmaker(bind=db.connection(), join_transaction_mode="create_savepoint", expire_on_commit=False)
    return factory, actor.id
