from models import Meeting
from repositories.base import Repository


class MeetingRepository(Repository[Meeting]):
    def __init__(self, session):
        super().__init__(session, Meeting)
