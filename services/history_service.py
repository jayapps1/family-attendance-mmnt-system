from pathlib import Path
from models import FamilyHistory, HistoryMedia, MediaType
from repositories.history_repository import HistoryRepository
from services.base import Service, snapshot
from utils.file_manager import FileManager
from utils.validators import required, ValidationError


class HistoryService(Service):
    def __init__(self, sessions, actor_id, media_root):
        super().__init__(sessions, actor_id)
        self.files = FileManager(media_root)

    def list(self):
        with self.transaction() as session:
            return [snapshot(row) for row in HistoryRepository(session).list()]

    def save(self, title, content, summary=None, historical_period=None, author=None, identity=None):
        with self.transaction() as session:
            repo = HistoryRepository(session)
            row = repo.get(identity, lock=True) if identity else FamilyHistory(created_by=self.actor_id)
            row.title, row.content = required(title, "Title"), required(content, "Content", 1000000)
            row.summary, row.historical_period, row.author = summary, historical_period, author
            repo.add(row)
            self.audit(session, "HISTORY_ACTION", row, "Saved history")
            return snapshot(row)

    def media(self, history_id):
        with self.transaction() as session:
            return [snapshot(row) for row in HistoryRepository(session).media.list(
                HistoryMedia.family_history_id == history_id)]

    def upload(self, history_id, source, title, media_type, description=None):
        kind = MediaType(media_type)
        extensions = {MediaType.IMAGE: {".jpg", ".jpeg", ".png", ".gif", ".webp"},
                      MediaType.VIDEO: {".mp4", ".mov"}, MediaType.AUDIO: {".mp3", ".wav"},
                      MediaType.DOCUMENT: {".pdf", ".txt", ".docx"}}
        if Path(source).suffix.lower() not in extensions[kind]:
            raise ValidationError("File extension does not match the selected media type")
        relative = None
        try:
            with self.transaction() as session:
                repo = HistoryRepository(session)
                repo.get(history_id)
                relative = self.files.import_file(Path(source), "history")
                row = repo.media.add(HistoryMedia(
                    family_history_id=history_id, file_path=relative, title=required(title, "Title"),
                    media_type=kind, description=description, uploaded_by=self.actor_id))
                self.audit(session, "HISTORY_ACTION", row, "Uploaded media")
                return snapshot(row)
        except Exception:
            if relative:
                self.files.discard_import(relative)
            raise
