"""Tests for ProcessTicketUseCase with in-memory fakes."""

from __future__ import annotations

import pytest

from app.application.ports.analytics_repo import AnalyticsRepository
from app.application.ports.assignment_repo import AssignmentRepository
from app.application.ports.geocoder_port import GeocoderPort
from app.application.ports.llm_port import LLMPort
from app.application.ports.manager_repo import ManagerRepository
from app.application.ports.office_repo import OfficeRepository
from app.application.ports.round_robin_repo import RoundRobinRepository
from app.application.ports.ticket_repo import TicketRepository
from app.application.use_cases.process_ticket import ProcessTicketUseCase
from app.domain.entities.ai_analysis import AIAnalysis
from app.domain.entities.assignment import Assignment
from app.domain.entities.manager import Manager
from app.domain.entities.office import Office
from app.domain.entities.ticket import Ticket
from app.domain.value_objects.enums import (
    Language,
    Position,
    Segment,
    Sentiment,
    TicketType,
)
from app.domain.value_objects.geo_point import GeoPoint

# ─── In-memory fakes ────────────────────────────────────────────────


class FakeLLM(LLMPort):
    def __init__(self, ticket_type=TicketType.CONSULTATION, language=Language.RU):
        self._type = ticket_type
        self._lang = language

    async def analyze_ticket(self, description, attachments=None):
        return AIAnalysis(
            id=None, ticket_id=0, ticket_type=self._type,
            sentiment=Sentiment.NEUTRAL, priority_score=5,
            language=self._lang, summary="test",
        )


class FakeGeocoder(GeocoderPort):
    def __init__(self, result: GeoPoint | None = None):
        self._result = result

    async def geocode(self, address):
        return self._result


class FakeTicketRepo(TicketRepository):
    def __init__(self):
        self.tickets: dict[int, Ticket] = {}

    async def save(self, ticket):
        ticket.id = len(self.tickets) + 1
        self.tickets[ticket.id] = ticket
        return ticket

    async def get_by_id(self, ticket_id):
        return self.tickets.get(ticket_id)

    async def get_by_guid(self, guid):
        return next((t for t in self.tickets.values() if t.guid == guid), None)

    async def get_all(self):
        return list(self.tickets.values())

    async def get_unprocessed(self):
        return list(self.tickets.values())

    async def update(self, ticket):
        self.tickets[ticket.id] = ticket
        return ticket


class FakeManagerRepo(ManagerRepository):
    def __init__(self, managers: list[Manager]):
        self._managers = {m.id: m for m in managers}

    async def save(self, manager):
        return manager

    async def get_by_id(self, manager_id):
        return self._managers.get(manager_id)

    async def get_by_office(self, office_id):
        return [m for m in self._managers.values() if m.office_id == office_id]

    async def get_all(self):
        return list(self._managers.values())

    async def increment_load(self, manager_id):
        if manager_id in self._managers:
            self._managers[manager_id].current_load += 1

    async def get_by_name(self, name):
        return next((m for m in self._managers.values() if m.name == name), None)


class FakeOfficeRepo(OfficeRepository):
    def __init__(self, offices: list[Office]):
        self._offices = {o.id: o for o in offices}

    async def save(self, office):
        return office

    async def get_by_id(self, office_id):
        return self._offices.get(office_id)

    async def get_by_name(self, name):
        return next((o for o in self._offices.values() if o.name == name), None)

    async def get_all(self):
        return list(self._offices.values())


class FakeAssignmentRepo(AssignmentRepository):
    def __init__(self):
        self.assignments: list[Assignment] = []

    async def save(self, assignment):
        assignment.id = len(self.assignments) + 1
        self.assignments.append(assignment)
        return assignment

    async def get_by_ticket(self, ticket_id):
        return next((a for a in self.assignments if a.ticket_id == ticket_id), None)

    async def get_all(self):
        return list(self.assignments)


