"""Output helpers: JSON, errors, and optional Rich tables."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Optional

from rich import box
from rich.console import Console
from rich.table import Table

err_console = Console(stderr=True)
out_console = Console()


TableBuilder = Callable[[Any], Optional[Table]]


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def print_error(
    error_type: str,
    message: str,
    status_code: Optional[int] = None,
    detail: Optional[Any] = None,
) -> None:
    payload: dict[str, Any] = {"type": error_type, "message": message}
    if status_code is not None:
        payload["status_code"] = status_code
    if detail is not None:
        payload["detail"] = detail
    err_console.print_json(json.dumps({"error": payload}, ensure_ascii=False))


def emit(data: Any, pretty: bool = False, table_builder: Optional[TableBuilder] = None) -> None:
    if pretty:
        table = table_builder(data) if table_builder else None
        if table is not None:
            out_console.print(table)
            return
        out_console.print_json(json.dumps(data, ensure_ascii=False))
        return
    print_json(data)


def read_text_arg(value: str) -> str:
    if value == "-":
        if sys.stdin.isatty():
            err_console.print("[dim]Reading from stdin (Ctrl+D to finish):[/dim]")
        return sys.stdin.read()
    return value


def simple_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], title: Optional[str] = None) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    for header, _ in columns:
        table.add_column(header)
    for row in rows:
        table.add_row(*[_cell(_resolve(row, key)) for _, key in columns])
    return table


def feedbacks_table(data: Any) -> Optional[Table]:
    feedbacks = _extract_feedbacks(data)
    if feedbacks is None:
        return None
    rows = []
    for item in feedbacks:
        rows.append(
            {
                "id": item.get("id"),
                "nmId": item.get("nmId") or _resolve(item, "productDetails.nmId"),
                "created": item.get("createdDate") or item.get("createdAt"),
                "text": item.get("text"),
                "answer": _resolve(item, "answer.text") if isinstance(item.get("answer"), dict) else item.get("answer"),
            }
        )
    return simple_table(rows, [("ID", "id"), ("nmID", "nmId"), ("Created", "created"), ("Text", "text"), ("Answer", "answer")], title="Feedbacks")


def questions_table(data: Any) -> Optional[Table]:
    questions = _extract_questions(data)
    if questions is None:
        return None
    rows = []
    for item in questions:
        rows.append(
            {
                "id": item.get("id"),
                "nmId": item.get("nmId") or _resolve(item, "productDetails.nmId"),
                "created": item.get("createdDate") or item.get("createdAt"),
                "state": item.get("state"),
                "text": item.get("text"),
            }
        )
    return simple_table(rows, [("ID", "id"), ("nmID", "nmId"), ("Created", "created"), ("State", "state"), ("Text", "text")], title="Questions")


def reports_table(data: Any) -> Optional[Table]:
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    candidates = [
        ("nmId", "nmId"),
        ("barcode", "barcode"),
        ("subject", "subject"),
        ("brand", "brand"),
        ("lastChangeDate", "lastChangeDate"),
        ("date", "date"),
        ("supplierArticle", "supplierArticle"),
        ("techSize", "techSize"),
        ("totalPrice", "totalPrice"),
        ("finishedPrice", "finishedPrice"),
        ("quantity", "quantity"),
    ]
    cols = [(h, k) for h, k in candidates if any(k in row for row in data[:20])]
    if not cols:
        cols = [(k, k) for k in list(first.keys())[:6]]
    return simple_table(data[:100], cols)


def fbs_orders_table(data: Any) -> Optional[Table]:
    rows = None
    if isinstance(data, dict):
        for key in ("orders", "data"):
            val = data.get(key)
            if isinstance(val, list):
                rows = val
                break
            if isinstance(val, dict) and isinstance(val.get("orders"), list):
                rows = val.get("orders")
                break
    if not isinstance(rows, list):
        return None
    display = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        display.append(
            {
                "id": item.get("id") or item.get("orderId"),
                "created": item.get("createdAt") or item.get("createdDate"),
                "status": item.get("wbStatus") or item.get("status"),
                "nmId": item.get("nmId"),
                "skus": item.get("skus") or item.get("chrtId"),
            }
        )
    return simple_table(display, [("ID", "id"), ("Created", "created"), ("Status", "status"), ("nmID", "nmId"), ("SKU", "skus")], title="FBS Orders")


def _extract_feedbacks(data: Any) -> Optional[list[dict[str, Any]]]:
    if not isinstance(data, dict):
        return None
    for path in ("data.feedbacks", "feedbacks"):
        val = _resolve(data, path)
        if isinstance(val, list):
            return [v for v in val if isinstance(v, dict)]
    return None


def _extract_questions(data: Any) -> Optional[list[dict[str, Any]]]:
    if not isinstance(data, dict):
        return None
    for path in ("data.questions", "questions"):
        val = _resolve(data, path)
        if isinstance(val, list):
            return [v for v in val if isinstance(v, dict)]
    return None


def _resolve(data: Any, dotted: str) -> Any:
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text if len(text) <= 80 else text[:77] + "..."
