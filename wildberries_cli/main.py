"""wildberries CLI root application."""


from importlib.metadata import version
from typing import Optional

import typer

from wildberries_cli.config import load_config


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"wildberries-cli {version('wildberries-cli')}")
        raise typer.Exit()


from wildberries_cli.commands import (  # noqa: E402
    communications,
    config_cmd,
    general,
    orders_fbs,
    products,
    raw,
    reports,
    tariffs,
)

app = typer.Typer(
    name="wildberries",
    help="[bold]wildberries[/bold] — Wildberries seller platform from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(config_cmd.app, name="config")
app.add_typer(general.app, name="general")
app.add_typer(tariffs.app, name="tariffs")
app.add_typer(reports.app, name="reports")
app.add_typer(communications.app, name="communications")
app.add_typer(products.app, name="products")
app.add_typer(orders_fbs.app, name="orders-fbs")
app.add_typer(raw.app, name="raw")


@app.callback()
def main(
    ctx: typer.Context,
    api_token: Optional[str] = typer.Option(
        None,
        "--api-token",
        envvar="WB_API_TOKEN",
        help="Wildberries API token (overrides config)",
        show_envvar=True,
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        envvar="WB_TIMEOUT",
        help="Request timeout in seconds (overrides config)",
        show_envvar=True,
    ),
    retries: Optional[int] = typer.Option(
        None,
        "--retries",
        envvar="WB_RETRIES",
        help="Max retry attempts for retryable API errors",
        show_envvar=True,
    ),
    locale: Optional[str] = typer.Option(
        None,
        "--locale",
        envvar="WB_LOCALE",
        help="Default locale for endpoints that support it (ru|en|zh)",
        show_envvar=True,
    ),
    pretty: Optional[bool] = typer.Option(
        None,
        "--pretty/--no-pretty",
        envvar="WB_PRETTY",
        help="Render Rich tables / pretty JSON when available (overrides config)",
        show_envvar=True,
    ),
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Interact with Wildberries Seller APIs via wildberries-sdk."""
    ctx.ensure_object(dict)
    cfg = load_config(
        api_token_flag=api_token,
        timeout_flag=timeout,
        retries_flag=retries,
        locale_flag=locale,
        pretty_flag=pretty,
    )
    ctx.obj = cfg