class FakeAnalyticsRepo(AnalyticsRepository):
    def __init__(self):
        self.records: list[AIAnalysis] = []

    async def save(self, analysis):
        analysis.id = len(self.records) + 1
        self.records.append(analysis)
        return analysis

    async def get_by_ticket(self, ticket_id):
        return next((r for r in self.records if r.ticket_id == ticket_id), None)

    async def get_all(self):
        return list(self.records)


class FakeRRRepo(RoundRobinRepository):
    def __init__(self):
        self._counters: dict[str, int] = {}

    async def get_counter(self, rr_key):
        return self._counters.get(rr_key, 0)

    async def increment_counter(self, rr_key):
        old = self._counters.get(rr_key, 0)
        self._counters[rr_key] = old + 1
        return old


# ─── Fixtures ────────────────────────────────────────────────────────


ALMATY_OFFICE = Office(
    id=1, name="Алматы ЦО", address="ул. Абая 1",
    location=GeoPoint(latitude=43.238949, longitude=76.945465),
)
ASTANA_OFFICE = Office(
    id=2, name="Астана ЦО", address="пр. Мангилик Ел 1",
    location=GeoPoint(latitude=51.128207, longitude=71.430411),
)


def _make_ticket(
    guid="t-1", segment=Segment.MASS, country="Казахстан",
    city="Алматы", location=None,
) -> Ticket:
    return Ticket(
        id=1, guid=guid, gender=None, birth_date=None,
        description="Тестовая заявка", attachments=None, segment=segment,
        country=country, region=None, city=city, street=None, building=None,
        client_location=location,
    )


