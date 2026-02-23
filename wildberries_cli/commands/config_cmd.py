"""config subcommand: show / set / init."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.prompt import Prompt

from wildberries_cli.client import call_api
from wildberries_cli.config import Config, CONFIG_PATH, config_as_dict, load_config, save_config, save_config_key
from wildberries_cli.output import print_error, print_json
from wildberries_cli.serialize import to_data

app = typer.Typer(name="config", help="Manage wb CLI configuration.", no_args_is_help=True)
console = Console()


@app.command("show")
def config_show(
    ctx: typer.Context,
    reveal: bool = typer.Option(False, "--reveal", help="Show full API token."),
) -> None:
    cfg: Config = ctx.obj
    print_json(config_as_dict(cfg, reveal=reveal))


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dotted config key, e.g. core.retries"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    try:
        save_config_key(key, value)
        print_json({"ok": True, "key": key, "value": value})
    except Exception as exc:
        print_error("config_error", f"Failed to write config: {exc}")
        raise typer.Exit(1)


@app.command("init")
def config_init(ctx: typer.Context) -> None:
    if not sys.stdin.isatty():
        print_error("validation_error", "`wb config init` requires an interactive terminal.")
        raise typer.Exit(1)

    cfg: Config = ctx.obj
    console.print("[bold]wb setup wizard[/bold]")
    console.print(f"Config will be saved to: [dim]{CONFIG_PATH}[/dim]\n")

    api_token = Prompt.ask("WB API token", password=True, default=cfg.api_token or "")
    timeout_text = Prompt.ask("Request timeout (seconds)", default=str(cfg.timeout_seconds))
    retries_text = Prompt.ask("Retry attempts", default=str(cfg.retries))
    locale_text = Prompt.ask("Default locale (ru/en/zh, optional)", default=cfg.locale or "")

    if not api_token:
        print_error("validation_error", "WB API token is required.")
        raise typer.Exit(1)

    try:
        timeout_seconds = float(timeout_text)
        retries = int(retries_text)
    except ValueError:
        print_error("validation_error", "Timeout must be a number and retries must be an integer.")
        raise typer.Exit(1)

    new_cfg = load_config()
    new_cfg.api_token = api_token
    new_cfg.timeout_seconds = timeout_seconds
    new_cfg.retries = retries
    new_cfg.locale = locale_text or None

    console.print("\nValidating token with `general.api_v1_seller_info_get`…")
    try:
        result = call_api("general", "api_v1_seller_info_get", new_cfg)
        seller = to_data(result)
        seller_name = seller.get("name") if isinstance(seller, dict) else None
        if seller_name:
            console.print(f"[green]✓[/green] Connected as: {seller_name}")
        else:
            console.print("[green]✓[/green] Token is valid")
    except typer.Exit:
        raise
    except Exception as exc:
        print_error("auth_error", f"Validation failed: {exc}")
        raise typer.Exit(1)

    save_config(new_cfg)
    console.print(f"\n[green]✓[/green] Config saved to {CONFIG_PATH}")
    print_json(config_as_dict(new_cfg))
