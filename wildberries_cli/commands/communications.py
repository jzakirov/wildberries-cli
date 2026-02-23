"""communications subcommand (feedbacks/questions)."""

from __future__ import annotations

import typer

from wildberries_cli.client import call_api
from wildberries_cli.config import Config
from wildberries_cli.output import emit, feedbacks_table, print_error, questions_table, read_text_arg
from wildberries_cli.serialize import to_data

app = typer.Typer(name="communications", help="Buyer communications APIs.", no_args_is_help=True)
feedbacks_app = typer.Typer(name="feedbacks", help="Feedbacks API.", no_args_is_help=True)
questions_app = typer.Typer(name="questions", help="Questions API.", no_args_is_help=True)
app.add_typer(feedbacks_app, name="feedbacks")
app.add_typer(questions_app, name="questions")


@feedbacks_app.command("list")
def feedbacks_list(
    ctx: typer.Context,
    answered: bool = typer.Option(..., "--answered/--unanswered", help="Filter by answered state"),
    take: int = typer.Option(100, "--take", min=1, max=5000, help="Number of feedbacks to return"),
    skip: int = typer.Option(0, "--skip", min=0, help="Offset"),
    nm_id: int | None = typer.Option(None, "--nm-id", help="WB nmID"),
    order: str | None = typer.Option(None, "--order", help="dateAsc or dateDesc"),
    date_from: int | None = typer.Option(None, "--date-from", help="Unix timestamp start"),
    date_to: int | None = typer.Option(None, "--date-to", help="Unix timestamp end"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {
        "is_answered": answered,
        "take": take,
        "skip": skip,
        "nm_id": nm_id,
        "order": order,
        "date_from": date_from,
        "date_to": date_to,
    }
    data = to_data(call_api("communications", "api_v1_feedbacks_get", cfg, **{k: v for k, v in kwargs.items() if v is not None}))
    emit(data, pretty=cfg.pretty, table_builder=feedbacks_table)


@feedbacks_app.command("get")
def feedbacks_get(ctx: typer.Context, feedback_id: str = typer.Argument(..., help="Feedback ID")) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("communications", "api_v1_feedback_get", cfg, id=feedback_id))
    emit(data, pretty=cfg.pretty)


@feedbacks_app.command("answer")
def feedbacks_answer(
    ctx: typer.Context,
    feedback_id: str = typer.Argument(..., help="Feedback ID"),
    text: str = typer.Option(..., "--text", help="Answer text or '-' for stdin"),
) -> None:
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.communications import ApiV1FeedbacksAnswerPostRequest

        req = ApiV1FeedbacksAnswerPostRequest(id=feedback_id, text=read_text_arg(text))
    except Exception as exc:
        print_error("validation_error", f"Invalid feedback answer payload: {exc}")
        raise typer.Exit(1)

    data = to_data(call_api("communications", "api_v1_feedbacks_answer_post", cfg, api_v1_feedbacks_answer_post_request=req))
    emit(data if data is not None else {"ok": True, "id": feedback_id}, pretty=cfg.pretty)


@questions_app.command("list")
def questions_list(
    ctx: typer.Context,
    answered: bool = typer.Option(..., "--answered/--unanswered", help="Filter by answered state"),
    take: int = typer.Option(100, "--take", min=1, max=10000, help="Number of questions to return"),
    skip: int = typer.Option(0, "--skip", min=0, help="Offset"),
    nm_id: int | None = typer.Option(None, "--nm-id", help="WB nmID"),
    order: str | None = typer.Option(None, "--order", help="dateAsc or dateDesc"),
    date_from: int | None = typer.Option(None, "--date-from", help="Unix timestamp start"),
    date_to: int | None = typer.Option(None, "--date-to", help="Unix timestamp end"),
) -> None:
    cfg: Config = ctx.obj
    kwargs = {
        "is_answered": answered,
        "take": take,
        "skip": skip,
        "nm_id": nm_id,
        "order": order,
        "date_from": date_from,
        "date_to": date_to,
    }
    data = to_data(call_api("communications", "api_v1_questions_get", cfg, **{k: v for k, v in kwargs.items() if v is not None}))
    emit(data, pretty=cfg.pretty, table_builder=questions_table)


@questions_app.command("get")
def questions_get(ctx: typer.Context, question_id: str = typer.Argument(..., help="Question ID")) -> None:
    cfg: Config = ctx.obj
    data = to_data(call_api("communications", "api_v1_question_get", cfg, id=question_id))
    emit(data, pretty=cfg.pretty)


@questions_app.command("answer")
def questions_answer(
    ctx: typer.Context,
    question_id: str = typer.Argument(..., help="Question ID"),
    text: str = typer.Option(..., "--text", help="Answer text or '-' for stdin"),
    state: str = typer.Option("wbRu", "--state", help="Question state (`wbRu` to publish answer, `none` to reject)")
) -> None:
    cfg: Config = ctx.obj
    try:
        from wildberries_sdk.communications import (
            ApiV1QuestionsPatchRequest,
            ApiV1QuestionsPatchRequestOneOf1,
            ApiV1QuestionsPatchRequestOneOf1Answer,
        )

        payload = ApiV1QuestionsPatchRequestOneOf1(
            id=question_id,
            answer=ApiV1QuestionsPatchRequestOneOf1Answer(text=read_text_arg(text)),
            state=state,
        )
        req = ApiV1QuestionsPatchRequest(actual_instance=payload)
    except Exception as exc:
        print_error("validation_error", f"Invalid question answer payload: {exc}")
        raise typer.Exit(1)

    data = to_data(call_api("communications", "api_v1_questions_patch", cfg, api_v1_questions_patch_request=req))
    emit(data, pretty=cfg.pretty)
