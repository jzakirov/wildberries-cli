"""tariffs subcommand."""


import typer

from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit
from wildberries_cli.serialize import to_data

app = typer.Typer(name="tariffs", help="Tariffs and coefficients.", no_args_is_help=True)


@app.command("commission")
def commission(
    ctx: typer.Context,
    locale: str | None = typer.Option(None, "--locale", help="Locale for names (ru|en|zh)"),
) -> None:
    cfg: Config = ctx.obj
    locale = locale or cfg.locale
    kwargs = {"locale": locale} if locale else {}
    emit(to_data(call_api("tariffs", "api_v1_tariffs_commission_get", cfg, **kwargs)), pretty=cfg.pretty)


@app.command("box")
def box_tariff(
    ctx: typer.Context,
    date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD"),
) -> None:
    cfg: Config = ctx.obj
    emit(to_data(call_api("tariffs", "api_v1_tariffs_box_get", cfg, var_date=date)), pretty=cfg.pretty)


@app.command("pallet")
def pallet_tariff(
    ctx: typer.Context,
    date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD"),
) -> None:
    cfg: Config = ctx.obj
    emit(to_data(call_api("tariffs", "api_v1_tariffs_pallet_get", cfg, var_date=date)), pretty=cfg.pretty)


@app.command("return")
def return_tariff(
    ctx: typer.Context,
    date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD"),
) -> None:
    cfg: Config = ctx.obj
    emit(to_data(call_api("tariffs", "api_v1_tariffs_return_get", cfg, var_date=date)), pretty=cfg.pretty)


@app.command("acceptance-coefficients")
def acceptance_coefficients(
    ctx: typer.Context,
    warehouse_ids: str | None = typer.Option(None, "--warehouse-ids", help="Comma-separated warehouse IDs"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"warehouse_ids": warehouse_ids} if warehouse_ids else {}
    emit(to_data(call_api("tariffs", "api_tariffs_v1_acceptance_coefficients_get", cfg, **kwargs)), pretty=cfg.pretty)
