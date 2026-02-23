"""orders-fbs subcommand (selected operational endpoints)."""


import typer

from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, fbs_orders_table, print_error
from wildberries_cli.serialize import to_data

app = typer.Typer(name="orders-fbs", help="Orders FBS APIs (selected endpoints).", no_args_is_help=True)
orders_app = typer.Typer(name="orders", help="FBS orders.", no_args_is_help=True)
supplies_app = typer.Typer(name="supplies", help="FBS supplies.", no_args_is_help=True)
app.add_typer(orders_app, name="orders")
app.add_typer(supplies_app, name="supplies")


@orders_app.command("new")
def orders_new(ctx: typer.Context) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("orders_fbs", "api_v3_orders_new_get", cfg))
    emit(data, pretty=cfg.pretty, table_builder=fbs_orders_table)


@orders_app.command("list")
def orders_list(
    ctx: typer.Context,
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    cursor: int = typer.Option(0, "--next", help="Pagination cursor"),
    date_from: int | None = typer.Option(None, "--date-from", help="Unix timestamp start"),
    date_to: int | None = typer.Option(None, "--date-to", help="Unix timestamp end"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"limit": limit, "next": cursor, "date_from": date_from, "date_to": date_to}
    data = to_data(call_api("orders_fbs", "api_v3_orders_get", cfg, **{k: v for k, v in kwargs.items() if v is not None}))
    emit(data, pretty=cfg.pretty, table_builder=fbs_orders_table)


@orders_app.command("status")
def orders_status(
    ctx: typer.Context,
    order_ids: list[int] = typer.Option(..., "--order", help="Order ID(s). Repeat option up to API limit."),
) -> None:
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.orders_fbs.models.api_v3_orders_status_post_request import ApiV3OrdersStatusPostRequest

        req = ApiV3OrdersStatusPostRequest(orders=order_ids)
    except Exception as exc:
        print_error("validation_error", f"Invalid status request: {exc}")
        raise typer.Exit(1)

    data = to_data(call_api("orders_fbs", "api_v3_orders_status_post", cfg, api_v3_orders_status_post_request=req))
    emit(data, pretty=cfg.pretty)


@orders_app.command("stickers")
def orders_stickers(
    ctx: typer.Context,
    order_ids: list[int] = typer.Option(..., "--order", help="Order ID(s). Repeat option."),
    type: str = typer.Option(..., "--type", help="Sticker type"),
    width: int = typer.Option(..., "--width", help="Sticker width"),
    height: int = typer.Option(..., "--height", help="Sticker height"),
) -> None:
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.orders_fbs.models.api_v3_orders_stickers_post_request import (
            ApiV3OrdersStickersPostRequest,
        )

        req = ApiV3OrdersStickersPostRequest(orders=order_ids)
    except Exception as exc:
        print_error("validation_error", f"Invalid stickers request: {exc}")
        raise typer.Exit(1)

    data = to_data(
        call_api(
            "orders_fbs",
            "api_v3_orders_stickers_post",
            cfg,
            type=type,
            width=width,
            height=height,
            api_v3_orders_stickers_post_request=req,
        )
    )
    emit(data, pretty=cfg.pretty)


@supplies_app.command("list")
def supplies_list(
    ctx: typer.Context,
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    cursor: int = typer.Option(0, "--next", help="Pagination cursor"),
) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("orders_fbs", "api_v3_supplies_get", cfg, limit=limit, next=cursor))
    emit(data, pretty=cfg.pretty)


@supplies_app.command("create")
def supplies_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Supply name"),
) -> None:
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.orders_fbs.models.api_v3_supplies_post_request import ApiV3SuppliesPostRequest

        req = ApiV3SuppliesPostRequest(name=name)
    except Exception as exc:
        print_error("validation_error", f"Invalid supply request: {exc}")
        raise typer.Exit(1)

    data = to_data(call_api("orders_fbs", "api_v3_supplies_post", cfg, api_v3_supplies_post_request=req))
    emit(data, pretty=cfg.pretty)
