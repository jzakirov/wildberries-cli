"""promotion subcommand — WB Promote / Advertising campaigns management."""

from __future__ import annotations

from typing import Any, Optional

import typer

from wildberries_cli.args import load_json_input
from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, print_error, simple_table
from wildberries_cli.serialize import to_data

app = typer.Typer(name="promotion", help="WB Promote advertising APIs.", no_args_is_help=True)

campaigns_app = typer.Typer(
    name="campaigns", help="Ad campaign lifecycle management.", no_args_is_help=True
)
budget_app = typer.Typer(name="budget", help="Campaign budget and balance.", no_args_is_help=True)
stats_app = typer.Typer(name="stats", help="Campaign and keyword statistics.", no_args_is_help=True)
bids_app = typer.Typer(name="bids", help="Search bid management.", no_args_is_help=True)
keywords_app = typer.Typer(
    name="keywords", help="Normalised keyword (normquery) management.", no_args_is_help=True
)
auction_app = typer.Typer(
    name="auction", help="Auction NM and placement management.", no_args_is_help=True
)
calendar_app = typer.Typer(
    name="calendar", help="WB promotional calendar (akcii).", no_args_is_help=True
)

app.add_typer(campaigns_app, name="campaigns")
app.add_typer(budget_app, name="budget")
app.add_typer(stats_app, name="stats")
app.add_typer(bids_app, name="bids")
app.add_typer(keywords_app, name="keywords")
app.add_typer(auction_app, name="auction")
app.add_typer(calendar_app, name="calendar")


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


@campaigns_app.command("list")
def campaigns_list(
    ctx: typer.Context,
    status: Optional[int] = typer.Option(
        None,
        "--status",
        help="Filter by status: 1=ready, 4=running, 8=paused, 9=ended, 11=rate_exceeded, 14=scheduled",
    ),
    type: Optional[int] = typer.Option(
        None,
        "--type",
        help="Filter by type: 4=catalog, 5=search+catalog, 6=search, 7=recommendations, 8=auto, 9=search_auto",
    ),
    limit: Optional[int] = typer.Option(None, "--limit", help="Max campaigns to return (<=1000)"),
    offset: Optional[int] = typer.Option(None, "--offset", help="Pagination offset"),
    order: Optional[str] = typer.Option(None, "--order", help="Sort field: create|change|id"),
    direction: Optional[str] = typer.Option(None, "--direction", help="Sort direction: asc|desc"),
) -> None:
    """List advertising campaigns with optional filters."""
    cfg: Config = ctx.obj
    kwargs = {
        "status": status,
        "type": type,
        "limit": limit,
        "offset": offset,
        "order": order,
        "direction": direction,
    }
    data = to_data(
        call_api(
            "promotion",
            "adv_v1_adverts_get",
            cfg,
            **{k: v for k, v in kwargs.items() if v is not None},
        )
    )
    emit(data, pretty=cfg.pretty, table_builder=_campaigns_table)


@campaigns_app.command("get")
def campaigns_get(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign (advert) ID"),
) -> None:
    """Get full details for a single campaign."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_advert_get", cfg, id=campaign_id))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("count")
def campaigns_count(ctx: typer.Context) -> None:
    """Get campaign counts grouped by status and type."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_count_get", cfg))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("start")
def campaigns_start(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID to start"),
) -> None:
    """Start (activate) a campaign."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v0_start_get", cfg, id=campaign_id))
    emit(data if data is not None else {"ok": True, "id": campaign_id}, pretty=cfg.pretty)


@campaigns_app.command("stop")
def campaigns_stop(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID to stop"),
) -> None:
    """Stop (end) a campaign permanently."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v0_stop_get", cfg, id=campaign_id))
    emit(data if data is not None else {"ok": True, "id": campaign_id}, pretty=cfg.pretty)


@campaigns_app.command("pause")
def campaigns_pause(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID to pause"),
) -> None:
    """Pause a running campaign."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v0_pause_get", cfg, id=campaign_id))
    emit(data if data is not None else {"ok": True, "id": campaign_id}, pretty=cfg.pretty)


@campaigns_app.command("delete")
def campaigns_delete(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID to delete"),
) -> None:
    """Delete a stopped/ended campaign."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v0_delete_get", cfg, id=campaign_id))
    emit(data if data is not None else {"ok": True, "id": campaign_id}, pretty=cfg.pretty)


