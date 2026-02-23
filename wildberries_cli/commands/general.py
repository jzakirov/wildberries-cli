"""general subcommand: ping / seller-info / users."""


import typer

from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit
from wildberries_cli.serialize import to_data

app = typer.Typer(name="general", help="General Wildberries seller APIs.", no_args_is_help=True)


@app.command("ping")
def ping(ctx: typer.Context) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("general", "ping_get", cfg, require_token=False))
    emit(data, pretty=cfg.pretty)


@app.command("seller-info")
def seller_info(ctx: typer.Context) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("general", "api_v1_seller_info_get", cfg))
    emit(data, pretty=cfg.pretty)


@app.command("users")
def users_list(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit", help="Max users to return (<=100)"),
    offset: int | None = typer.Option(None, "--offset", help="Pagination offset"),
    invited_only: bool | None = typer.Option(
        None,
        "--invited-only/--active",
        help="List invited (not activated) users or active users",
    ),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"limit": limit, "offset": offset}
    if invited_only is not None:
        kwargs["is_invite_only"] = invited_only
    data = to_data(call_api("general", "api_v1_users_get", cfg, **{k: v for k, v in kwargs.items() if v is not None}))
    emit(data, pretty=cfg.pretty)
