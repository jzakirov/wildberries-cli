"""reports subcommand (read-only exports)."""


import typer

from wildberries_cli.args import parse_rfc3339ish
from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, reports_table
from wildberries_cli.serialize import to_data

app = typer.Typer(name="reports", help="Reports API helpers (orders, sales, stocks, incomes).", no_args_is_help=True)


@app.command("orders")
def supplier_orders(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--date-from", help="RFC3339/ISO datetime in MSK timezone semantics"),
    flag: int | None = typer.Option(None, "--flag", help="WB API flag (0 incremental, 1 by date)"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"date_from": parse_rfc3339ish(date_from)}
    if flag is not None:
        kwargs["flag"] = flag
    data = to_data(call_api("reports", "api_v1_supplier_orders_get", cfg, **kwargs))
    emit(data, pretty=cfg.pretty, table_builder=reports_table)


@app.command("sales")
def supplier_sales(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--date-from", help="RFC3339/ISO datetime in MSK timezone semantics"),
    flag: int | None = typer.Option(None, "--flag", help="WB API flag (0 incremental, 1 by date)"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"date_from": parse_rfc3339ish(date_from)}
    if flag is not None:
        kwargs["flag"] = flag
    data = to_data(call_api("reports", "api_v1_supplier_sales_get", cfg, **kwargs))
    emit(data, pretty=cfg.pretty, table_builder=reports_table)


@app.command("stocks")
def supplier_stocks(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--date-from", help="RFC3339/ISO datetime (use an early date for full stock snapshot)"),
) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("reports", "api_v1_supplier_stocks_get", cfg, date_from=parse_rfc3339ish(date_from)))
    emit(data, pretty=cfg.pretty, table_builder=reports_table)


@app.command("incomes")
def supplier_incomes(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--date-from", help="RFC3339/ISO datetime"),
) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("reports", "api_v1_supplier_incomes_get", cfg, date_from=parse_rfc3339ish(date_from)))
    emit(data, pretty=cfg.pretty, table_builder=reports_table)