@campaigns_app.command("rename")
def campaigns_rename(
    ctx: typer.Context,
    campaign_id: int = typer.Option(..., "--id", help="Campaign ID"),
    name: str = typer.Option(..., "--name", help="New campaign name"),
) -> None:
    """Rename an advertising campaign."""
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.promotion.models.adv_v0_rename_post_request import (
            AdvV0RenamePostRequest,
        )

        req = AdvV0RenamePostRequest(advert_id=campaign_id, name=name)
    except Exception as exc:
        print_error("validation_error", f"Invalid rename request: {exc}")
        raise typer.Exit(1)
    data = to_data(call_api("promotion", "adv_v0_rename_post", cfg, adv_v0_rename_post_request=req))
    emit(
        data if data is not None else {"ok": True, "id": campaign_id, "name": name},
        pretty=cfg.pretty,
    )


@campaigns_app.command("promo-count")
def campaigns_promo_count(ctx: typer.Context) -> None:
    """Get count of campaigns eligible for promotional calendar actions."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_promotion_count_get", cfg))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("upd-dates")
def campaigns_upd_dates(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--from", help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option(..., "--to", help="End date YYYY-MM-DD"),
) -> None:
    """Get campaigns updated within a date range."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_upd_get", cfg, var_from=date_from, to=date_to))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("payments")
def campaigns_payments(
    ctx: typer.Context,
    date_from: str = typer.Option(..., "--from", help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option(..., "--to", help="End date YYYY-MM-DD"),
) -> None:
    """Get advertising payment history for a date range."""
    cfg: Config = ctx.obj
    data = to_data(
        call_api("promotion", "adv_v1_payments_get", cfg, var_from=date_from, to=date_to)
    )
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("subjects")
def campaigns_subjects(
    ctx: typer.Context,
    payment_type: Optional[str] = typer.Option(
        None, "--payment-type", help="Payment type filter: cpm|cpc"
    ),
) -> None:
    """List product subjects (categories) available for advertising."""
    cfg: Config = ctx.obj
    kwargs = {}
    if payment_type:
        kwargs["payment_type"] = payment_type
    data = to_data(call_api("promotion", "adv_v1_supplier_subjects_get", cfg, **kwargs))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("nms")
def campaigns_nms(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get NM (product) lists for campaigns. Body: list of campaign IDs [{...}]."""
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(call_api("promotion", "adv_v2_supplier_nms_post", cfg, request_body=body))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("adverts-v2")
def campaigns_adverts_v2(
    ctx: typer.Context,
    ids: Optional[list[int]] = typer.Option(None, "--id", help="Campaign ID(s). Repeat option."),
    statuses: Optional[list[int]] = typer.Option(
        None, "--status", help="Status filter(s). Repeat option."
    ),
    payment_type: Optional[str] = typer.Option(
        None, "--payment-type", help="Payment type: cpm|cpc"
    ),
) -> None:
    """Get campaign details via the v2 adverts endpoint (supports batch IDs)."""
    cfg: Config = ctx.obj
    kwargs: dict = {}
    if ids:
        kwargs["ids"] = ",".join(str(v) for v in ids)
    if statuses:
        kwargs["statuses"] = ",".join(str(v) for v in statuses)
    if payment_type:
        kwargs["payment_type"] = payment_type
    data = to_data(call_api("promotion", "api_advert_v2_adverts_get", cfg, **kwargs))
    emit(data, pretty=cfg.pretty)


@campaigns_app.command("seacat-save")
def campaigns_seacat_save(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Create/update a search+catalog campaign (seacat).

    Body example:
    {"name":"My campaign","nms":[123456,123457],"bid_type":"manual","payment_type":"cpm","placement_types":["search"]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.adv_v2_seacat_save_ad_post_request import (
            AdvV2SeacatSaveAdPostRequest,
        )

        req = AdvV2SeacatSaveAdPostRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v2_seacat_save_ad_post", cfg, adv_v2_seacat_save_ad_post_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


@budget_app.command("balance")
def budget_balance(ctx: typer.Context) -> None:
    """Get overall advertising account balance (cash + bonuses)."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_balance_get", cfg))
    emit(data, pretty=cfg.pretty)


@budget_app.command("get")
def budget_get(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
) -> None:
    """Get the budget remaining for a specific campaign."""
    cfg: Config = ctx.obj
    data = to_data(call_api("promotion", "adv_v1_budget_get", cfg, id=campaign_id))
    emit(data, pretty=cfg.pretty)


