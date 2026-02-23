"""Serialization helpers for generated SDK models and Python types."""

from __future__ import annotations

import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any


def to_data(obj: Any) -> Any:
    """Convert SDK responses/models to JSON-serializable data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "type": "bytes",
                "encoding": "base64",
                "size": len(obj),
                "data": base64.b64encode(obj).decode("ascii"),
            }

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): to_data(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_data(v) for v in obj]

    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return to_data(obj.model_dump(by_alias=True, exclude_none=True))
        except TypeError:
            return to_data(obj.model_dump())

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return to_data(obj.to_dict())
        except Exception:
            pass

    if hasattr(obj, "data") and hasattr(obj, "status"):
        # Some generated wrappers expose a response-ish object.
        return {
            "status": getattr(obj, "status", None),
            "reason": getattr(obj, "reason", None),
            "data": to_data(getattr(obj, "data", None)),
            "headers": to_data(getattr(obj, "headers", None)),
        }

    if hasattr(obj, "__dict__"):
        return to_data(vars(obj))

    return str(obj)
