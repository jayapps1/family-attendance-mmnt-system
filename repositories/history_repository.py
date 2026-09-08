from models import FamilyHistory, HistoryMedia
from repositories.base import Repository


class HistoryRepository(Repository[FamilyHistory]):
    def __init__(self, session):
        super().__init__(session, FamilyHistory)
        self.media = Repository(session, HistoryMedia)
