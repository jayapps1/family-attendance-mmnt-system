from models import GalleryAlbum, GalleryItem
from repositories.base import Repository


class GalleryRepository(Repository[GalleryAlbum]):
    def __init__(self, session):
        super().__init__(session, GalleryAlbum)
        self.items = Repository(session, GalleryItem)