@budget_app.command("deposit")
def budget_deposit(
    ctx: typer.Context,
    campaign_id: int = typer.Option(..., "--id", help="Campaign ID"),
    amount: int = typer.Option(
        ..., "--amount", help="Amount to deposit in kopecks (100 kopecks = 1 RUB)"
    ),
) -> None:
    """Deposit funds into a campaign's budget."""
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.promotion.models.adv_v1_budget_deposit_post_request import (
            AdvV1BudgetDepositPostRequest,
        )

        req = AdvV1BudgetDepositPostRequest(**{"sum": amount})
    except Exception as exc:
        print_error("validation_error", f"Invalid deposit request: {exc}")
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion",
            "adv_v1_budget_deposit_post",
            cfg,
            id=campaign_id,
            adv_v1_budget_deposit_post_request=req,
        )
    )
    emit(
        data if data is not None else {"ok": True, "id": campaign_id, "amount": amount},
        pretty=cfg.pretty,
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@stats_app.command("get")
def stats_get(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get campaign statistics.

    Body is a JSON array of objects, e.g.:
    [{"id": 12345, "dates": ["2024-01-15", "2024-01-16"]}]
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.adv_v1_stats_post_request_inner import (
            AdvV1StatsPostRequestInner,
        )

        if not isinstance(body, list):
            raise ValueError("Body must be a JSON array")
        items = [AdvV1StatsPostRequestInner.from_dict(item) for item in body]
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api("promotion", "adv_v1_stats_post", cfg, adv_v1_stats_post_request_inner=items)
    )
    emit(data, pretty=cfg.pretty)


@stats_app.command("fullstats")
def stats_fullstats(
    ctx: typer.Context,
    ids: list[int] = typer.Option(..., "--id", help="Campaign ID(s). Repeat option."),
    begin_date: str = typer.Option(..., "--from", help="Start date YYYY-MM-DD"),
    end_date: str = typer.Option(..., "--to", help="End date YYYY-MM-DD"),
) -> None:
    """Get full granular statistics for campaigns within a date range.

    Returns daily breakdowns of impressions, clicks, CTR, spend, and orders.
    Essential for ROI analysis and bid optimisation decisions.
    """
    cfg: Config = ctx.obj
    data = to_data(
        call_api(
            "promotion",
            "adv_v3_fullstats_get",
            cfg,
            ids=",".join(str(v) for v in ids),
            begin_date=begin_date,
            end_date=end_date,
        )
    )
    emit(data, pretty=cfg.pretty, table_builder=_fullstats_table)


@stats_app.command("keywords")
def stats_keywords(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get per-keyword statistics for search campaigns (v1).

    Body: {"items": [{"id": 12345, "dates": ["2024-01-15"]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v1_get_norm_query_stats_request import (
            V1GetNormQueryStatsRequest,
        )

        req = V1GetNormQueryStatsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v1_normquery_stats_post", cfg, v1_get_norm_query_stats_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Bids (CPM / search)
# ---------------------------------------------------------------------------


@bids_app.command("set")
def bids_set(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Set CPM bids for NMs in search campaigns.

    Body: {"bids": [{"advertId": 12345, "nmBids": [{"nm": 67890, "bid": 300}]}]}

    Bids are in kopecks (300 = 3 RUB). Minimum bid varies by category.
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.api_advert_v1_bids_patch_request import (
            ApiAdvertV1BidsPatchRequest,
        )

        req = ApiAdvertV1BidsPatchRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api("promotion", "api_advert_v1_bids_patch", cfg, api_advert_v1_bids_patch_request=req)
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


@bids_app.command("min")
def bids_min(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get minimum CPM bids for NMs (by category/subject).

    Body: {"nmIds": [67890, 67891]}

    Use this to understand the floor bid before setting CPMs.
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.api_advert_v1_bids_min_post_request import (
            ApiAdvertV1BidsMinPostRequest,
        )

        req = ApiAdvertV1BidsMinPostRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "api_advert_v1_bids_min_post", cfg, api_advert_v1_bids_min_post_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Keywords (normquery)
# ---------------------------------------------------------------------------


@keywords_app.command("list")
def keywords_list(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """List normalised keywords (normqueries) for a campaign.

    Body: {"items": [{"id": 12345}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_get_norm_query_list_request import (
            V0GetNormQueryListRequest,
        )

        req = V0GetNormQueryListRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api("promotion", "adv_v0_normquery_list_post", cfg, v0_get_norm_query_list_request=req)
    )
    emit(data, pretty=cfg.pretty)


@keywords_app.command("bids-get")
def keywords_bids_get(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get current bids for normalised keywords.

    Body: {"items": [{"id": 12345, "normQueries": ["кроссовки мужские"]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_get_norm_query_bids_request import (
            V0GetNormQueryBidsRequest,
        )

        req = V0GetNormQueryBidsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v0_normquery_get_bids_post", cfg, v0_get_norm_query_bids_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


@keywords_app.command("bids-set")
def keywords_bids_set(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Set bids for normalised keywords in a search campaign.

    Body: {"items": [{"id": 12345, "normQueries": [{"normQuery": "кроссовки", "bid": 300}]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_set_norm_query_bids_request import (
            V0SetNormQueryBidsRequest,
        )

        req = V0SetNormQueryBidsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api("promotion", "adv_v0_normquery_bids_post", cfg, v0_set_norm_query_bids_request=req)
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


@keywords_app.command("bids-del")
def keywords_bids_del(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Delete keyword-level bids (revert to campaign-level CPM).

    Body: {"items": [{"id": 12345, "normQueries": ["кроссовки мужские"]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_set_norm_query_bids_request import (
            V0SetNormQueryBidsRequest,
        )

        req = V0SetNormQueryBidsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v0_normquery_bids_delete", cfg, v0_set_norm_query_bids_request=req
        )
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


@keywords_app.command("minus-get")
def keywords_minus_get(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get minus-keywords (excluded search queries) for a campaign.

    Body: {"items": [{"id": 12345}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_get_norm_query_minus_request import (
            V0GetNormQueryMinusRequest,
        )

        req = V0GetNormQueryMinusRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v0_normquery_get_minus_post", cfg, v0_get_norm_query_minus_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


@keywords_app.command("minus-set")
def keywords_minus_set(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Set minus-keywords (excluded queries) for a campaign.

    Body: {"items": [{"id": 12345, "minusNormQueries": ["бесплатно", "б/у"]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_set_minus_norm_query_request import (
            V0SetMinusNormQueryRequest,
        )

        req = V0SetMinusNormQueryRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v0_normquery_set_minus_post", cfg, v0_set_minus_norm_query_request=req
        )
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


@keywords_app.command("stats")
def keywords_stats(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Get keyword-level statistics (v0 — impressions/clicks per normquery).

    Body: {"items": [{"id": 12345, "dates": ["2024-01-15"]}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.v0_get_norm_query_stats_request import (
            V0GetNormQueryStatsRequest,
        )

        req = V0GetNormQueryStatsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v0_normquery_stats_post", cfg, v0_get_norm_query_stats_request=req
        )
    )
    emit(data, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Auction (NM lists and placements for manual campaigns)
# ---------------------------------------------------------------------------


@auction_app.command("nms")
def auction_nms(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Update the NM (product) list of a manual search campaign.

    Body: {"nms": [{"campaignId": 12345, "nms": {"add": [67890], "delete": []}}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.adv_v0_auction_nms_patch_request import (
            AdvV0AuctionNmsPatchRequest,
        )

        req = AdvV0AuctionNmsPatchRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api("promotion", "adv_v0_auction_nms_patch", cfg, adv_v0_auction_nms_patch_request=req)
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


@auction_app.command("placements")
def auction_placements(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Change placement types for a manual search campaign.

    Body: {"placements": [{"advertId": 12345, "placements": {"search": true, "catalog": false}}]}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.adv_v0_auction_placements_put_request import (
            AdvV0AuctionPlacementsPutRequest,
        )

        req = AdvV0AuctionPlacementsPutRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion",
            "adv_v0_auction_placements_put",
            cfg,
            adv_v0_auction_placements_put_request=req,
        )
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Calendar (promotional akcii)
# ---------------------------------------------------------------------------


@calendar_app.command("list")
def calendar_list(
    ctx: typer.Context,
    start_date: str = typer.Option(
        ..., "--from", help="Start datetime (RFC3339, e.g. 2024-01-01T00:00:00Z)"
    ),
    end_date: str = typer.Option(..., "--to", help="End datetime (RFC3339)"),
    all_promo: bool = typer.Option(
        False, "--all/--eligible", help="True=all WB promos, False=promos your products qualify for"
    ),
    limit: Optional[int] = typer.Option(None, "--limit", help="Max promotions to return"),
    offset: Optional[int] = typer.Option(None, "--offset", help="Pagination offset"),
) -> None:
    """List WB promotional calendar actions (akcii) in a date range."""
    cfg: Config = ctx.obj
    kwargs = {
        "start_date_time": start_date,
        "end_date_time": end_date,
        "all_promo": all_promo,
    }
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    data = to_data(call_api("promotion", "api_v1_calendar_promotions_get", cfg, **kwargs))
    emit(data, pretty=cfg.pretty)


@calendar_app.command("details")
def calendar_details(
    ctx: typer.Context,
    promotion_ids: list[int] = typer.Option(..., "--id", help="Promotion ID(s). Repeat option."),
) -> None:
    """Get detailed info about specific WB promotional actions."""
    cfg: Config = ctx.obj
    data = to_data(
        call_api(
            "promotion", "api_v1_calendar_promotions_details_get", cfg, promotion_ids=promotion_ids
        )
    )
    emit(data, pretty=cfg.pretty)


@calendar_app.command("products")
def calendar_products(
    ctx: typer.Context,
    promotion_id: int = typer.Option(..., "--id", help="Promotion ID"),
    in_action: bool = typer.Option(
        ...,
        "--in-action/--eligible",
        help="True=products already in action, False=eligible but not enrolled",
    ),
    limit: Optional[int] = typer.Option(None, "--limit"),
    offset: Optional[int] = typer.Option(None, "--offset"),
) -> None:
    """List products for a promotional action (enrolled or eligible)."""
    cfg: Config = ctx.obj
    kwargs: dict = {"promotion_id": promotion_id, "in_action": in_action}
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    data = to_data(
        call_api("promotion", "api_v1_calendar_promotions_nomenclatures_get", cfg, **kwargs)
    )
    emit(data, pretty=cfg.pretty)


@calendar_app.command("upload")
def calendar_upload(
    ctx: typer.Context,
    body_json: Optional[str] = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Path to JSON body file"),
) -> None:
    """Enrol products into a promotional action.

    Body: {"data": {"promotionId": 123, "nomenclatures": [{"nmId": 67890, "price": 999}]}}
    """
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json=body_json, body_file=body_file)
        from wildberries_sdk.promotion.models.api_v1_calendar_promotions_upload_post_request import (
            ApiV1CalendarPromotionsUploadPostRequest,
        )

        req = ApiV1CalendarPromotionsUploadPostRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", str(exc))
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion",
            "api_v1_calendar_promotions_upload_post",
            cfg,
            api_v1_calendar_promotions_upload_post_request=req,
        )
    )
    emit(data if data is not None else {"ok": True}, pretty=cfg.pretty)


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------


def _campaigns_table(data: Any) -> Optional["Table"]:  # noqa: F821
    if not isinstance(data, list) or not data:
        return None
    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "id": item.get("advertId") or item.get("id"),
                "name": item.get("name"),
                "type": item.get("type"),
                "status": item.get("status"),
                "budget": item.get("dailyBudget"),
                "changed": item.get("changeTime") or item.get("changeDate"),
            }
        )
    return simple_table(
        rows,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Type", "type"),
            ("Status", "status"),
            ("Budget", "budget"),
            ("Changed", "changed"),
        ],
        title="Campaigns",
    )


def _fullstats_table(data: Any) -> Optional["Table"]:  # noqa: F821
    if not isinstance(data, list) or not data:
        return None
    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "id": item.get("advert_id") or item.get("advertId"),
                "views": item.get("views"),
                "clicks": item.get("clicks"),
                "ctr": item.get("ctr"),
                "cpc": item.get("cpc"),
                "spend": item.get("sum"),
                "orders": item.get("orders"),
                "cr": item.get("cr"),
            }
        )
    return simple_table(
        rows,
        [
            ("CampaignID", "id"),
            ("Views", "views"),
            ("Clicks", "clicks"),
            ("CTR%", "ctr"),
            ("CPC", "cpc"),
            ("Spend", "spend"),
            ("Orders", "orders"),
            ("CR%", "cr"),
        ],
        title="Campaign Full Stats",
    )
