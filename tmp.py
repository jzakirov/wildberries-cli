"""Temporary WB Promote optimization playground (moved out of CLI wrapper)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Optional

import typer

from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, print_error
from wildberries_cli.serialize import to_data

optimize_app = typer.Typer(
    name="optimize",
    help="Rule-based optimization workflows for WB Promote campaigns.",
    no_args_is_help=True,
)
app = optimize_app

# ---------------------------------------------------------------------------
# Optimize (rule-based workflows)
# ---------------------------------------------------------------------------


@optimize_app.command("snapshot")
def optimize_snapshot(
    ctx: typer.Context,
    ids: Optional[list[int]] = typer.Option(None, "--id", help="Campaign ID(s). Repeat option."),
    statuses: Optional[list[int]] = typer.Option(
        None,
        "--status",
        help="Campaign statuses for discovery. Repeat option. Default: 9(active),11(paused)",
    ),
    payment_type: Optional[str] = typer.Option(None, "--payment-type", help="cpm|cpc"),
    date_from: Optional[str] = typer.Option(
        None, "--from", help="Start date YYYY-MM-DD (default: last 7 closed days)"
    ),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD"),
    include_budget: bool = typer.Option(
        True, "--budget/--no-budget", help="Fetch per-campaign budgets"
    ),
) -> None:
    """Build a normalized campaign performance snapshot for automation and LLM analysis."""
    cfg: Config = ctx.obj
    start, end, _, day_count = _resolve_date_range(date_from, date_to, default_days=7)
    default_statuses = statuses if statuses is not None else (None if ids else [9, 11])
    advert_rows = _fetch_adverts_v2(
        cfg, ids=ids, statuses=default_statuses, payment_type=payment_type
    )
    campaign_ids = [int(row["id"]) for row in advert_rows if _is_int(row.get("id"))]
    stats_map = _fetch_fullstats_map(cfg, campaign_ids, start.isoformat(), end.isoformat())
    budgets_map = _fetch_budgets_map(cfg, campaign_ids) if include_budget else {}

    rows: list[dict[str, Any]] = []
    for advert in advert_rows:
        campaign_id = _as_int(advert.get("id"))
        if campaign_id is None:
            continue
        stat = stats_map.get(campaign_id, {})
        metrics = _campaign_metrics(stat)
        settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
        budget = budgets_map.get(campaign_id)
        runway_days = None
        if isinstance(budget, dict):
            total_kop = _as_num(budget.get("total")) or 0
            spend_day_kop = (metrics["spend_rub"] / max(day_count, 1)) * 100
            if spend_day_kop > 0:
                runway_days = round(total_kop / spend_day_kop, 2)
        rows.append(
            {
                "campaign_id": campaign_id,
                "name": settings.get("name"),
                "status": advert.get("status"),
                "bid_type": advert.get("bid_type"),
                "payment_type": settings.get("payment_type"),
                "placements": settings.get("placements"),
                "nms_count": len(advert.get("nm_settings") or []),
                **metrics,
                "budget": budget,
                "budget_runway_days": runway_days,
            }
        )

    emit(
        {
            "period": {"from": start.isoformat(), "to": end.isoformat(), "days": day_count},
            "campaigns": rows,
            "summary": _snapshot_summary(rows),
        },
        pretty=cfg.pretty,
    )


@optimize_app.command("bids-plan")
def optimize_bids_plan(
    ctx: typer.Context,
    ids: list[int] = typer.Option(..., "--id", help="Search campaign ID(s). Repeat option."),
    date_from: Optional[str] = typer.Option(
        None, "--from", help="Start date YYYY-MM-DD (default: last 3 closed days)"
    ),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD"),
    target_cpa: Optional[float] = typer.Option(
        None, "--target-cpa", help="Target CPA in RUB (optional)"
    ),
    min_clicks: int = typer.Option(15, "--min-clicks", help="Minimum clicks before making changes"),
    kill_clicks: int = typer.Option(
        35, "--kill-clicks", help="Zero-order clicks threshold for stronger decrease"
    ),
    min_ctr: Optional[float] = typer.Option(None, "--min-ctr", help="CTR% floor (optional)"),
    max_avg_pos: Optional[float] = typer.Option(
        6.0, "--max-avg-pos", help="If avg position is worse than this, good NMs can be raised"
    ),
    increase_pct: int = typer.Option(10, "--increase-pct", help="Bid increase percent"),
    decrease_pct: int = typer.Option(10, "--decrease-pct", help="Bid decrease percent"),
    strong_decrease_pct: int = typer.Option(
        20, "--strong-decrease-pct", help="Stronger decrease percent"
    ),
    min_orders_for_increase: int = typer.Option(
        2, "--min-orders-for-increase", help="Orders needed before increase"
    ),
    bid_step: int = typer.Option(10, "--bid-step", help="Round bid to this many kopecks"),
    max_bid_kopecks: Optional[int] = typer.Option(
        None, "--max-bid", help="Hard cap for new bids in kopecks"
    ),
    placement: str = typer.Option(
        "auto",
        "--placement",
        help="auto|search|recommendations|combined. auto chooses based on campaign settings.",
    ),
    use_min_bids: bool = typer.Option(
        True, "--min-bids/--no-min-bids", help="Clamp to WB minimum bids"
    ),
    apply: bool = typer.Option(False, "--apply/--no-apply", help="Apply generated bid changes"),
    max_changes: Optional[int] = typer.Option(
        None, "--max-changes", help="Limit number of changes (highest impact first)"
    ),
) -> None:
    """Generate and optionally apply NM bid changes using keyword-cluster performance."""
    cfg: Config = ctx.obj
    allowed_placements = {"auto", "search", "recommendations", "combined"}
    if placement.strip().lower() not in allowed_placements:
        print_error("validation_error", f"--placement must be one of {sorted(allowed_placements)}")
        raise typer.Exit(1)
    start, end, dates, day_count = _resolve_date_range(date_from, date_to, default_days=3)
    advert_rows = _fetch_adverts_v2(cfg, ids=ids)
    advert_map = {int(row["id"]): row for row in advert_rows if _is_int(row.get("id"))}

    missing = [cid for cid in ids if cid not in advert_map]
    if missing:
        print_error("validation_error", f"Campaign(s) not found via adverts-v2: {missing}")
        raise typer.Exit(1)

    keyword_stats = _fetch_keyword_stats_v1(cfg, ids, dates)
    keyword_rows = _extract_keyword_rows(keyword_stats)
    nm_perf = _aggregate_keyword_rows_by_nm(keyword_rows)

    min_bid_map: dict[tuple[int, int, str], int] = {}
    if use_min_bids:
        min_bid_map = _fetch_min_bid_map(cfg, [advert_map[cid] for cid in ids])

    recommendations: list[dict[str, Any]] = []
    for cid in ids:
        advert = advert_map[cid]
        settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
        payment_type = str(settings.get("payment_type") or "")
        if payment_type != "cpm":
            continue
        placement_choice = _choose_bid_placement(advert, placement)
        for nm_settings in advert.get("nm_settings") or []:
            if not isinstance(nm_settings, dict):
                continue
            nm_id = _as_int(nm_settings.get("nm_id"))
            if nm_id is None:
                continue
            perf = nm_perf.get((cid, nm_id))
            current_bid = _current_nm_bid_kopecks(nm_settings, placement_choice)
            if current_bid is None:
                continue
            if perf is None:
                continue
            rec = _recommend_nm_bid(
                campaign_id=cid,
                campaign_name=_safe_get(settings, "name"),
                nm_id=nm_id,
                placement=placement_choice,
                current_bid_kopecks=current_bid,
                perf=perf,
                target_cpa=target_cpa,
                min_clicks=min_clicks,
                kill_clicks=kill_clicks,
                min_ctr=min_ctr,
                max_avg_pos=max_avg_pos,
                increase_pct=increase_pct,
                decrease_pct=decrease_pct,
                strong_decrease_pct=strong_decrease_pct,
                min_orders_for_increase=min_orders_for_increase,
                bid_step=bid_step,
                max_bid_kopecks=max_bid_kopecks,
                min_bid_floor_kopecks=min_bid_map.get((cid, nm_id, placement_choice)),
            )
            if rec is not None:
                recommendations.append(rec)

    # Highest estimated wasted spend / impact first.
    recommendations.sort(
        key=lambda r: (
            _as_num(r.get("priority_score")) or 0,
            _as_num(_safe_get(r, "perf.spend_rub")) or 0,
        ),
        reverse=True,
    )
    if max_changes is not None:
        recommendations = recommendations[: max(0, max_changes)]

    payload = _build_bids_patch_payload(recommendations)
    api_result = None
    if apply and payload["bids"]:
        api_result = _apply_bids_patch(cfg, payload)

    emit(
        {
            "period": {"from": start.isoformat(), "to": end.isoformat(), "days": day_count},
            "summary": _bids_plan_summary(recommendations, apply=apply),
            "recommendations": recommendations,
            "api_payload": payload,
            "api_result": api_result,
        },
        pretty=cfg.pretty,
    )


@optimize_app.command("budget-plan")
def optimize_budget_plan(
    ctx: typer.Context,
    ids: Optional[list[int]] = typer.Option(None, "--id", help="Campaign ID(s). Repeat option."),
    statuses: Optional[list[int]] = typer.Option(
        None,
        "--status",
        help="Campaign statuses for discovery. Repeat option. Default: 9(active),11(paused)",
    ),
    date_from: Optional[str] = typer.Option(
        None, "--from", help="Start date YYYY-MM-DD (default: last 7 closed days)"
    ),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD"),
    target_runway_days: float = typer.Option(3.0, "--runway-days", help="Desired runway in days"),
    min_spend_per_day_rub: float = typer.Option(
        50.0, "--min-spend-day", help="Ignore campaigns with lower average spend/day"
    ),
    max_cpa: Optional[float] = typer.Option(
        None, "--max-cpa", help="Only recommend top-up if CPA <= this"
    ),
    min_roas: Optional[float] = typer.Option(
        None, "--min-roas", help="Only recommend top-up if ROAS >= this"
    ),
    round_to_kopecks: int = typer.Option(
        10000, "--round-to", help="Round suggested top-up to this many kopecks"
    ),
    min_topup_kopecks: int = typer.Option(
        10000, "--min-topup", help="Minimum suggested top-up amount in kopecks"
    ),
) -> None:
    """Prioritize campaign top-ups by runway and efficiency (plan only; no spend is applied)."""
    cfg: Config = ctx.obj
    start, end, _, day_count = _resolve_date_range(date_from, date_to, default_days=7)
    default_statuses = statuses if statuses is not None else (None if ids else [9, 11])
    advert_rows = _fetch_adverts_v2(cfg, ids=ids, statuses=default_statuses)
    campaign_ids = [int(row["id"]) for row in advert_rows if _is_int(row.get("id"))]
    stats_map = _fetch_fullstats_map(cfg, campaign_ids, start.isoformat(), end.isoformat())
    budgets_map = _fetch_budgets_map(cfg, campaign_ids)

    plans: list[dict[str, Any]] = []
    for advert in advert_rows:
        cid = _as_int(advert.get("id"))
        if cid is None:
            continue
        stat = stats_map.get(cid)
        budget = budgets_map.get(cid)
        if not isinstance(stat, dict) or not isinstance(budget, dict):
            continue
        metrics = _campaign_metrics(stat)
        spend_per_day_rub = metrics["spend_rub"] / max(day_count, 1)
        if spend_per_day_rub < min_spend_per_day_rub:
            continue
        if (
            max_cpa is not None
            and metrics.get("cpa_rub") is not None
            and metrics["cpa_rub"] > max_cpa
        ):
            continue
        if min_roas is not None and metrics.get("roas") is not None and metrics["roas"] < min_roas:
            continue

        total_kop = int(_as_num(budget.get("total")) or 0)
        spend_per_day_kop = spend_per_day_rub * 100
        if spend_per_day_kop <= 0:
            continue
        runway_days = total_kop / spend_per_day_kop
        if runway_days >= target_runway_days:
            continue

        needed_kop = int(max(0, (target_runway_days - runway_days) * spend_per_day_kop))
        suggested_kop = _round_up(max(needed_kop, min_topup_kopecks), max(1, round_to_kopecks))
        settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
        plans.append(
            {
                "campaign_id": cid,
                "name": settings.get("name"),
                "status": advert.get("status"),
                "payment_type": settings.get("payment_type"),
                "spend_per_day_rub": round(spend_per_day_rub, 2),
                "current_budget_kopecks": total_kop,
                "runway_days": round(runway_days, 2),
                "suggested_topup_kopecks": suggested_kop,
                "reason": f"runway {runway_days:.2f}d < target {target_runway_days:.2f}d",
                "metrics": metrics,
            }
        )

    plans.sort(
        key=lambda r: (
            -(_as_num(r.get("spend_per_day_rub")) or 0),
            _as_num(r.get("runway_days")) or 999,
        )
    )
    emit(
        {
            "period": {"from": start.isoformat(), "to": end.isoformat(), "days": day_count},
            "target_runway_days": target_runway_days,
            "plans": plans,
            "summary": {
                "campaigns_requiring_topup": len(plans),
                "total_suggested_topup_kopecks": sum(
                    int(p["suggested_topup_kopecks"]) for p in plans
                ),
            },
        },
        pretty=cfg.pretty,
    )


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------


def _resolve_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    *,
    default_days: int,
) -> tuple[date, date, list[str], int]:
    if (date_from is None) ^ (date_to is None):
        print_error("validation_error", "Use both --from and --to, or neither.")
        raise typer.Exit(1)

    if date_from is None and date_to is None:
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=max(0, default_days - 1))
    else:
        try:
            start = date.fromisoformat(str(date_from))
            end = date.fromisoformat(str(date_to))
        except ValueError as exc:
            print_error("validation_error", f"Invalid date: {exc}")
            raise typer.Exit(1)
    if start > end:
        print_error("validation_error", "--from must be <= --to")
        raise typer.Exit(1)
    days = (end - start).days + 1
    if days > 31:
        print_error(
            "validation_error",
            "Max date range is 31 days for fullstats-dependent optimizer commands.",
        )
        raise typer.Exit(1)
    return start, end, [(start + timedelta(days=i)).isoformat() for i in range(days)], days


def _iter_chunks(items: list[Any], size: int) -> list[list[Any]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _fetch_adverts_v2(
    cfg: Config,
    *,
    ids: Optional[list[int]] = None,
    statuses: Optional[list[int]] = None,
    payment_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    chunks = _iter_chunks(ids, 50) if ids else [None]
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for chunk in chunks:
        kwargs: dict[str, Any] = {}
        if chunk:
            kwargs["ids"] = ",".join(str(v) for v in chunk)
        if statuses:
            kwargs["statuses"] = ",".join(str(v) for v in statuses)
        if payment_type:
            kwargs["payment_type"] = payment_type
        data = to_data(call_api("promotion", "api_advert_v2_adverts_get", cfg, **kwargs))
        adverts = data.get("adverts") if isinstance(data, dict) else None
        if not isinstance(adverts, list):
            continue
        for item in adverts:
            if not isinstance(item, dict):
                continue
            cid = _as_int(item.get("id"))
            if cid is None:
                continue
            if cid in seen:
                continue
            seen.add(cid)
            out.append(item)
    return out


def _fetch_fullstats_map(
    cfg: Config, campaign_ids: list[int], begin_date: str, end_date: str
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for chunk in _iter_chunks(campaign_ids, 50):
        if not chunk:
            continue
        data = to_data(
            call_api(
                "promotion",
                "adv_v3_fullstats_get",
                cfg,
                ids=",".join(str(v) for v in chunk),
                begin_date=begin_date,
                end_date=end_date,
            )
        )
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            cid = _as_int(item.get("advert_id"))
            if cid is None:
                cid = _as_int(item.get("advertId"))
            if cid is None:
                continue
            out[cid] = item
    return out


def _fetch_budgets_map(cfg: Config, campaign_ids: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for cid in campaign_ids:
        data = to_data(call_api("promotion", "adv_v1_budget_get", cfg, id=cid))
        if isinstance(data, dict):
            out[cid] = data
    return out


def _fetch_keyword_stats_v1(
    cfg: Config, campaign_ids: list[int], dates: list[str]
) -> dict[str, Any]:
    try:
        from wildberries_sdk.promotion.models.v1_get_norm_query_stats_request import (
            V1GetNormQueryStatsRequest,
        )
    except Exception as exc:
        print_error("validation_error", f"wildberries-sdk model import failed: {exc}")
        raise typer.Exit(1)
    body = {"items": [{"id": int(cid), "dates": dates} for cid in campaign_ids]}
    try:
        req = V1GetNormQueryStatsRequest.from_dict(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid keyword stats request: {exc}")
        raise typer.Exit(1)
    data = to_data(
        call_api(
            "promotion", "adv_v1_normquery_stats_post", cfg, v1_get_norm_query_stats_request=req
        )
    )
    if not isinstance(data, dict):
        return {}
    return data


def _extract_keyword_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    items = data.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            advert_id = _as_int(item.get("advertId"))
            nm_id = _as_int(item.get("nmId"))
            if advert_id is None or nm_id is None:
                continue
            for daily in item.get("dailyStats") or []:
                if not isinstance(daily, dict):
                    continue
                stat = daily.get("stat")
                if not isinstance(stat, dict):
                    continue
                rows.append(
                    {
                        "advert_id": advert_id,
                        "nm_id": nm_id,
                        "date": daily.get("date"),
                        "norm_query": stat.get("normQuery") or stat.get("norm_query"),
                        "views": _as_num(stat.get("views")) or 0,
                        "clicks": _as_num(stat.get("clicks")) or 0,
                        "orders": _as_num(stat.get("orders")) or 0,
                        "atbs": _as_num(stat.get("atbs")) or 0,
                        "spend": _as_num(stat.get("spend")) or 0,
                        "cpc": _as_num(stat.get("cpc")),
                        "ctr": _as_num(stat.get("ctr")),
                        "cpm": _as_num(stat.get("cpm")),
                        "avg_pos": _as_num(stat.get("avgPos") or stat.get("avg_pos")),
                    }
                )
        return rows

    stats = data.get("stats")
    if isinstance(stats, list):
        for item in stats:
            if not isinstance(item, dict):
                continue
            advert_id = _as_int(item.get("advertId") or item.get("advert_id"))
            nm_id = _as_int(item.get("nmId") or item.get("nm_id"))
            if advert_id is None or nm_id is None:
                continue
            for stat in item.get("stats") or []:
                if not isinstance(stat, dict):
                    continue
                rows.append(
                    {
                        "advert_id": advert_id,
                        "nm_id": nm_id,
                        "date": None,
                        "norm_query": stat.get("normQuery") or stat.get("norm_query"),
                        "views": _as_num(stat.get("views")) or 0,
                        "clicks": _as_num(stat.get("clicks")) or 0,
                        "orders": _as_num(stat.get("orders")) or 0,
                        "atbs": _as_num(stat.get("atbs")) or 0,
                        "spend": _as_num(stat.get("spend")) or 0,
                        "cpc": _as_num(stat.get("cpc")),
                        "ctr": _as_num(stat.get("ctr")),
                        "cpm": _as_num(stat.get("cpm")),
                        "avg_pos": _as_num(stat.get("avgPos") or stat.get("avg_pos")),
                    }
                )
    return rows


def _aggregate_keyword_rows_by_nm(
    rows: list[dict[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        advert_id = _as_int(row.get("advert_id"))
        nm_id = _as_int(row.get("nm_id"))
        if advert_id is None or nm_id is None:
            continue
        key = (advert_id, nm_id)
        cur = grouped.get(key)
        if cur is None:
            cur = {
                "advert_id": advert_id,
                "nm_id": nm_id,
                "views": 0.0,
                "clicks": 0.0,
                "orders": 0.0,
                "atbs": 0.0,
                "spend_rub": 0.0,
                "query_rows": 0,
                "_avg_pos_weighted_sum": 0.0,
                "_avg_pos_weight": 0.0,
                "bad_queries": [],
            }
            grouped[key] = cur
        views = _as_num(row.get("views")) or 0.0
        clicks = _as_num(row.get("clicks")) or 0.0
        orders = _as_num(row.get("orders")) or 0.0
        atbs = _as_num(row.get("atbs")) or 0.0
        spend = _as_num(row.get("spend")) or 0.0
        cur["views"] += views
        cur["clicks"] += clicks
        cur["orders"] += orders
        cur["atbs"] += atbs
        cur["spend_rub"] += spend
        cur["query_rows"] += 1

        avg_pos = _as_num(row.get("avg_pos"))
        weight = views or clicks
        if avg_pos is not None and weight > 0:
            cur["_avg_pos_weighted_sum"] += avg_pos * weight
            cur["_avg_pos_weight"] += weight

        if clicks >= 10 and orders <= 0 and spend > 0:
            cur["bad_queries"].append(
                {
                    "query": row.get("norm_query"),
                    "clicks": int(clicks),
                    "spend_rub": round(spend, 2),
                }
            )

    for cur in grouped.values():
        views = cur["views"]
        clicks = cur["clicks"]
        orders = cur["orders"]
        spend = cur["spend_rub"]
        cur["views"] = int(views)
        cur["clicks"] = int(clicks)
        cur["orders"] = int(orders)
        cur["atbs"] = int(cur["atbs"])
        cur["spend_rub"] = round(spend, 2)
        cur["ctr"] = round((clicks / views) * 100, 2) if views > 0 else None
        cur["cpc_rub"] = round(spend / clicks, 2) if clicks > 0 else None
        cur["cpa_rub"] = round(spend / orders, 2) if orders > 0 else None
        weight = cur.pop("_avg_pos_weight", 0.0)
        weighted_sum = cur.pop("_avg_pos_weighted_sum", 0.0)
        cur["avg_pos"] = round(weighted_sum / weight, 2) if weight > 0 else None
        bad = sorted(
            (q for q in cur["bad_queries"] if isinstance(q, dict)),
            key=lambda q: (_as_num(q.get("spend_rub")) or 0, _as_num(q.get("clicks")) or 0),
            reverse=True,
        )
        cur["bad_queries"] = bad[:5]
    return grouped


def _fetch_min_bid_map(
    cfg: Config, adverts: list[dict[str, Any]]
) -> dict[tuple[int, int, str], int]:
    out: dict[tuple[int, int, str], int] = {}
    try:
        from wildberries_sdk.promotion.models.api_advert_v1_bids_min_post_request import (
            ApiAdvertV1BidsMinPostRequest,
        )
    except Exception:
        return out

    for advert in adverts:
        cid = _as_int(advert.get("id"))
        settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
        nm_settings_list = [x for x in (advert.get("nm_settings") or []) if isinstance(x, dict)]
        if cid is None or not nm_settings_list:
            continue
        payment_type = str(settings.get("payment_type") or "cpm")
        placement_types = _placement_types_for_min_bids(advert)
        nm_ids = [
            nm for nm in (_as_int(x.get("nm_id")) for x in nm_settings_list) if nm is not None
        ]
        for nm_chunk in _iter_chunks(nm_ids, 50):
            try:
                req = ApiAdvertV1BidsMinPostRequest.from_dict(
                    {
                        "advert_id": cid,
                        "nm_ids": nm_chunk,
                        "payment_type": payment_type,
                        "placement_types": placement_types,
                    }
                )
            except Exception:
                continue
            data = to_data(
                call_api(
                    "promotion",
                    "api_advert_v1_bids_min_post",
                    cfg,
                    api_advert_v1_bids_min_post_request=req,
                )
            )
            bids = data.get("bids") if isinstance(data, dict) else None
            if not isinstance(bids, list):
                continue
            for item in bids:
                if not isinstance(item, dict):
                    continue
                nm_id = _as_int(item.get("nm_id") or item.get("nmId"))
                if nm_id is None:
                    continue
                for bid in item.get("bids") or []:
                    if not isinstance(bid, dict):
                        continue
                    ptype = str(bid.get("type") or "")
                    value = _as_int(bid.get("value"))
                    if value is None or not ptype:
                        continue
                    normalized = "recommendations" if ptype == "recommendation" else ptype
                    out[(cid, nm_id, normalized)] = value
    return out


def _recommend_nm_bid(
    *,
    campaign_id: int,
    campaign_name: Optional[str],
    nm_id: int,
    placement: str,
    current_bid_kopecks: int,
    perf: dict[str, Any],
    target_cpa: Optional[float],
    min_clicks: int,
    kill_clicks: int,
    min_ctr: Optional[float],
    max_avg_pos: Optional[float],
    increase_pct: int,
    decrease_pct: int,
    strong_decrease_pct: int,
    min_orders_for_increase: int,
    bid_step: int,
    max_bid_kopecks: Optional[int],
    min_bid_floor_kopecks: Optional[int],
) -> Optional[dict[str, Any]]:
    clicks = int(_as_num(perf.get("clicks")) or 0)
    views = int(_as_num(perf.get("views")) or 0)
    orders = int(_as_num(perf.get("orders")) or 0)
    spend_rub = float(_as_num(perf.get("spend_rub")) or 0.0)
    ctr = _as_num(perf.get("ctr"))
    avg_pos = _as_num(perf.get("avg_pos"))
    cpa_rub = _as_num(perf.get("cpa_rub"))

    if clicks < min_clicks and views < max(1000, min_clicks * 30):
        return None

    action = "hold"
    delta_pct = 0
    reason = ""
    priority_score = 0.0

    if orders == 0 and clicks >= kill_clicks:
        action = "decrease"
        delta_pct = -abs(strong_decrease_pct)
        reason = f"0 orders after {clicks} clicks"
        priority_score = spend_rub + clicks
    elif (
        target_cpa is not None
        and orders > 0
        and cpa_rub is not None
        and cpa_rub > target_cpa * 1.15
    ):
        action = "decrease"
        delta_pct = -abs(decrease_pct)
        reason = f"CPA {cpa_rub:.2f} > target {target_cpa:.2f}"
        priority_score = spend_rub + max(0.0, cpa_rub - target_cpa)
    elif (
        min_ctr is not None
        and orders == 0
        and clicks >= min_clicks
        and ctr is not None
        and ctr < min_ctr
    ):
        action = "decrease"
        delta_pct = -abs(decrease_pct)
        reason = f"CTR {ctr:.2f}% < floor {min_ctr:.2f}%"
        priority_score = spend_rub + max(0.0, (min_ctr - ctr) * 10)
    elif orders >= min_orders_for_increase:
        good_by_cpa = target_cpa is None or (cpa_rub is not None and cpa_rub <= target_cpa * 0.85)
        weak_position = max_avg_pos is not None and avg_pos is not None and avg_pos > max_avg_pos
        if good_by_cpa and (weak_position or target_cpa is not None):
            action = "increase"
            delta_pct = abs(increase_pct)
            if target_cpa is not None and cpa_rub is not None:
                reason = f"CPA {cpa_rub:.2f} <= target {target_cpa:.2f}"
            else:
                reason = f"{orders} orders and avg_pos {avg_pos}"
            priority_score = orders * 10 + max(0.0, spend_rub / 10)

    if action == "hold":
        return None

    new_bid = int(round(current_bid_kopecks * (1 + (delta_pct / 100.0))))
    new_bid = _round_to_step(max(1, new_bid), max(1, bid_step))

    floor_applied = None
    if min_bid_floor_kopecks is not None:
        floor_applied = int(min_bid_floor_kopecks)
        if new_bid < floor_applied:
            new_bid = _round_to_step(floor_applied, max(1, bid_step))

    if max_bid_kopecks is not None and new_bid > max_bid_kopecks:
        new_bid = _round_to_step(max_bid_kopecks, max(1, bid_step))

    if new_bid == current_bid_kopecks:
        return None

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "nm_id": nm_id,
        "placement": placement,
        "action": action,
        "reason": reason,
        "priority_score": round(priority_score, 2),
        "current_bid_kopecks": current_bid_kopecks,
        "new_bid_kopecks": new_bid,
        "delta_kopecks": new_bid - current_bid_kopecks,
        "delta_pct": round(((new_bid / current_bid_kopecks) - 1) * 100, 2)
        if current_bid_kopecks
        else None,
        "min_bid_floor_kopecks": floor_applied,
        "perf": {
            "views": views,
            "clicks": clicks,
            "orders": orders,
            "spend_rub": round(spend_rub, 2),
            "ctr": ctr,
            "cpa_rub": cpa_rub,
            "avg_pos": avg_pos,
            "bad_queries": perf.get("bad_queries") or [],
        },
    }


def _build_bids_patch_payload(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    by_campaign: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in recommendations:
        cid = _as_int(item.get("campaign_id"))
        nm_id = _as_int(item.get("nm_id"))
        bid = _as_int(item.get("new_bid_kopecks"))
        placement = str(item.get("placement") or "")
        if cid is None or nm_id is None or bid is None or not placement:
            continue
        by_campaign[cid].append({"nm_id": nm_id, "bid_kopecks": bid, "placement": placement})
    payload_bids = [{"advert_id": cid, "nm_bids": nms} for cid, nms in sorted(by_campaign.items())]
    return {"bids": payload_bids}


def _apply_bids_patch(cfg: Config, payload: dict[str, Any]) -> list[Any]:
    if not payload.get("bids"):
        return []
    try:
        from wildberries_sdk.promotion.models.api_advert_v1_bids_patch_request import (
            ApiAdvertV1BidsPatchRequest,
        )
    except Exception as exc:
        print_error("validation_error", f"wildberries-sdk model import failed: {exc}")
        raise typer.Exit(1)

    results: list[Any] = []
    campaign_chunks = _iter_chunks(payload["bids"], 50)
    for chunk in campaign_chunks:
        # Also split large nm lists to keep each campaign body small and predictable.
        split_chunk: list[dict[str, Any]] = []
        for campaign in chunk:
            nm_bids = campaign.get("nm_bids") or []
            if not isinstance(nm_bids, list):
                continue
            for nm_chunk in _iter_chunks([x for x in nm_bids if isinstance(x, dict)], 50):
                split_chunk.append({"advert_id": campaign.get("advert_id"), "nm_bids": nm_chunk})
        if not split_chunk:
            continue
        req = ApiAdvertV1BidsPatchRequest.from_dict({"bids": split_chunk})
        result = to_data(
            call_api(
                "promotion",
                "api_advert_v1_bids_patch",
                cfg,
                api_advert_v1_bids_patch_request=req,
            )
        )
        results.append(result)
    return results


def _campaign_metrics(stat: dict[str, Any]) -> dict[str, Any]:
    views = int(_as_num(stat.get("views")) or 0)
    clicks = int(_as_num(stat.get("clicks")) or 0)
    orders = int(_as_num(stat.get("orders")) or 0)
    spend_rub = float(_as_num(stat.get("sum")) or 0.0)
    revenue_rub = float(_as_num(stat.get("sum_price")) or 0.0)
    return {
        "views": views,
        "clicks": clicks,
        "orders": orders,
        "spend_rub": round(spend_rub, 2),
        "revenue_rub": round(revenue_rub, 2),
        "ctr": round((clicks / views) * 100, 2) if views else None,
        "cpc_rub": round(spend_rub / clicks, 2) if clicks else None,
        "cpa_rub": round(spend_rub / orders, 2) if orders else None,
        "roas": round(revenue_rub / spend_rub, 2) if spend_rub > 0 else None,
        "acos": round((spend_rub / revenue_rub) * 100, 2) if revenue_rub > 0 else None,
    }


def _snapshot_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    spend = sum(float(_as_num(r.get("spend_rub")) or 0) for r in rows)
    revenue = sum(float(_as_num(r.get("revenue_rub")) or 0) for r in rows)
    clicks = sum(int(_as_num(r.get("clicks")) or 0) for r in rows)
    orders = sum(int(_as_num(r.get("orders")) or 0) for r in rows)
    active = sum(1 for r in rows if _as_int(r.get("status")) == 9)
    return {
        "campaigns": len(rows),
        "active_campaigns": active,
        "spend_rub": round(spend, 2),
        "revenue_rub": round(revenue, 2),
        "clicks": clicks,
        "orders": orders,
        "roas": round(revenue / spend, 2) if spend > 0 else None,
        "cpa_rub": round(spend / orders, 2) if orders > 0 else None,
    }


def _bids_plan_summary(recommendations: list[dict[str, Any]], *, apply: bool) -> dict[str, Any]:
    inc = sum(1 for r in recommendations if r.get("action") == "increase")
    dec = sum(1 for r in recommendations if r.get("action") == "decrease")
    return {
        "mode": "apply" if apply else "dry_run",
        "changes": len(recommendations),
        "increase": inc,
        "decrease": dec,
        "campaigns_affected": len(
            {
                _as_int(r.get("campaign_id"))
                for r in recommendations
                if _as_int(r.get("campaign_id")) is not None
            }
        ),
    }


def _choose_bid_placement(advert: dict[str, Any], placement: str) -> str:
    choice = placement.strip().lower()
    if choice != "auto":
        return choice
    if str(advert.get("bid_type") or "") == "unified":
        return "combined"
    settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    search_on = bool(placements.get("search"))
    rec_on = bool(placements.get("recommendations"))
    if search_on:
        return "search"
    if rec_on:
        return "recommendations"
    return "search"


def _placement_types_for_min_bids(advert: dict[str, Any]) -> list[str]:
    if str(advert.get("bid_type") or "") == "unified":
        return ["combined"]
    settings = advert.get("settings") if isinstance(advert.get("settings"), dict) else {}
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    out = []
    if placements.get("search"):
        out.append("search")
    if placements.get("recommendations"):
        out.append("recommendation")
    return out or ["search"]


def _current_nm_bid_kopecks(nm_settings: dict[str, Any], placement: str) -> Optional[int]:
    bids = nm_settings.get("bids_kopecks")
    if not isinstance(bids, dict):
        return None
    if placement == "combined":
        search = _as_int(bids.get("search"))
        rec = _as_int(bids.get("recommendations"))
        if search is None and rec is None:
            return None
        return max(v for v in [search, rec] if v is not None)
    if placement == "recommendations":
        return _as_int(bids.get("recommendations"))
    return _as_int(bids.get("search"))


def _round_to_step(value: int, step: int) -> int:
    if step <= 1:
        return int(value)
    return int(round(value / step) * step)


def _round_up(value: int, step: int) -> int:
    if step <= 1:
        return int(value)
    return ((int(value) + step - 1) // step) * step


def _as_num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:
        return None


def _as_int(value: Any) -> Optional[int]:
    num = _as_num(value)
    if num is None:
        return None
    return int(num)


def _is_int(value: Any) -> bool:
    return _as_int(value) is not None


def _safe_get(data: Any, dotted: str) -> Any:
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


if __name__ == "__main__":
    app()