def _make_use_case(
    llm=None, geocoder=None, managers=None, offices=None,
    assignment_repo=None, analytics_repo=None, rr_repo=None, ticket_repo=None,
) -> ProcessTicketUseCase:
    if managers is None:
        managers = [
            Manager(id=1, name="M1", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
            Manager(id=2, name="M2", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
        ]
    if offices is None:
        offices = [ALMATY_OFFICE, ASTANA_OFFICE]

    return ProcessTicketUseCase(
        llm=llm or FakeLLM(),
        geocoder=geocoder or FakeGeocoder(GeoPoint(latitude=43.24, longitude=76.95)),
        ticket_repo=ticket_repo or FakeTicketRepo(),
        manager_repo=FakeManagerRepo(managers),
        office_repo=FakeOfficeRepo(offices),
        assignment_repo=assignment_repo or FakeAssignmentRepo(),
        analytics_repo=analytics_repo or FakeAnalyticsRepo(),
        rr_repo=rr_repo or FakeRRRepo(),
    )


# ─── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_basic_assignment():
    """Mass/RU ticket near Almaty → assigned to a manager in Almaty office."""
    uc = _make_use_case()
    ticket = _make_ticket(location=GeoPoint(latitude=43.24, longitude=76.95))
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.assigned_office == "Алматы ЦО"
    assert result.assigned_manager in ("M1", "M2")


@pytest.mark.asyncio
async def test_vip_ticket_requires_vip_skill():
    """VIP ticket should only be assigned to a manager with VIP skill."""
    managers = [
        Manager(id=1, name="NoSkill", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
        Manager(id=2, name="VIPMgr", position=Position.SPECIALIST, office_id=1, skills={"VIP"}, current_load=0),
    ]
    uc = _make_use_case(managers=managers)
    ticket = _make_ticket(segment=Segment.VIP, location=GeoPoint(latitude=43.24, longitude=76.95))
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.assigned_manager == "VIPMgr"


@pytest.mark.asyncio
async def test_data_change_requires_chief_specialist():
    """Data change ticket → only Главный специалист."""
    managers = [
        Manager(id=1, name="Senior", position=Position.SENIOR_SPECIALIST, office_id=1, skills=set(), current_load=0),
        Manager(id=2, name="Chief", position=Position.CHIEF_SPECIALIST, office_id=1, skills=set(), current_load=0),
    ]
    uc = _make_use_case(
        llm=FakeLLM(ticket_type=TicketType.DATA_CHANGE),
        managers=managers,
    )
    ticket = _make_ticket(location=GeoPoint(latitude=43.24, longitude=76.95))
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.assigned_manager == "Chief"


@pytest.mark.asyncio
async def test_kz_language_requires_kz_skill():
    """Kazakh language ticket → manager must have KZ skill."""
    managers = [
        Manager(id=1, name="RuOnly", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
        Manager(id=2, name="KzMgr", position=Position.SPECIALIST, office_id=1, skills={"KZ"}, current_load=0),
    ]
    uc = _make_use_case(
        llm=FakeLLM(language=Language.KZ),
        managers=managers,
    )
    ticket = _make_ticket(location=GeoPoint(latitude=43.24, longitude=76.95))
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.assigned_manager == "KzMgr"


@pytest.mark.asyncio
async def test_fallback_for_abroad_ticket():
    """Abroad ticket → fallback 50/50 between Астана and Алматы."""
    uc = _make_use_case()
    ticket = _make_ticket(country="Россия", city="Москва")
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.fallback_used is True
    assert result.assigned_office in ("Алматы ЦО", "Астана ЦО")


@pytest.mark.asyncio
async def test_fallback_for_unknown_address():
    """Empty address → fallback 50/50."""
    uc = _make_use_case(geocoder=FakeGeocoder(result=None))
    ticket = _make_ticket(country=None, city=None)
    result = await uc.execute(ticket)
    assert result.error is None
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_round_robin_distributes():
    """Over 4 tickets, both managers should receive assignments."""
    assignment_repo = FakeAssignmentRepo()
    rr_repo = FakeRRRepo()
    managers = [
        Manager(id=1, name="M1", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
        Manager(id=2, name="M2", position=Position.SPECIALIST, office_id=1, skills=set(), current_load=0),
    ]
    uc = _make_use_case(managers=managers, assignment_repo=assignment_repo, rr_repo=rr_repo)

    assigned_names = set()
    for i in range(4):
        t = Ticket(
            id=i + 1, guid=f"t{i}", gender=None, birth_date=None,
            description="Тест", attachments=None, segment=Segment.MASS,
            country="Казахстан", region=None, city="Алматы", street=None, building=None,
            client_location=GeoPoint(latitude=43.24, longitude=76.95),
        )
        result = await uc.execute(t)
        assert result.error is None
        assigned_names.add(result.assigned_manager)

    # Both managers should get at least one ticket over 4 rounds
    assert "M1" in assigned_names
    assert "M2" in assigned_names


@pytest.mark.asyncio
async def test_no_eligible_managers_returns_error():
    """If no managers match, result should contain an error."""
    managers = [
        Manager(id=1, name="M1", position=Position.SPECIALIST, office_id=99, skills=set(), current_load=0),
    ]
    uc = _make_use_case(
        llm=FakeLLM(ticket_type=TicketType.DATA_CHANGE),
        managers=managers,
    )
    ticket = _make_ticket(location=GeoPoint(latitude=43.24, longitude=76.95))
    result = await uc.execute(ticket)
    assert result.error is not None
    assert "No eligible managers" in result.error


@pytest.mark.asyncio
async def test_geocoding_updates_ticket():
    """Ticket without location should be geocoded and updated."""
    ticket_repo = FakeTicketRepo()
    geo_point = GeoPoint(latitude=43.24, longitude=76.95)
    uc = _make_use_case(
        geocoder=FakeGeocoder(result=geo_point),
        ticket_repo=ticket_repo,
    )
    ticket = _make_ticket(country="Казахстан", city="Алматы")
    result = await uc.execute(ticket)
    assert result.error is None
    # Ticket should have been updated with geocoded location
    assert ticket.client_location == geo_point


@pytest.mark.asyncio
async def test_analytics_persisted():
    """AI analysis should be saved to analytics repo."""
    analytics = FakeAnalyticsRepo()
    uc = _make_use_case(analytics_repo=analytics)
    ticket = _make_ticket(location=GeoPoint(latitude=43.24, longitude=76.95))
    await uc.execute(ticket)
    assert len(analytics.records) == 1
    assert analytics.records[0].ticket_id == ticket.id
