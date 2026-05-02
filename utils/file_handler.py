from __future__ import annotations

# Mapping of MIME type → canonical file extension
SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

_MAGIC_SIGNATURES: list[tuple[bytes, int, str]] = [
    # (magic_bytes, offset, mime_type)
    (b"%PDF",               0, "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", 0, "image/png"),
    (b"\xff\xd8\xff",      0, "image/jpeg"),
    (b"II\x2a\x00",        0, "image/tiff"),
    (b"MM\x00\x2a",        0, "image/tiff"),
    (b"PK\x03\x04",        0, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
]

_HEADER_WINDOW = 16


def detect_mime_type(data: bytes) -> str:
    """Detect MIME type from file magic bytes — ignores filename/extension entirely."""
    header = data[:_HEADER_WINDOW]
    for magic, offset, mime in _MAGIC_SIGNATURES:
        if header[offset: offset + len(magic)] == magic:
            return mime
    return "application/octet-stream"


def is_supported(mime_type: str) -> bool:
    """Return True if this MIME type is in the platform's supported set."""
    return mime_type in SUPPORTED_MIME_TYPES


def extension_for(mime_type: str) -> str:
    """Return the canonical file extension for a supported MIME type."""
    return SUPPORTED_MIME_TYPES.get(mime_type, ".bin")


def human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes //= 1024
    return f"{num_bytes:.1f} TB"
