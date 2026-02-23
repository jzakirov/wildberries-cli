"""CLI argument parsing helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from wildberries_cli.output import read_text_arg


def load_json_input(body_json: str | None = None, body_file: str | None = None) -> Any:
    """Load JSON from one source (`--body-json` or `--body-file`)."""
    if body_json and body_file:
        raise ValueError("Use only one of --body-json or --body-file")
    if body_json is None and body_file is None:
        raise ValueError("Body JSON is required")

    if body_json is not None:
        text = read_text_arg(body_json)
    else:
        if body_file == "-":
            text = read_text_arg("-")
        else:
            text = Path(str(body_file)).read_text()

    return json.loads(text)


def parse_rfc3339ish(value: str) -> datetime:
    """Parse an RFC3339-ish datetime/date string accepted by the SDK."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid datetime '{value}'. Use ISO/RFC3339 (e.g. 2024-01-01 or 2024-01-01T12:00:00+03:00).") from exc


def parse_kv_pairs(items: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        key, value = _split_kv(item)
        out[key] = value
    return out


def parse_json_kv_pairs(items: Iterable[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        key, value = _split_kv(item)
        out[key] = json.loads(value)
    return out


def _split_kv(item: str) -> tuple[str, str]:
    if "=" not in item:
        raise ValueError(f"Expected KEY=VALUE, got '{item}'")
    key, value = item.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Expected KEY=VALUE, got '{item}'")
    return key, value
