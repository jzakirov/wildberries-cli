"""raw subcommand for direct SDK method access."""

from __future__ import annotations

import json

import typer

from wildberries_cli.args import parse_json_kv_pairs, parse_kv_pairs
from wildberries_cli.client import call_api, list_methods, list_sdk_modules, method_signature, normalize_module_name
from wildberries_cli.config import Config
from wildberries_cli.output import emit, print_error
from wildberries_cli.serialize import to_data

app = typer.Typer(name="raw", help="Direct SDK access for unsupported endpoints.", no_args_is_help=True)


@app.command("modules")
def raw_modules() -> None:
    emit(list_sdk_modules())


@app.command("methods")
def raw_methods(module: str = typer.Argument(..., help="SDK module (e.g. reports, orders_fbs)")) -> None:
    try:
        emit(list_methods(normalize_module_name(module)))
    except Exception as exc:
        print_error("validation_error", f"Could not list methods for module '{module}': {exc}")
        raise typer.Exit(1)


@app.command("signature")
def raw_signature(
    module: str = typer.Argument(..., help="SDK module"),
    method: str = typer.Argument(..., help="DefaultApi method name"),
) -> None:
    try:
        emit({"module": normalize_module_name(module), "signature": method_signature(module, method)})
    except Exception as exc:
        print_error("validation_error", f"Could not inspect method signature: {exc}")
        raise typer.Exit(1)


@app.command("call")
def raw_call(
    ctx: typer.Context,
    module: str = typer.Argument(..., help="SDK module (e.g. reports, products, orders_fbs)"),
    method: str = typer.Argument(..., help="DefaultApi method name"),
    arg: list[str] = typer.Option([], "--arg", help="String kwarg in KEY=VALUE form (repeatable)"),
    arg_json: list[str] = typer.Option([], "--arg-json", help="JSON kwarg in KEY=<json> form (repeatable)"),
    kwargs_json: str | None = typer.Option(None, "--kwargs-json", help="JSON object with kwargs or '-' for stdin"),
) -> None:
    cfg: Config = ctx.obj
    try:
        kwargs: dict = {}
        if kwargs_json is not None:
            raw_text = kwargs_json
            if raw_text == "-":
                raw_text = typer.get_text_stream("stdin").read()
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("--kwargs-json must be a JSON object")
            kwargs.update(parsed)
        kwargs.update(parse_json_kv_pairs(arg_json))
        kwargs.update(parse_kv_pairs(arg))
    except Exception as exc:
        print_error("validation_error", f"Invalid raw call arguments: {exc}")
        raise typer.Exit(1)

    data = to_data(call_api(normalize_module_name(module), method, cfg, **kwargs))
    emit(data, pretty=cfg.pretty)
