"""Bounded upload and media validation helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image


async def read_limited(file: UploadFile, limit: int, chunk_size: int = 1024 * 1024) -> bytes:
    """Read an upload in bounded chunks and reject it without buffering past the limit."""

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(min(chunk_size, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise ValueError(f"Upload exceeds the {limit // (1024 * 1024)} MB limit")
    return b"".join(chunks)


def validate_image_bytes(raw: bytes, max_pixels: int = 45_000_000) -> str:
    """Validate an image by decoding its signature, not just its filename."""

    with Image.open(BytesIO(raw)) as image:
        if image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Unsupported image format")
        if image.width * image.height > max_pixels:
            raise ValueError("Image dimensions are too large")
        extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[image.format]
        image.verify()
    return extension


def extension_for(kind: str, filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    allowed = {
        "image": {".png", ".jpg", ".jpeg", ".webp"},
        "video": {".mp4", ".webm", ".gif"},
        "audio": {".wav", ".mp3", ".flac"},
    }[kind]
    if suffix not in allowed:
        raise ValueError(f"Unsupported {kind} file; accepted: {', '.join(sorted(allowed))}")
    return suffix


def validate_media_signature(raw: bytes, kind: str, *, strict: bool = False) -> None:
    """Validate cheap container signatures when strict media mode is enabled.

    Video/audio decoding is intentionally not forced for the default local test
    mode (it would make tiny fixture uploads impossible), but cloud workers can
    set ``STUDIO_STRICT_MEDIA=1`` to reject renamed or malformed files before
    they enter the asset vault.
    """

    if not strict:
        return
    signatures = {
        "video": (
            (b"GIF87a", b"GIF89a"),
            (b"\x1a\x45\xdf\xa3",),  # WebM/Matroska EBML
            (b"RIFF",),  # AVI/WAV family; extension still constrains the type
        ),
        "audio": ((b"RIFF",), (b"fLaC",), (b"ID3",)),
    }
    if kind == "video" and raw[4:8] == b"ftyp":
        return  # ISO-BMFF/MP4
    if kind not in signatures or not any(raw.startswith(option) for group in signatures[kind] for option in group):
        raise ValueError(f"File does not have a recognised {kind} container signature")

