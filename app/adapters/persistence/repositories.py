"""SQLAlchemy repository implementations."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.models import (
    AssignmentModel,
    ManagerModel,
    OfficeModel,
    RoundRobinStateModel,
    TicketAnalyticsModel,
    TicketModel,
)
from app.application.ports.analytics_repo import AnalyticsRepository
from app.application.ports.assignment_repo import AssignmentRepository
from app.application.ports.manager_repo import ManagerRepository
from app.application.ports.office_repo import OfficeRepository
from app.application.ports.round_robin_repo import RoundRobinRepository
from app.application.ports.ticket_repo import TicketRepository
from app.domain.entities.ai_analysis import AIAnalysis
from app.domain.entities.assignment import Assignment
from app.domain.entities.manager import Manager
from app.domain.entities.office import Office
from app.domain.entities.ticket import Ticket
from app.domain.value_objects.enums import (
    GeoStatus,
    Language,
    Position,
    Segment,
    Sentiment,
    TicketType,
)
from app.domain.value_objects.geo_point import GeoPoint

# ─── Mappers ─────────────────────────────────────────────────────────


def _office_to_domain(m: OfficeModel) -> Office:
    location = None
    if m.latitude is not None and m.longitude is not None:
        location = GeoPoint(latitude=m.latitude, longitude=m.longitude)
    return Office(id=m.id, name=m.name, address=m.address, location=location)


def _manager_to_domain(m: ManagerModel) -> Manager:
    return Manager(
        id=m.id,
        name=m.name,
        position=Position(m.position),
        office_id=m.office_id,
        skills=set(m.skills) if m.skills else set(),
        current_load=m.current_load,
    )


def _ticket_to_domain(m: TicketModel) -> Ticket:
    location = None
    if m.client_lat is not None and m.client_lon is not None:
        location = GeoPoint(latitude=m.client_lat, longitude=m.client_lon)
    return Ticket(
        id=m.id,
        guid=m.guid,
        gender=m.gender,
        birth_date=m.birth_date,
        description=m.description,
        attachments=m.attachments,
        segment=Segment(m.segment),
        country=m.country,
        region=m.region,
        city=m.city,
        street=m.street,
        building=m.building,
        client_location=location,
        geo_status=GeoStatus(m.geo_status),
    )


def _analytics_to_domain(m: TicketAnalyticsModel) -> AIAnalysis:
    return AIAnalysis(
        id=m.id,
        ticket_id=m.ticket_id,
        ticket_type=TicketType(m.ticket_type),
        sentiment=Sentiment(m.sentiment),
        priority_score=m.priority_score,
        language=Language(m.language),
        summary=m.summary,
        llm_model=m.llm_model,
    )


def _assignment_to_domain(m: AssignmentModel) -> Assignment:
    return Assignment(
        id=m.id,
        ticket_id=m.ticket_id,
        manager_id=m.manager_id,
        office_id=m.office_id,
        distance_km=m.distance_km,
        assignment_reason=m.assignment_reason,
        fallback_used=m.fallback_used,
    )


# ─── Repositories ────────────────────────────────────────────────────


class SqlTicketRepository(TicketRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, ticket: Ticket) -> Ticket:
        m = TicketModel(
            guid=ticket.guid,
            gender=ticket.gender,
            birth_date=ticket.birth_date,
            description=ticket.description,
            attachments=ticket.attachments,
            segment=ticket.segment.value,
            country=ticket.country,
            region=ticket.region,
            city=ticket.city,
            street=ticket.street,
            building=ticket.building,
            client_lat=ticket.client_location.latitude if ticket.client_location else None,
            client_lon=ticket.client_location.longitude if ticket.client_location else None,
            geo_status=ticket.geo_status.value,
        )
        self._s.add(m)
        await self._s.flush()
        ticket.id = m.id
        return ticket

    async def get_by_id(self, ticket_id: int) -> Ticket | None:
        m = await self._s.get(TicketModel, ticket_id)
        return _ticket_to_domain(m) if m else None

    async def get_by_guid(self, guid: str) -> Ticket | None:
        result = await self._s.execute(select(TicketModel).where(TicketModel.guid == guid))
        m = result.scalar_one_or_none()
        return _ticket_to_domain(m) if m else None

    async def get_all(self) -> list[Ticket]:
        result = await self._s.execute(select(TicketModel).order_by(TicketModel.id))
        return [_ticket_to_domain(m) for m in result.scalars()]

    async def get_unprocessed(self) -> list[Ticket]:
        result = await self._s.execute(
            select(TicketModel)
            .outerjoin(TicketAnalyticsModel)
            .where(TicketAnalyticsModel.id.is_(None))
            .order_by(TicketModel.id)
        )
        return [_ticket_to_domain(m) for m in result.scalars()]

    async def update(self, ticket: Ticket) -> Ticket:
        await self._s.execute(
            update(TicketModel)
            .where(TicketModel.id == ticket.id)
            .values(
                client_lat=ticket.client_location.latitude if ticket.client_location else None,
                client_lon=ticket.client_location.longitude if ticket.client_location else None,
                geo_status=ticket.geo_status.value,
            )
        )
        await self._s.flush()
        return ticket


class SqlManagerRepository(ManagerRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, manager: Manager) -> Manager:
        m = ManagerModel(
            name=manager.name,
            position=manager.position.value,
            office_id=manager.office_id,
            skills=sorted(manager.skills),
            current_load=manager.current_load,
        )
        self._s.add(m)
        await self._s.flush()
        manager.id = m.id
        return manager

    async def get_by_id(self, manager_id: int) -> Manager | None:
        m = await self._s.get(ManagerModel, manager_id)
        return _manager_to_domain(m) if m else None

    async def get_by_office(self, office_id: int) -> list[Manager]:
        result = await self._s.execute(
            select(ManagerModel).where(ManagerModel.office_id == office_id)
        )
        return [_manager_to_domain(m) for m in result.scalars()]

    async def get_all(self) -> list[Manager]:
        result = await self._s.execute(select(ManagerModel).order_by(ManagerModel.id))
        return [_manager_to_domain(m) for m in result.scalars()]

    async def increment_load(self, manager_id: int) -> None:
        await self._s.execute(
            update(ManagerModel)
            .where(ManagerModel.id == manager_id)
            .values(current_load=ManagerModel.current_load + 1)
        )
        await self._s.flush()

    async def get_by_name(self, name: str) -> Manager | None:
        result = await self._s.execute(
            select(ManagerModel).where(ManagerModel.name == name)
        )
        m = result.scalar_one_or_none()
        return _manager_to_domain(m) if m else None


class SqlOfficeRepository(OfficeRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, office: Office) -> Office:
        m = OfficeModel(
            name=office.name,
            address=office.address,
            latitude=office.location.latitude if office.location else None,
            longitude=office.location.longitude if office.location else None,
        )
        self._s.add(m)
        await self._s.flush()
        office.id = m.id
        return office

    async def get_by_id(self, office_id: int) -> Office | None:
        m = await self._s.get(OfficeModel, office_id)
        return _office_to_domain(m) if m else None

    async def get_by_name(self, name: str) -> Office | None:
        result = await self._s.execute(
            select(OfficeModel).where(OfficeModel.name == name)
        )
        m = result.scalar_one_or_none()
        return _office_to_domain(m) if m else None

    async def get_all(self) -> list[Office]:
        result = await self._s.execute(select(OfficeModel).order_by(OfficeModel.id))
        return [_office_to_domain(m) for m in result.scalars()]


class SqlAssignmentRepository(AssignmentRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, assignment: Assignment) -> Assignment:
        m = AssignmentModel(
            ticket_id=assignment.ticket_id,
            manager_id=assignment.manager_id,
            office_id=assignment.office_id,
            distance_km=assignment.distance_km,
            assignment_reason=assignment.assignment_reason,
            fallback_used=assignment.fallback_used,
        )
        self._s.add(m)
        await self._s.flush()
        assignment.id = m.id
        return assignment

    async def get_by_ticket(self, ticket_id: int) -> Assignment | None:
        result = await self._s.execute(
            select(AssignmentModel).where(AssignmentModel.ticket_id == ticket_id)
        )
        m = result.scalar_one_or_none()
        return _assignment_to_domain(m) if m else None

    async def get_all(self) -> list[Assignment]:
        result = await self._s.execute(select(AssignmentModel).order_by(AssignmentModel.id))
        return [_assignment_to_domain(m) for m in result.scalars()]


class SqlAnalyticsRepository(AnalyticsRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, analysis: AIAnalysis) -> AIAnalysis:
        m = TicketAnalyticsModel(
            ticket_id=analysis.ticket_id,
            ticket_type=analysis.ticket_type.value,
            sentiment=analysis.sentiment.value,
            priority_score=analysis.priority_score,
            language=analysis.language.value,
            summary=analysis.summary,
            llm_model=analysis.llm_model,
        )
        self._s.add(m)
        await self._s.flush()
        analysis.id = m.id
        return analysis

    async def get_by_ticket(self, ticket_id: int) -> AIAnalysis | None:
        result = await self._s.execute(
            select(TicketAnalyticsModel).where(
                TicketAnalyticsModel.ticket_id == ticket_id
            )
        )
        m = result.scalar_one_or_none()
        return _analytics_to_domain(m) if m else None

    async def get_all(self) -> list[AIAnalysis]:
        result = await self._s.execute(
            select(TicketAnalyticsModel).order_by(TicketAnalyticsModel.id)
        )
        return [_analytics_to_domain(m) for m in result.scalars()]


class SqlRoundRobinRepository(RoundRobinRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def get_counter(self, rr_key: str) -> int:
        result = await self._s.execute(
            select(RoundRobinStateModel).where(
                RoundRobinStateModel.rr_key == rr_key
            )
        )
        m = result.scalar_one_or_none()
        if m is None:
            m = RoundRobinStateModel(rr_key=rr_key, counter=0)
            self._s.add(m)
            await self._s.flush()
        return m.counter

    async def increment_counter(self, rr_key: str) -> int:
        result = await self._s.execute(
            select(RoundRobinStateModel)
            .where(RoundRobinStateModel.rr_key == rr_key)
            .with_for_update()
        )
        m = result.scalar_one_or_none()
        if m is None:
            m = RoundRobinStateModel(rr_key=rr_key, counter=1)
            self._s.add(m)
            await self._s.flush()
            return 0
        old_value = m.counter
        m.counter += 1
        await self._s.flush()
        return old_value
