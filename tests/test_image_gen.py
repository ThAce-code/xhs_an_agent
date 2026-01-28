from __future__ import annotations

import base64

from src.image_gen import (
    decode_inline_data,
    guess_extension_from_bytes,
    mime_to_extension,
)


def test_mime_to_extension_defaults_to_png() -> None:
    assert mime_to_extension("") == ".png"
    assert mime_to_extension("application/octet-stream") == ".png"


def test_mime_to_extension_known_types() -> None:
    assert mime_to_extension("image/png") == ".png"
    assert mime_to_extension("image/jpeg") == ".jpg"
    assert mime_to_extension("image/webp") == ".webp"


def test_decode_inline_data_base64() -> None:
    raw = b"hello"
    s = base64.b64encode(raw).decode("ascii")
    assert decode_inline_data(s) == raw


def test_decode_inline_data_bytes() -> None:
    assert decode_inline_data(b"\x00\x01") == b"\x00\x01"


def test_guess_extension_from_bytes() -> None:
    assert guess_extension_from_bytes(b"\x89PNG\r\n\x1a\nxxxx") == ".png"
    assert guess_extension_from_bytes(b"\xff\xd8\xffxxxx") == ".jpg"
    assert guess_extension_from_bytes(b"RIFFxxxxWEBPxxxx") == ".webp"
