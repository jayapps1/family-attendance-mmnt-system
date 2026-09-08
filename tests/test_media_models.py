import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from models import GalleryAlbum, GalleryItem, FamilyHistory, HistoryMedia, MediaType


def test_media_roundtrip_and_preservation(db):
    album = GalleryAlbum(title="Test")
    history = FamilyHistory(title="History", content="Family story")
    item = GalleryItem(album=album, title="Photo", file_path="gallery/test.jpg")
    attachment = HistoryMedia(history=history, title="Recording", media_type=MediaType.AUDIO,
                              file_path="history/test.mp3")
    db.add_all([album, history, item, attachment])
    db.flush()
    db.expire_all()
    assert album.items[0].file_path == "gallery/test.jpg"
    assert history.media[0].media_type is MediaType.AUDIO
    assert item.uploaded_at.tzinfo is not None
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.delete(album)
            db.flush()
    inspector = inspect(db.connection())
    for model in (GalleryAlbum, GalleryItem, FamilyHistory, HistoryMedia):
        assert set(model.__table__.c.keys()) == {c["name"] for c in inspector.get_columns(model.__tablename__)}
