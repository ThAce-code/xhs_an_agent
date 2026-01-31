from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Primary LLM
    gemini_model: str = "gemini-2.5-flash"
    # Optional: use a Gemini-compatible proxy base URL (v1beta/models).
    # Example: https://api.ikuncode.cc/v1beta/models
    gemini_base_url: str | None = None
    # Optional: API key for Gemini proxy (falls back to GOOGLE_API_KEY if unset).
    gemini_api_key: str | None = None

    # Fallback LLM (MiniMax)
    minimax_model: str = "MiniMax-M2.1"
    # Official docs: https://platform.minimaxi.com/docs/api-reference/text-chat
    minimax_base_url: str = "https://api.minimaxi.com/v1/text/chatcompletion_v2"

    # General
    max_results: int = 5
    out_dir: str = "outputs"

    # Temperatures (per module)
    analysis_temperature: float = 0.0
    rewrite_temperature: float = 0.7
    cover_temperature: float = 0.6

    # Prompt style
    style_preset: str = "balanced"  # balanced | xhs

    # Validation (auto-repair retries on invalid JSON/citations)
    validate_retries: int = 1

    # Optional: cover image generation (Stage 3.2)
    cover_image_provider: str = "minimax"  # minimax | google
    cover_image_model: str = "image-01"
    cover_image_aspect: str = "3:4"
    minimax_image_base_url: str = "https://api.minimaxi.com/v1/image_generation"

    # Search shaping
    days: int | None = None
    lang: str | None = None
    region: str | None = None

    # Retrieval quality (Stage 2)
    max_queries: int = 6
    max_sources: int = 10


def _get_int(name: str) -> int | None:
    v = os.getenv(name)
    if v is None or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None


def load_settings() -> Settings:
    """Load settings from env.

    Uses pydantic-settings when available (for typed parsing), otherwise falls
    back to plain `os.environ`.

    Env vars (recommended):
    - `XHS_GEMINI_MODEL`
    - `XHS_GEMINI_BASE_URL` (optional Gemini-compatible proxy)
    - `XHS_GEMINI_API_KEY` (optional proxy key; defaults to GOOGLE_API_KEY)
    - `XHS_MINIMAX_MODEL`, `XHS_MINIMAX_BASE_URL`
    - `XHS_MAX_RESULTS`, `XHS_OUT_DIR`
    - `XHS_DAYS`, `XHS_LANG`, `XHS_REGION`
    - `XHS_MAX_QUERIES`, `XHS_MAX_SOURCES`
    - `XHS_ANALYSIS_TEMPERATURE`, `XHS_REWRITE_TEMPERATURE`, `XHS_COVER_TEMPERATURE`
    - `XHS_COVER_IMAGE_PROVIDER`, `XHS_COVER_IMAGE_MODEL`, `XHS_COVER_IMAGE_ASPECT`
    - `XHS_MINIMAX_IMAGE_BASE_URL`
    """

    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

        class _PydanticSettings(BaseSettings):  # type: ignore
            gemini_model: str = Settings.gemini_model
            gemini_base_url: str | None = None
            gemini_api_key: str | None = None
            minimax_model: str = Settings.minimax_model
            minimax_base_url: str = Settings.minimax_base_url
            max_results: int = Settings.max_results
            out_dir: str = Settings.out_dir
            analysis_temperature: float = Settings.analysis_temperature
            rewrite_temperature: float = Settings.rewrite_temperature
            cover_temperature: float = Settings.cover_temperature
            style_preset: str = Settings.style_preset
            validate_retries: int = Settings.validate_retries
            cover_image_provider: str = Settings.cover_image_provider
            cover_image_model: str = Settings.cover_image_model
            cover_image_aspect: str = Settings.cover_image_aspect
            minimax_image_base_url: str = Settings.minimax_image_base_url
            days: int | None = None
            lang: str | None = None
            region: str | None = None
            max_queries: int = Settings.max_queries
            max_sources: int = Settings.max_sources

            model_config = SettingsConfigDict(env_prefix="XHS_", extra="ignore")

        s = _PydanticSettings()
        return Settings(
            gemini_model=s.gemini_model,
            gemini_base_url=s.gemini_base_url,
            gemini_api_key=s.gemini_api_key,
            minimax_model=s.minimax_model,
            minimax_base_url=s.minimax_base_url,
            max_results=s.max_results,
            out_dir=s.out_dir,
            analysis_temperature=s.analysis_temperature,
            rewrite_temperature=s.rewrite_temperature,
            cover_temperature=s.cover_temperature,
            style_preset=s.style_preset,
            validate_retries=s.validate_retries,
            cover_image_provider=s.cover_image_provider,
            cover_image_model=s.cover_image_model,
            cover_image_aspect=s.cover_image_aspect,
            minimax_image_base_url=s.minimax_image_base_url,
            days=s.days,
            lang=s.lang,
            region=s.region,
            max_queries=s.max_queries,
            max_sources=s.max_sources,
        )
    except Exception:
        return Settings(
            gemini_model=os.getenv("XHS_GEMINI_MODEL", Settings.gemini_model),
            gemini_base_url=os.getenv("XHS_GEMINI_BASE_URL") or None,
            gemini_api_key=os.getenv("XHS_GEMINI_API_KEY") or None,
            minimax_model=os.getenv("XHS_MINIMAX_MODEL", Settings.minimax_model),
            minimax_base_url=os.getenv("XHS_MINIMAX_BASE_URL", Settings.minimax_base_url),
            max_results=int(os.getenv("XHS_MAX_RESULTS", str(Settings.max_results))),
            out_dir=os.getenv("XHS_OUT_DIR", Settings.out_dir),
            analysis_temperature=float(os.getenv("XHS_ANALYSIS_TEMPERATURE", str(Settings.analysis_temperature))),
            rewrite_temperature=float(os.getenv("XHS_REWRITE_TEMPERATURE", str(Settings.rewrite_temperature))),
            cover_temperature=float(os.getenv("XHS_COVER_TEMPERATURE", str(Settings.cover_temperature))),
            style_preset=os.getenv("XHS_STYLE_PRESET", Settings.style_preset),
            validate_retries=int(os.getenv("XHS_VALIDATE_RETRIES", str(Settings.validate_retries))),
            cover_image_provider=os.getenv("XHS_COVER_IMAGE_PROVIDER", Settings.cover_image_provider),
            cover_image_model=os.getenv("XHS_COVER_IMAGE_MODEL", Settings.cover_image_model),
            cover_image_aspect=os.getenv("XHS_COVER_IMAGE_ASPECT", Settings.cover_image_aspect),
            minimax_image_base_url=os.getenv("XHS_MINIMAX_IMAGE_BASE_URL", Settings.minimax_image_base_url),
            days=_get_int("XHS_DAYS"),
            lang=os.getenv("XHS_LANG") or None,
            region=os.getenv("XHS_REGION") or None,
            max_queries=int(os.getenv("XHS_MAX_QUERIES", str(Settings.max_queries))),
            max_sources=int(os.getenv("XHS_MAX_SOURCES", str(Settings.max_sources))),
        )


