from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedImage:
    path: Path
    mime_type: str
    model: str


def mime_to_extension(mime_type: str) -> str:
    mt = (mime_type or "").lower().strip()
    if mt == "image/jpeg" or mt == "image/jpg":
        return ".jpg"
    if mt == "image/webp":
        return ".webp"
    if mt == "image/png":
        return ".png"
    return ".png"


def guess_extension_from_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return ".webp"
    return ".png"


def extension_to_mime(ext: str) -> str:
    e = (ext or "").lower()
    if e == ".jpg" or e == ".jpeg":
        return "image/jpeg"
    if e == ".webp":
        return "image/webp"
    return "image/png"


def decode_inline_data(data: Any) -> bytes | None:
    if data is None:
        return None
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        s = data.strip()
        if not s:
            return None
        # Support data URLs: data:image/png;base64,....
        if s.lower().startswith("data:") and "base64," in s.lower():
            s = s.split(",", 1)[-1].strip()
        try:
            return base64.b64decode(s)
        except Exception:
            return None
    return None


def _extract_image_from_parts(parts: list[Any]) -> tuple[bytes | None, str]:
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None and isinstance(part, dict):
            inline = part.get("inline_data")
        if inline is None:
            continue

        mime_type = getattr(inline, "mime_type", None)
        data = getattr(inline, "data", None)
        if isinstance(inline, dict):
            mime_type = inline.get("mime_type") or inline.get("mimeType")
            data = inline.get("data")

        b = decode_inline_data(data)
        if b:
            return b, str(mime_type or "image/png")
    return None, ""


def _extract_image_from_interaction(interaction: Any) -> tuple[bytes | None, str]:
    outputs = getattr(interaction, "outputs", None)
    if not isinstance(outputs, list):
        return None, ""

    for out in outputs:
        out_type = getattr(out, "type", None)
        if isinstance(out, dict):
            out_type = out.get("type")
        if str(out_type or "").lower() != "image":
            continue

        mime_type = getattr(out, "mime_type", None)
        data = getattr(out, "data", None)
        if isinstance(out, dict):
            mime_type = out.get("mime_type") or out.get("mimeType")
            data = out.get("data")

        b = decode_inline_data(data)
        if b:
            return b, str(mime_type or "image/png")
    return None, ""


def generate_cover_image_google(
    *,
    prompt: str,
    out_path: Path,
    model: str = "gemini-2.5-flash-image",
    aspect_ratio: str = "3:4",
    api_key: str | None = None,
) -> GeneratedImage:
    """Best-effort cover image generation via Google GenAI.

    Soft-contract:
    - Returns `GeneratedImage` on success.
    - Raises on failure (caller should catch and keep the pipeline running).
    """

    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    key = (api_key or "").strip() or None
    if key is None:
        raise RuntimeError("Missing GOOGLE_API_KEY (required for --cover-image)")

    client = genai.Client(api_key=key)

    config_kwargs: dict[str, Any] = {"response_modalities": ["IMAGE"]}
    try:
        config_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)
    except Exception:
        logger.info("ImageConfig(aspect_ratio=%s) not supported; continuing without aspect ratio", aspect_ratio)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        parts = getattr(response, "parts", None)
        if isinstance(parts, list):
            image_bytes, mime_type = _extract_image_from_parts(parts)
            if image_bytes:
                out_path.write_bytes(image_bytes)
                return GeneratedImage(path=out_path, mime_type=mime_type or "image/png", model=model)
    except Exception as e:
        logger.warning("generate_content image failed: %s", e)

    # Fallback path for older preview endpoints that expose images via interactions API.
    try:
        interaction = client.interactions.create(
            model=model,
            input=prompt,
            response_modalities=["IMAGE"],
        )
        image_bytes, mime_type = _extract_image_from_interaction(interaction)
        if image_bytes:
            out_path.write_bytes(image_bytes)
            return GeneratedImage(path=out_path, mime_type=mime_type or "image/png", model=model)
    except Exception as e:
        logger.warning("interactions.create image failed: %s", e)

    raise RuntimeError(f"No image generated (model={model})")


