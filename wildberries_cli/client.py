"""Dynamic Wildberries SDK client factory and API invocation helpers."""


import importlib
import inspect
import pkgutil
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import typer
import wildberries_sdk

from wildberries_cli.output import print_error

if TYPE_CHECKING:
    from wildberries_cli.config import Config


@dataclass
class ModuleClient:
    module_name: str
    sdk_module: Any
    api: Any


def list_sdk_modules() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(wildberries_sdk.__path__))


def list_methods(module_name: str) -> list[str]:
    cls = _get_default_api_class(normalize_module_name(module_name))
    methods = []
    for name, fn in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith("_"):
            continue
        methods.append(name)
    return sorted(methods)


def method_signature(module_name: str, method_name: str) -> str:
    cls = _get_default_api_class(normalize_module_name(module_name))
    fn = getattr(cls, method_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(f"Method '{method_name}' not found in module '{module_name}'")
    return f"{method_name}{inspect.signature(fn)}"


def get_module_client(module_name: str, cfg: "Config", *, require_token: bool = True) -> ModuleClient:
    module_name = normalize_module_name(module_name)
    if require_token:
        _require_token(cfg)

    sdk_module = importlib.import_module(f"wildberries_sdk.{module_name}")
    Configuration = getattr(sdk_module, "Configuration")
    ApiClient = getattr(sdk_module, "ApiClient")
    DefaultApi = getattr(sdk_module, "DefaultApi")

    conf_kwargs: dict[str, Any] = {}
    if cfg.api_token:
        conf_kwargs["api_key"] = {"HeaderApiKey": cfg.api_token}
    if cfg.retries is not None:
        conf_kwargs["retries"] = cfg.retries
    conf = Configuration(**conf_kwargs)
    api_client = ApiClient(conf)
    api = DefaultApi(api_client)
    return ModuleClient(module_name=module_name, sdk_module=sdk_module, api=api)


def call_api(
    module_name: str,
    method_name: str,
    cfg: "Config",
    *,
    require_token: bool = True,
    **kwargs: Any,
) -> Any:
    client = get_module_client(module_name, cfg, require_token=require_token)
    fn = getattr(client.api, method_name, None)
    if fn is None or not callable(fn):
        print_error("validation_error", f"Unknown method '{method_name}' for module '{client.module_name}'")
        raise typer.Exit(1)
    return call_with_retry(fn, cfg, **kwargs)


def call_with_retry(fn: Any, cfg: "Config", **kwargs: Any) -> Any:
    sig = inspect.signature(fn)
    if "_request_timeout" in sig.parameters and "_request_timeout" not in kwargs:
        kwargs["_request_timeout"] = cfg.timeout_seconds

    max_attempts = max(1, int(cfg.retries))
    for attempt in range(max_attempts):
        try:
            return fn(**kwargs)
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status in {429, 500, 502, 503, 504} and attempt < max_attempts - 1:
                delay = _retry_after_seconds(exc) or min(2 ** attempt, 10)
                time.sleep(delay)
                continue
            _handle_exception(exc)
            raise typer.Exit(1)


def normalize_module_name(value: str) -> str:
    return value.replace("-", "_").strip()


def _require_token(cfg: "Config") -> None:
    if not cfg.api_token:
        print_error(
            "auth_error",
            "No WB API token configured. Set WB_API_TOKEN, use --api-token, or run `wildberries config init`.",
        )
        raise typer.Exit(1)


def _get_default_api_class(module_name: str) -> Any:
    sdk_module = importlib.import_module(f"wildberries_sdk.{module_name}")
    return getattr(sdk_module, "DefaultApi")


def _retry_after_seconds(exc: Exception) -> int | None:
    headers = getattr(exc, "headers", None)
    if not headers:
        return None
    try:
        value = headers.get("Retry-After")  # type: ignore[union-attr]
        if value is None:
            return None
        return max(1, int(value))
    except Exception:
        return None


def _handle_exception(exc: Exception) -> None:
    status = getattr(exc, "status", None)
    message = str(exc)
    detail = getattr(exc, "body", None)

    if status == 401:
        print_error("auth_error", "Authentication failed. Check WB_API_TOKEN.", status_code=status, detail=detail)
        return
    if status == 403:
        print_error("forbidden", "Permission denied or token lacks required scope.", status_code=status, detail=detail)
        return
    if status == 404:
        print_error("not_found", "Resource not found.", status_code=status, detail=detail)
        return
    if status == 429:
        print_error("rate_limit", "Rate limit exceeded.", status_code=status, detail=detail)
        return
    if status is not None:
        print_error("api_error", message, status_code=status, detail=detail)
        return
    print_error("cli_error", message)
