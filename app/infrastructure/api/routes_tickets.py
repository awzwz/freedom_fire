"""Ticket endpoints — CRUD + detail view."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.adapters.persistence.database import get_session
from app.adapters.persistence.models import (
    AssignmentModel,
    TicketModel,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
async def list_tickets(session: AsyncSession = Depends(get_session)):
    """List all tickets with analytics and assignment info."""
    result = await session.execute(
        select(TicketModel)
        .options(
            joinedload(TicketModel.analytics),
            joinedload(TicketModel.assignment).joinedload(AssignmentModel.manager),
            joinedload(TicketModel.assignment).joinedload(AssignmentModel.office),
        )
        .order_by(TicketModel.id)
    )
    tickets = result.unique().scalars().all()

    return {
        "total": len(tickets),
        "tickets": [_serialize_ticket(t) for t in tickets],
    }


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single ticket with full details."""
    result = await session.execute(
        select(TicketModel)
        .options(
            joinedload(TicketModel.analytics),
            joinedload(TicketModel.assignment).joinedload(AssignmentModel.manager),
            joinedload(TicketModel.assignment).joinedload(AssignmentModel.office),
        )
        .where(TicketModel.id == ticket_id)
    )
    ticket = result.unique().scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _serialize_ticket(ticket)


def _serialize_ticket(t: TicketModel) -> dict:
    """Convert a TicketModel (with loaded relationships) to an API response dict."""
    data = {
        "id": t.id,
        "guid": t.guid,
        "gender": t.gender,
        "birth_date": str(t.birth_date) if t.birth_date else None,
        "description": t.description,
        "attachments": t.attachments,
        "segment": t.segment,
        "country": t.country,
        "region": t.region,
        "city": t.city,
        "street": t.street,
        "building": t.building,
        "client_lat": t.client_lat,
        "client_lon": t.client_lon,
        "geo_status": t.geo_status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }

    # Analytics
    if t.analytics:
        a = t.analytics
        data["analytics"] = {
            "ticket_type": a.ticket_type,
            "sentiment": a.sentiment,
            "priority_score": a.priority_score,
            "language": a.language,
            "summary": a.summary,
            "llm_model": a.llm_model,
        }
    else:
        data["analytics"] = None

    # Assignment
    if t.assignment:
        asgn = t.assignment
        data["assignment"] = {
            "manager_name": asgn.manager.name if asgn.manager else None,
            "manager_id": asgn.manager_id,
            "office_name": asgn.office.name if asgn.office else None,
            "office_id": asgn.office_id,
            "distance_km": asgn.distance_km,
            "fallback_used": asgn.fallback_used,
            "assignment_reason": asgn.assignment_reason,
        }
    else:
        data["assignment"] = None

    return data
