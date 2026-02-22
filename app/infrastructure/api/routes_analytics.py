"""Analytics endpoints — dashboard summary + manager load."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.database import get_session
from app.adapters.persistence.models import (
    AssignmentModel,
    ManagerModel,
    OfficeModel,
    TicketAnalyticsModel,
    TicketModel,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(session: AsyncSession = Depends(get_session)):
    """Aggregate stats for the dashboard."""
    # Total tickets
    total_tickets = (
        await session.execute(select(func.count(TicketModel.id)))
    ).scalar() or 0

    # Processed (have analytics)
    processed = (
        await session.execute(select(func.count(TicketAnalyticsModel.id)))
    ).scalar() or 0

    # Assigned
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
    by_type = {row[0]: row[1] for row in type_rows}

    # By sentiment
    sentiment_rows = (
        await session.execute(
            select(
                TicketAnalyticsModel.sentiment,
                func.count(TicketAnalyticsModel.id),
            ).group_by(TicketAnalyticsModel.sentiment)
        )
    ).all()
    by_sentiment = {row[0]: row[1] for row in sentiment_rows}

    # By language
    lang_rows = (
        await session.execute(
            select(
                TicketAnalyticsModel.language,
                func.count(TicketAnalyticsModel.id),
            ).group_by(TicketAnalyticsModel.language)
        )
    ).all()
    by_language = {row[0]: row[1] for row in lang_rows}

    # By segment
    seg_rows = (
        await session.execute(
            select(TicketModel.segment, func.count(TicketModel.id)).group_by(
                TicketModel.segment
            )
        )
    ).all()
    by_segment = {row[0]: row[1] for row in seg_rows}

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
    by_office = {row[0]: row[1] for row in office_rows}

    # Fallback usage
    fallback_count = (
        await session.execute(
            select(func.count(AssignmentModel.id)).where(
                AssignmentModel.fallback_used.is_(True)
            )
        )
    ).scalar() or 0

    return {
        "total_tickets": total_tickets,
        "processed": processed,
        "assigned": assigned,
        "unprocessed": total_tickets - processed,
        "by_type": by_type,
        "by_sentiment": by_sentiment,
        "by_language": by_language,
        "by_segment": by_segment,
        "by_office": by_office,
        "fallback_count": fallback_count,
    }


@router.get("/managers")
async def manager_load(session: AsyncSession = Depends(get_session)):
    """Manager load distribution."""
    result = await session.execute(
        select(
            ManagerModel.id,
            ManagerModel.name,
            ManagerModel.position,
            ManagerModel.current_load,
            OfficeModel.name.label("office_name"),
        )
        .join(OfficeModel, ManagerModel.office_id == OfficeModel.id)
        .order_by(ManagerModel.current_load.desc())
    )
    managers = result.all()

    return {
        "total_managers": len(managers),
        "managers": [
            {
                "id": m.id,
                "name": m.name,
                "position": m.position,
                "current_load": m.current_load,
                "office_name": m.office_name,
            }
            for m in managers
        ],
    }
