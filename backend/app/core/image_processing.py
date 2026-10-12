"""Secure image processing and validation pipeline for user wardrobe uploads.

Enforces:
- File size limits (default 10 MB)
- Magic-byte signature verification (JPEG, PNG, WebP)
- Dimension and pixel limits (decompression bomb protection)
- Metadata stripping (EXIF, GPS, camera model)
- EXIF orientation auto-rotation
- Clean re-encoding to standardized JPEG
- Automatic thumbnail generation
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps

from .exceptions import AppException

logger = logging.getLogger("flashfit.image_processing")

# Security and sizing limits
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DIMENSION = 4096                # Max width or height in pixels
MAX_TOTAL_PIXELS = 16_777_216       # 16 Megapixels
DISPLAY_MAX_DIMENSION = 1600       # Display image resized bounds
THUMBNAIL_MAX_DIMENSION = 320      # Thumbnail bounds
JPEG_DISPLAY_QUALITY = 85
JPEG_THUMB_QUALITY = 80

# Limit Pillow's max pixel allocation to protect against decompression bombs
Image.MAX_IMAGE_PIXELS = 20_000_000


@dataclass
class ProcessedImage:
    display_bytes: bytes
    thumbnail_bytes: bytes
    width: int
    height: int
    byte_size: int
    format: str = "JPEG"
    mime_type: str = "image/jpeg"

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "byte_size": self.byte_size,
            "display_format": self.format,
            "mime_type": self.mime_type,
            "metadata_stripped": True,
        }


def check_magic_bytes(raw: bytes) -> str:
    """Verify magic bytes signature. Returns detected canonical format or raises error."""
    if len(raw) < 12:
        raise AppException(
            message="Uploaded file is too small to be a valid image.",
            code="IMAGE_TOO_SMALL",
            status_code=400,
        )

    # JPEG signature: 0xFF, 0xD8, 0xFF
    if raw[:3] == b"\xff\xd8\xff":
        return "JPEG"

    # PNG signature: 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"

    # WebP signature: RIFF....WEBP
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "WEBP"

    raise AppException(
        message="Invalid image signature. Only JPEG, PNG, and WebP images are allowed.",
        code="INVALID_IMAGE_SIGNATURE",
        status_code=400,
    )


def sanitize_and_process_image(raw_bytes: bytes) -> ProcessedImage:
    """Validate, strip metadata, re-encode, and generate thumbnail for an uploaded image.

    Raises AppException for any security or format violation.
    """
    byte_size = len(raw_bytes)
    if byte_size > MAX_FILE_BYTES:
        raise AppException(
            message=f"Image size ({byte_size / (1024 * 1024):.1f} MB) exceeds maximum limit of 10 MB.",
            code="FILE_TOO_LARGE",
            status_code=400,
        )

    # 1. Signature check
    check_magic_bytes(raw_bytes)

    # 2. Open and verify header
    try:
        verify_img = Image.open(io.BytesIO(raw_bytes))
        verify_img.verify()
    except Exception as exc:
        logger.warning(f"Image header verification failed: {exc}")
        raise AppException(
            message="Corrupted or malformed image data.",
            code="CORRUPTED_IMAGE",
            status_code=400,
        )

    # 3. Re-open for actual processing (as required after .verify())
    try:
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise AppException(
            message="Unable to decode image payload.",
            code="IMAGE_DECODE_ERROR",
            status_code=400,
        )

    orig_w, orig_h = img.size
    if orig_w > MAX_DIMENSION or orig_h > MAX_DIMENSION or (orig_w * orig_h) > MAX_TOTAL_PIXELS:
        raise AppException(
            message=f"Image dimensions ({orig_w}x{orig_h}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION} limit.",
            code="DIMENSIONS_TOO_LARGE",
            status_code=400,
        )

    # 4. Handle EXIF orientation rotation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # 5. Convert to RGB to strip alpha and standardize colorspace
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    # 6. Re-scale display version if larger than bounds (strips all EXIF/metadata in memory)
    display_img = img.copy()
    if display_img.width > DISPLAY_MAX_DIMENSION or display_img.height > DISPLAY_MAX_DIMENSION:
        display_img.thumbnail(
            (DISPLAY_MAX_DIMENSION, DISPLAY_MAX_DIMENSION),
            Image.Resampling.LANCZOS,
        )

    display_buf = io.BytesIO()
    # Saving without exif or info parameter strips all metadata completely
    display_img.save(
        display_buf,
        format="JPEG",
        quality=JPEG_DISPLAY_QUALITY,
        optimize=True,
    )
    display_bytes = display_buf.getvalue()

    # 7. Generate thumbnail
    thumb_img = display_img.copy()
    thumb_img.thumbnail(
        (THUMBNAIL_MAX_DIMENSION, THUMBNAIL_MAX_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    thumb_buf = io.BytesIO()
    thumb_img.save(
        thumb_buf,
        format="JPEG",
        quality=JPEG_THUMB_QUALITY,
        optimize=True,
    )
    thumb_bytes = thumb_buf.getvalue()

    return ProcessedImage(
        display_bytes=display_bytes,
        thumbnail_bytes=thumb_bytes,
        width=display_img.width,
        height=display_img.height,
        byte_size=len(display_bytes),
        format="JPEG",
        mime_type="image/jpeg",
    )
