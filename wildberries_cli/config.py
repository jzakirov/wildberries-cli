"""Configuration management for wildberries CLI."""


import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tomlkit

CONFIG_PATH = Path.home() / ".config" / "wildberries-cli" / "config.toml"


@dataclass
class Config:
    api_token: Optional[str] = None
    timeout_seconds: float = 30.0
    retries: int = 3
    locale: Optional[str] = None
    pretty: bool = False


_ENV_MAP = {
    "api_token": "WB_API_TOKEN",
    "timeout_seconds": "WB_TIMEOUT",
    "retries": "WB_RETRIES",
    "locale": "WB_LOCALE",
    "pretty": "WB_PRETTY",
}


def load_config(
    api_token_flag: Optional[str] = None,
    timeout_flag: Optional[float] = None,
    retries_flag: Optional[int] = None,
    locale_flag: Optional[str] = None,
    pretty_flag: Optional[bool] = None,
) -> Config:
    """Load config with priority: file < env < CLI flags."""
    cfg = Config()

    if CONFIG_PATH.exists():
        try:
            doc = tomlkit.parse(CONFIG_PATH.read_text())
            core = doc.get("core", {})
            defaults = doc.get("defaults", {})
            if core.get("api_token"):
                cfg.api_token = str(core["api_token"])
            if core.get("timeout_seconds") is not None:
                cfg.timeout_seconds = float(core["timeout_seconds"])
            if core.get("retries") is not None:
                cfg.retries = int(core["retries"])
            if defaults.get("locale"):
                cfg.locale = str(defaults["locale"])
            if defaults.get("pretty") is not None:
                cfg.pretty = bool(defaults["pretty"])
        except Exception as exc:
            print(f"wildberries: warning: could not parse config file {CONFIG_PATH}: {exc}", file=sys.stderr)

    if os.environ.get(_ENV_MAP["api_token"]):
        cfg.api_token = os.environ[_ENV_MAP["api_token"]]
    if os.environ.get(_ENV_MAP["timeout_seconds"]):
        try:
            cfg.timeout_seconds = float(os.environ[_ENV_MAP["timeout_seconds"]])
        except ValueError:
            pass
    if os.environ.get(_ENV_MAP["retries"]):
        try:
            cfg.retries = int(os.environ[_ENV_MAP["retries"]])
        except ValueError:
            pass
    if os.environ.get(_ENV_MAP["locale"]):
        cfg.locale = os.environ[_ENV_MAP["locale"]]
    if os.environ.get(_ENV_MAP["pretty"]):
        cfg.pretty = os.environ[_ENV_MAP["pretty"]].lower() in {"1", "true", "yes"}

    if api_token_flag is not None:
        cfg.api_token = api_token_flag
    if timeout_flag is not None:
        cfg.timeout_seconds = timeout_flag
    if retries_flag is not None:
        cfg.retries = retries_flag
    if locale_flag is not None:
        cfg.locale = locale_flag
    if pretty_flag is not None:
        cfg.pretty = pretty_flag

    if cfg.timeout_seconds <= 0:
        cfg.timeout_seconds = 30.0
    if cfg.retries < 1:
        cfg.retries = 1

    return cfg


def save_config(cfg: Config) -> None:
    """Persist a full Config object to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        doc = tomlkit.parse(CONFIG_PATH.read_text())
    else:
        doc = tomlkit.document()

    if "core" not in doc:
        doc["core"] = tomlkit.table()
    if "defaults" not in doc:
        doc["defaults"] = tomlkit.table()

    if cfg.api_token:
        doc["core"]["api_token"] = cfg.api_token
    elif "api_token" in doc["core"]:
        del doc["core"]["api_token"]

    doc["core"]["timeout_seconds"] = float(cfg.timeout_seconds)
    doc["core"]["retries"] = int(cfg.retries)

    if cfg.locale:
        doc["defaults"]["locale"] = cfg.locale
    elif "locale" in doc["defaults"]:
        del doc["defaults"]["locale"]

    if cfg.pretty:
        doc["defaults"]["pretty"] = True
    elif "pretty" in doc["defaults"]:
        del doc["defaults"]["pretty"]

    CONFIG_PATH.write_text(tomlkit.dumps(doc))


def save_config_key(dotted_key: str, value: str) -> None:
    """Write a dotted config key (e.g. core.retries) to the config file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        doc = tomlkit.parse(CONFIG_PATH.read_text())
    else:
        doc = tomlkit.document()

    parts = dotted_key.split(".", 1)
    if len(parts) == 2:
        section, key = parts
        if section not in doc:
            doc[section] = tomlkit.table()
        doc[section][key] = _coerce_scalar(value)
    else:
        doc[dotted_key] = _coerce_scalar(value)

    CONFIG_PATH.write_text(tomlkit.dumps(doc))


def config_as_dict(cfg: Config, reveal: bool = False) -> dict[str, Any]:
    token = cfg.api_token
    if token and not reveal:
        visible = token[:8] if len(token) >= 8 else token
        token = f"{visible}...{'*' * 8}"

    return {
        "core": {
            "api_token": token,
            "timeout_seconds": cfg.timeout_seconds,
            "retries": cfg.retries,
        },
        "defaults": {"locale": cfg.locale, "pretty": cfg.pretty},
    }


def _coerce_scalar(value: str) -> Any:
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
