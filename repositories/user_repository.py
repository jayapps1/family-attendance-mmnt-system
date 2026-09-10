from sqlalchemy import select, or_, func
from models import User, RecoveryCode
from repositories.base import Repository


class UserRepository(Repository[User]):
    def __init__(self, session):
        super().__init__(session, User)

    def find_identifier(self, identifier: str, *, lock=False):
        query = select(User).where(or_(func.lower(User.username) == identifier.lower(),
                                      func.lower(User.email) == identifier.lower()))
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)

    def recovery_codes(self, user_id):
        return list(self.session.scalars(select(RecoveryCode).where(
            RecoveryCode.user_id == user_id, RecoveryCode.is_used.is_(False)
        ).with_for_update()))

    def names(self):
        return dict(self.session.execute(select(User.id, User.username)).all())
