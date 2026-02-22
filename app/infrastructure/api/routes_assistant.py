"""AI Assistant endpoint — Star Task.

Accepts a user question, gathers fresh DB statistics,
sends everything to OpenAI, and returns a text answer
with optional chart data for dynamic visualization.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore

from app.adapters.persistence.database import get_session
from app.adapters.persistence.models import (
    AssignmentModel,
    ManagerModel,
    OfficeModel,
    TicketAnalyticsModel,
    TicketModel,
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["assistant"])

# ── Request / Response schemas ──────────────────────────────────────

class AssistantRequest(BaseModel):
    question: str


class ChartItem(BaseModel):
    name: str
    value: int | float


class ChartPayload(BaseModel):
    type: str  # "bar" | "pie"
    title: str
    data: list[ChartItem]


class AssistantResponse(BaseModel):
    answer: str
    chart: ChartPayload | None = None


# ── Helpers ─────────────────────────────────────────────────────────

async def _gather_db_context(session: AsyncSession) -> str:
    """Collect dashboard-level statistics into a text block for the LLM."""

    total_tickets = (
        await session.execute(select(func.count(TicketModel.id)))
    ).scalar() or 0

    processed = (
        await session.execute(select(func.count(TicketAnalyticsModel.id)))
    ).scalar() or 0

    assigned = (
        await session.execute(select(func.count(AssignmentModel.id)))
    ).scalar() or 0

    # By ticket type
    type_rows = (
        await session.execute(
            select(
                TicketAnalyticsModel.ticket_type,
                func.count(TicketAnalyticsModel.id),
            ).group_by(TicketAnalyticsModel.ticket_type)
        )
    ).all()

    # By sentiment
    sentiment_rows = (
        await session.execute(
            select(
                TicketAnalyticsModel.sentiment,
                func.count(TicketAnalyticsModel.id),
            ).group_by(TicketAnalyticsModel.sentiment)
        )
    ).all()

    # By language
    lang_rows = (
        await session.execute(
            select(
                TicketAnalyticsModel.language,
                func.count(TicketAnalyticsModel.id),
            ).group_by(TicketAnalyticsModel.language)
        )
    ).all()

    # By segment
    seg_rows = (
        await session.execute(
            select(TicketModel.segment, func.count(TicketModel.id)).group_by(
                TicketModel.segment
            )
        )
    ).all()

    # By office
    office_rows = (
        await session.execute(
            select(
                OfficeModel.name,
                func.count(AssignmentModel.id),
            )
            .join(AssignmentModel, OfficeModel.id == AssignmentModel.office_id)
            .group_by(OfficeModel.name)
        )
    ).all()

    # Manager loads (top 20)
    manager_rows = (
        await session.execute(
            select(
                ManagerModel.name,
                ManagerModel.position,
                ManagerModel.current_load,
                OfficeModel.name.label("office_name"),
            )
            .join(OfficeModel, ManagerModel.office_id == OfficeModel.id)
            .order_by(ManagerModel.current_load.desc())
            .limit(20)
        )
    ).all()

    # Fallback usage
    fallback_count = (
        await session.execute(
            select(func.count(AssignmentModel.id)).where(
                AssignmentModel.fallback_used.is_(True)
            )
        )
    ).scalar() or 0

    # Average priority
    avg_priority = (
        await session.execute(
            select(func.avg(TicketAnalyticsModel.priority_score))
        )
    ).scalar()

    lines = [
        "=== FIRE Dashboard Data ===",
        f"Total tickets: {total_tickets}",
        f"Processed: {processed}",
        f"Assigned: {assigned}",
        f"Unprocessed: {total_tickets - processed}",
        f"Fallback assignments: {fallback_count}",
        f"Average priority score: {round(avg_priority, 1) if avg_priority else 'N/A'}",
        "",
        "By ticket type:",
        *[f"  {row[0]}: {row[1]}" for row in type_rows],
        "",
        "By sentiment:",
        *[f"  {row[0]}: {row[1]}" for row in sentiment_rows],
        "",
        "By language:",
        *[f"  {row[0]}: {row[1]}" for row in lang_rows],
        "",
        "By segment:",
        *[f"  {row[0]}: {row[1]}" for row in seg_rows],
        "",
        "By office (assignments):",
        *[f"  {row[0]}: {row[1]}" for row in office_rows],
        "",
        "Manager loads (top 20):",
        *[f"  {row[0]} ({row[1]}, {row[3]}): load={row[2]}" for row in manager_rows],
    ]

    return "\n".join(lines)


ASSISTANT_SYSTEM_PROMPT = """\
You are the AI assistant for the FIRE (Freedom Intelligent Routing Engine) dashboard.
You help managers and analysts understand ticket data through natural-language questions.

You will receive the current database statistics as context, plus a user question.

RESPONSE FORMAT — return ONLY valid JSON with these fields:
{
  "answer": "Your helpful answer in the same language as the question.",
  "chart": null  OR  {
    "type": "bar" or "pie",
    "title": "Chart title",
    "data": [{"name": "Label", "value": 123}, ...]
  }
}

RULES:
- Answer in the SAME language as the user's question (Russian/Kazakh/English).
- If the question is about a distribution or comparison, include a "chart" with appropriate data.
- For yes/no or simple number questions, set "chart" to null.
- Keep answers concise but informative (2-4 sentences).
- If the data doesn't contain enough info, say so honestly.
- Return ONLY valid JSON, no markdown, no extra text.
"""


# ── Route ───────────────────────────────────────────────────────────

@router.post("/assistant", response_model=AssistantResponse)
async def ask_assistant(
    req: AssistantRequest,
    session: AsyncSession = Depends(get_session),
):
    """Handle a natural-language question about the dashboard data."""

    # 1) Gather live data
    db_context = await _gather_db_context(session)

    # 2) Build messages
    user_content = f"Dashboard data:\n{db_context}\n\nUser question: {req.question}"

    # 3) Call OpenAI
    if AsyncOpenAI is None or not (settings.openai_api_key or "").strip():
        return AssistantResponse(
            answer="AI assistant is not available — OpenAI API key is not configured.",
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)

        answer = parsed.get("answer", "Не удалось получить ответ.")
        chart_data = parsed.get("chart")

        chart = None
        if chart_data and isinstance(chart_data, dict):
            chart = ChartPayload(
                type=chart_data.get("type", "bar"),
                title=chart_data.get("title", ""),
                data=[
                    ChartItem(name=item["name"], value=item["value"])
                    for item in chart_data.get("data", [])
                    if isinstance(item, dict) and "name" in item and "value" in item
                ],
            )
            if not chart.data:
                chart = None

        return AssistantResponse(answer=answer, chart=chart)

    except json.JSONDecodeError:
        logger.exception("Failed to parse assistant LLM response as JSON")
        return AssistantResponse(
            answer="Произошла ошибка при обработке ответа AI. Попробуйте переформулировать вопрос.",
        )
    except Exception:
        logger.exception("Assistant LLM call failed")
        return AssistantResponse(
            answer="Произошла ошибка при обращении к AI. Попробуйте позже.",
        )
