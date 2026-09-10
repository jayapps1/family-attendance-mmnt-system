from pathlib import Path
from models import GalleryAlbum, GalleryItem
from repositories.gallery_repository import GalleryRepository
from services.base import Service, snapshot
from utils.file_manager import FileManager
from utils.validators import required


class GalleryService(Service):
    def __init__(self, sessions, actor_id, media_root):
        super().__init__(sessions, actor_id)
        self.files = FileManager(media_root)

    def albums(self):
        with self.transaction() as session:
            return [snapshot(row) for row in GalleryRepository(session).list()]

    def save_album(self, title, description=None, event_date=None, location=None, identity=None):
        with self.transaction() as session:
            repo = GalleryRepository(session)
            row = repo.get(identity, lock=True) if identity else GalleryAlbum(created_by=self.actor_id)
            row.title, row.description = required(title, "Title"), description
            row.event_date, row.location = event_date, location
            repo.add(row)
            self.audit(session, "GALLERY_ACTION", row, "Saved album")
            return snapshot(row)

    def items(self, album_id):
        with self.transaction() as session:
            return [snapshot(row) for row in GalleryRepository(session).items.list(GalleryItem.album_id == album_id)]

    def upload(self, album_id, source, title, description=None):
        relative = None
        try:
            with self.transaction() as session:
                repo = GalleryRepository(session)
                album = repo.get(album_id, lock=True)
                relative = self.files.import_file(Path(source), "gallery")
                row = repo.items.add(GalleryItem(
                    album_id=album_id, title=required(title, "Title"), description=description,
                    file_path=relative, uploaded_by=self.actor_id))
                if album.cover_image_path is None and Path(relative).suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    album.cover_image_path = relative
                self.audit(session, "GALLERY_ACTION", row, "Uploaded item")
                return snapshot(row)
        except Exception:
            if relative:
                self.files.discard_import(relative)
            raise

    def delete_empty_album(self, identity):
        from utils.validators import ValidationError
        with self.transaction() as session:
            repo = GalleryRepository(session)
            row = repo.get(identity,lock=True)
            if repo.items.list(GalleryItem.album_id == identity) or row.cover_image_path:
                raise ValidationError('This album contains media and cannot be deleted. Its files and history will be preserved.')
            self.audit(session,'DELETE_ALBUM',row,'Deleted empty album only')
            session.delete(row)
