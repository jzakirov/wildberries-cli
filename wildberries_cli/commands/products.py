"""products subcommand (selected read endpoints + cards list body query)."""


import typer

from wildberries_cli.args import load_json_input
from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, print_error
from wildberries_cli.serialize import to_data

app = typer.Typer(name="products", help="Products APIs (selected endpoints).", no_args_is_help=True)
cards_app = typer.Typer(name="cards", help="Product cards.", no_args_is_help=True)
objects_app = typer.Typer(name="objects", help="Product objects/categories.", no_args_is_help=True)
directories_app = typer.Typer(name="directories", help="Reference directories.", no_args_is_help=True)
tags_app = typer.Typer(name="tags", help="Product tags.", no_args_is_help=True)

app.add_typer(cards_app, name="cards")
app.add_typer(objects_app, name="objects")
app.add_typer(directories_app, name="directories")
app.add_typer(tags_app, name="tags")


@cards_app.command("limits")
def cards_limits(ctx: typer.Context) -> None:
    cfg: Config = ctx.obj
    emit(to_data(call_api("products", "content_v2_cards_limits_get", cfg)), pretty=cfg.pretty)


@cards_app.command("list")
def cards_list(
    ctx: typer.Context,
    body_json: str | None = typer.Option(None, "--body-json", help="JSON request body or '-' for stdin"),
    body_file: str | None = typer.Option(None, "--body-file", help="Path to JSON request body file"),
    locale: str | None = typer.Option(None, "--locale", help="Locale (ru|en|zh)"),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.products.models.content_v2_get_cards_list_post_request import (
            ContentV2GetCardsListPostRequest,
        )

        req = ContentV2GetCardsListPostRequest.from_dict(body)
    except ValueError as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        print_error("validation_error", f"Invalid cards list request body: {exc}")
        raise typer.Exit(1)

    call_kwargs = {"content_v2_get_cards_list_post_request": req}
    if locale or cfg.locale:
        call_kwargs["locale"] = locale or cfg.locale
    emit(to_data(call_api("products", "content_v2_get_cards_list_post", cfg, **call_kwargs)), pretty=cfg.pretty)


@objects_app.command("list")
def objects_list(
    ctx: typer.Context,
    locale: str | None = typer.Option(None, "--locale", help="Locale (ru|en|zh)"),
    name: str | None = typer.Option(None, "--name", help="Search by subject name substring"),
    limit: int | None = typer.Option(None, "--limit"),
    offset: int | None = typer.Option(None, "--offset"),
    parent_id: int | None = typer.Option(None, "--parent-id"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {
        "locale": locale or cfg.locale,
        "name": name,
        "limit": limit,
        "offset": offset,
        "parent_id": parent_id,
    }
    emit(to_data(call_api("products", "content_v2_object_all_get", cfg, **{k: v for k, v in kwargs.items() if v is not None})), pretty=cfg.pretty)


@directories_app.command("colors")
def directories_colors(
    ctx: typer.Context,
    locale: str | None = typer.Option(None, "--locale", help="Locale (ru|en|zh)"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {"locale": locale or cfg.locale} if (locale or cfg.locale) else {}
    emit(to_data(call_api("products", "content_v2_directory_colors_get", cfg, **kwargs)), pretty=cfg.pretty)


@tags_app.command("list")
def tags_list(ctx: typer.Context) -> None:
    cfg: Config = ctx.obj
    emit(to_data(call_api("products", "content_v2_tags_get", cfg)), pretty=cfg.pretty)
