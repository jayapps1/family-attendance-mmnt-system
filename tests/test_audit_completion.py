"""Regression coverage for audit fixes that change protected records."""
import uuid
import pytest
from sqlalchemy import select
from models import User, GalleryAlbum
from services.admin_service import AdminService
from services.gallery_service import GalleryService
from tests.service_helpers import service_context
from utils.validators import ValidationError


def test_admin_contact_update_preserves_auth_and_rejects_duplicates(db):
    context = service_context(db)
    service = AdminService(*context)
    actor = db.get(User, context[1])
    original = (actor.role, actor.totp_enabled, actor.totp_secret_encrypted)
    name = "edited_" + uuid.uuid4().hex
    service.update_profile(actor.id, name, name + "@example.test", "0540000000")
    db.refresh(actor)
    assert actor.username == name
    assert actor.email == name + "@example.test"
    assert (actor.role, actor.totp_enabled, actor.totp_secret_encrypted) == original
    other = User(username="other_" + uuid.uuid4().hex, is_active=True)
    db.add(other)
    db.flush()
    with pytest.raises(ValidationError):
        service.update_profile(actor.id, other.username)
    db.refresh(actor)
    assert actor.username == name


def test_gallery_empty_delete_preserves_nonempty_album_and_file(db, tmp_path):
    service = GalleryService(*service_context(db), tmp_path / "media")
    empty = service.save_album("Empty audit album")
    service.delete_empty_album(empty["id"])
    assert db.scalar(select(GalleryAlbum).where(GalleryAlbum.id == empty["id"])) is None
    album = service.save_album("Preserved audit album")
    source = tmp_path / "story.txt"
    source.write_text("Family history")
    item = service.upload(album["id"], source, "Story")
    with pytest.raises(ValidationError):
        service.delete_empty_album(album["id"])
    assert service.items(album["id"])[0]["id"] == item["id"]
    assert (tmp_path / "media" / item["file_path"]).read_text() == "Family history"
