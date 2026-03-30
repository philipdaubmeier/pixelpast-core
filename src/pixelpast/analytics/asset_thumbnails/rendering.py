"""Fixed WebP thumbnail rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

THUMBNAIL_RENDITIONS = ("h120", "h240", "q200")
_MAX_WIDE_ASPECT_RATIO = 3.0
_WEBP_SAVE_OPTIONS = {
    "format": "WEBP",
    "quality": 80,
    "method": 6,
}


class ThumbnailRenderError(RuntimeError):
    """Raised when a thumbnail source cannot be rendered."""


@dataclass(slots=True, frozen=True)
class ThumbnailOutput:
    """Describes one deterministic thumbnail output location."""

    rendition: str
    path: Path


def build_thumbnail_output_path(
    *,
    thumb_root: Path,
    rendition: str,
    short_id: str,
) -> Path:
    """Return the deterministic WebP output path for one rendition."""

    return thumb_root / rendition / f"{short_id}.webp"


def render_thumbnail(
    *,
    source_path: Path,
    output_path: Path,
    rendition: str,
) -> None:
    """Render one fixed thumbnail rendition from a source image."""

    try:
        with Image.open(source_path) as image:
            normalized = ImageOps.exif_transpose(image)
            prepared = _render_rendition(image=normalized, rendition=rendition)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            prepared.save(output_path, **_WEBP_SAVE_OPTIONS)
    except FileNotFoundError as error:
        raise ThumbnailRenderError(
            f"Original file is missing: {source_path}"
        ) from error
    except UnidentifiedImageError as error:
        raise ThumbnailRenderError(
            f"Unsupported or unreadable image source: {source_path}"
        ) from error
    except OSError as error:
        raise ThumbnailRenderError(
            f"Could not render thumbnail from source image: {source_path}"
        ) from error


def _render_rendition(*, image: Image.Image, rendition: str) -> Image.Image:
    if rendition == "h120":
        return _render_height_variant(image=image, height=120)
    if rendition == "h240":
        return _render_height_variant(image=image, height=240)
    if rendition == "q200":
        return _render_square_variant(image=image, size=200)
    raise ValueError(f"Unsupported thumbnail rendition: {rendition}.")


def _render_height_variant(*, image: Image.Image, height: int) -> Image.Image:
    prepared = _center_crop_overwide_image(image=image)
    width = max(1, round((prepared.width / prepared.height) * height))
    return prepared.convert("RGB").resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


def _render_square_variant(*, image: Image.Image, size: int) -> Image.Image:
    crop_size = min(image.width, image.height)
    left = (image.width - crop_size) / 2
    top = (image.height - crop_size) / 2
    right = left + crop_size
    bottom = top + crop_size
    cropped = image.crop((left, top, right, bottom))
    return cropped.convert("RGB").resize(
        (size, size),
        Image.Resampling.LANCZOS,
    )


def _center_crop_overwide_image(*, image: Image.Image) -> Image.Image:
    if image.height <= 0:
        raise ValueError("Image height must be positive.")

    aspect_ratio = image.width / image.height
    if aspect_ratio <= _MAX_WIDE_ASPECT_RATIO:
        return image

    target_width = image.height * _MAX_WIDE_ASPECT_RATIO
    left = (image.width - target_width) / 2
    right = left + target_width
    return image.crop((left, 0, right, image.height))


__all__ = [
    "THUMBNAIL_RENDITIONS",
    "ThumbnailOutput",
    "ThumbnailRenderError",
    "build_thumbnail_output_path",
    "render_thumbnail",
]
