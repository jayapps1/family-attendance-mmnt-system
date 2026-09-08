"""User-controlled portrait processing; originals are never overwritten."""
from dataclasses import dataclass
from io import BytesIO
from PIL import Image, ImageOps
from utils.validators import ValidationError


@dataclass(frozen=True)
class PreparedPhoto:
    data: bytes
    size: int


def load_portrait(path):
    try:
        with Image.open(path) as source:
            if source.width * source.height > 30_000_000:
                raise ValidationError("Choose an image smaller than 30 megapixels.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            return image
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("Choose a readable JPG, PNG, WebP or GIF image.") from exc


def crop_portrait(image, *, size=512, zoom=1.0, horizontal=0.5, vertical=0.5):
    size = int(size)
    if size not in (256, 512, 1024):
        raise ValidationError("Choose a portrait size of 256, 512 or 1024 pixels.")
    if not 1 <= zoom <= 3 or not 0 <= horizontal <= 1 or not 0 <= vertical <= 1:
        raise ValidationError("Invalid portrait crop.")
    side = min(image.size) / zoom
    left, top = (image.width - side) * horizontal, (image.height - side) * vertical
    return image.resize((size, size), Image.Resampling.LANCZOS, box=(left, top, left+side, top+side))


def prepare_portrait(image, **settings):
    photo = crop_portrait(image, **settings)
    buffer = BytesIO()
    photo.save(buffer, format="JPEG", quality=90, optimize=True)
    return PreparedPhoto(buffer.getvalue(), photo.width)
