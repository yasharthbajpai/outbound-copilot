"""Environment-driven configuration.

All values come from environment variables (optionally loaded from a `.env`
file at startup). `BEDROCK_MODEL_ID` is required and has no default — the
app fails fast if it is missing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    bedrock_model_id: str
    aws_region: str
    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    aws_session_token: Optional[str]
    max_tokens: int
    temperature: float
    http_timeout_seconds: int
    min_website_text_chars: int


def _load_dotenv_if_present() -> None:
    """Best-effort load of a local `.env` file.

    We intentionally do not fail if python-dotenv isn't installed or no
    `.env` is present — env vars set elsewhere should still work.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(override=False)
    except Exception:
        pass


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def _optional(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, "")
    value = value.strip() if value else ""
    return value or default


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a float, got {raw!r}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance read from the environment."""
    _load_dotenv_if_present()
    return Settings(
        bedrock_model_id=_require("BEDROCK_MODEL_ID"),
        aws_region=_optional("AWS_REGION", "us-east-1") or "us-east-1",
        aws_access_key_id=_optional("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_optional("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=_optional("AWS_SESSION_TOKEN"),
        max_tokens=_int("BEDROCK_MAX_TOKENS", 1500),
        temperature=_float("BEDROCK_TEMPERATURE", 0.2),
        http_timeout_seconds=_int("HTTP_TIMEOUT_SECONDS", 15),
        min_website_text_chars=_int("MIN_WEBSITE_TEXT_CHARS", 400),
    )