def _minimax_extract_base64(resp: dict[str, Any]) -> str | None:
    data = resp.get("data")
    if isinstance(data, dict):
        b64_list = data.get("image_base64")
        if isinstance(b64_list, list) and b64_list:
            b = b64_list[0]
            if isinstance(b, str) and b.strip():
                return b.strip()

        items = data.get("items")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                b = first.get("base64") or first.get("b64_json") or first.get("b64") or first.get("image_base64")
                if isinstance(b, str) and b.strip():
                    return b.strip()

    # OpenAI-like image endpoint variants
    data2 = resp.get("data")
    if isinstance(data2, list) and data2:
        first = data2[0]
        if isinstance(first, dict):
            b = first.get("b64_json") or first.get("base64")
            if isinstance(b, str) and b.strip():
                return b.strip()

    return None


def _minimax_extract_url(resp: dict[str, Any]) -> str | None:
    data = resp.get("data")
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                u = first.get("url")
                if isinstance(u, str) and u.strip():
                    return u.strip()

        urls = data.get("image_urls")
        if isinstance(urls, list) and urls:
            u = urls[0]
            if isinstance(u, str) and u.strip():
                return u.strip()
        if isinstance(data.get("image_urls".upper()), list) and data.get("image_urls".upper()):
            u = data.get("image_urls".upper())[0]
            if isinstance(u, str) and u.strip():
                return u.strip()

    data2 = resp.get("data")
    if isinstance(data2, list) and data2:
        first = data2[0]
        if isinstance(first, dict):
            u = first.get("url")
            if isinstance(u, str) and u.strip():
                return u.strip()
    return None


def generate_cover_image_minimax(
    *,
    prompt: str,
    out_path: Path,
    model: str = "image-01",
    base_url: str = "https://api.minimaxi.com/v1/image_generation",
    aspect_ratio: str = "3:4",
    api_key: str | None = None,
    response_format: str = "base64",
    n: int = 1,
    prompt_optimizer: bool = False,
    debug_json_path: Path | None = None,
) -> GeneratedImage:
    """Generate a cover image using MiniMax image model (e.g., image-01).

    Docs: POST /v1/image_generation
    - model: image-01
    - response_format: base64 | url
    """

    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if not key:
        raise RuntimeError("Missing MINIMAX_API_KEY (required for --cover-image-provider minimax)")

    url = (base_url or "").strip()
    if not url:
        raise RuntimeError("Missing MINIMAX_IMAGE_BASE_URL")

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": response_format,
        "n": int(n),
        "prompt_optimizer": bool(prompt_optimizer),
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiniMax image HTTP {e.code}: {detail}") from e

    j = json.loads(body)
    if debug_json_path is not None:
        try:
            debug_json_path.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.info("failed to write debug json to %s", str(debug_json_path))

    # Some MiniMax endpoints return 200 OK but with an error status inside the payload.
    if isinstance(j.get("error"), dict):
        raise RuntimeError(f"MiniMax image error={j.get('error')}")

    base_resp = j.get("base_resp")
    if isinstance(base_resp, dict):
        status_code = base_resp.get("status_code")
        status_msg = base_resp.get("status_msg")
        try:
            code_int = int(status_code)
        except Exception:
            code_int = None
        if code_int not in (None, 0):
            raise RuntimeError(f"MiniMax image status_code={status_code} msg={status_msg}")

    top_code = j.get("code")
    if top_code is not None:
        if str(top_code) not in {"0", "200", "OK"}:
            raise RuntimeError(f"MiniMax image code={top_code} msg={j.get('msg')}")

    b64 = _minimax_extract_base64(j)
    if b64:
        img_bytes = decode_inline_data(b64) or b""
        if not img_bytes:
            raise RuntimeError("MiniMax image base64 decode failed")
        ext = guess_extension_from_bytes(img_bytes)
        path = out_path
        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        path.write_bytes(img_bytes)
        return GeneratedImage(path=path, mime_type=extension_to_mime(ext), model=model)

    image_url = _minimax_extract_url(j)
    if image_url:
        try:
            with urllib.request.urlopen(image_url, timeout=60.0) as resp:
                img_bytes = resp.read()
        except Exception as e:
            raise RuntimeError(f"MiniMax returned URL but download failed: {e}") from e
        ext = guess_extension_from_bytes(img_bytes)
        path = out_path
        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        path.write_bytes(img_bytes)
        return GeneratedImage(path=path, mime_type=extension_to_mime(ext), model=model)

    # Improve error message with some context.
    meta = j.get("metadata")
    base_resp = j.get("base_resp")
    raise RuntimeError(f"MiniMax image response has no base64/url items (metadata={meta}, base_resp={base_resp})")
