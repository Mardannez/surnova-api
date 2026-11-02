from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_image(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("El tamaño máximo es 5 MB.")
    if Path(upload.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValidationError("Solo se permiten JPEG, PNG y WebP.")
    try:
        upload.open("rb")
        img = Image.open(upload)
        if img.format not in {"JPEG", "PNG", "WEBP"} or img.width * img.height > 20_000_000:
            raise ValidationError("Formato o dimensiones de imagen inválidos.")
        img.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("Imagen inválida.") from exc
    finally:
        upload.seek(0)
