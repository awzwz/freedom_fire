"""Tests for domain entities."""

from datetime import date

from app.domain.entities.manager import Manager
from app.domain.entities.ticket import Ticket
from app.domain.value_objects.enums import Position, Segment


def test_ticket_build_address_full():
    t = Ticket(
        id=1, guid="test", gender="М", birth_date=date(1990, 1, 1),
        description="test", attachments=None, segment=Segment.MASS,
        country="Казахстан", region="Алматинская", city="Алматы",
        street="ул. Абая", building="10",
    )
    addr = t.build_address_string()
    assert addr == "Казахстан, Алматинская, Алматы, ул. Абая, 10"


def test_ticket_build_address_partial():
    t = Ticket(
        id=1, guid="test", gender=None, birth_date=None,
        description=None, attachments=None, segment=Segment.MASS,
        country="Казахстан", region=None, city="Актау",
        street=None, building=None,
    )
    addr = t.build_address_string()
    assert addr == "Казахстан, Актау"


def test_ticket_build_address_empty():
    t = Ticket(
        id=1, guid="test", gender=None, birth_date=None,
        description=None, attachments=None, segment=Segment.MASS,
        country=None, region=None, city=None, street=None, building=None,
    )
    assert t.build_address_string() is None


def test_ticket_is_domestic():
    t = Ticket(
        id=1, guid="test", gender=None, birth_date=None,
        description=None, attachments=None, segment=Segment.MASS,
        country="Казахстан", region=None, city=None, street=None, building=None,
    )
    assert t.is_domestic() is True


def test_ticket_is_not_domestic_empty():
    t = Ticket(
        id=1, guid="test", gender=None, birth_date=None,
        description=None, attachments=None, segment=Segment.MASS,
        country=None, region=None, city=None, street=None, building=None,
    )
    assert t.is_domestic() is False


def test_ticket_requires_vip_handling():
    for seg in (Segment.VIP, Segment.PRIORITY):
        t = Ticket(
            id=1, guid="test", gender=None, birth_date=None,
            description=None, attachments=None, segment=seg,
            country=None, region=None, city=None, street=None, building=None,
        )
        assert t.requires_vip_handling() is True

    t_mass = Ticket(
        id=1, guid="test", gender=None, birth_date=None,
        description=None, attachments=None, segment=Segment.MASS,
        country=None, region=None, city=None, street=None, building=None,
    )
    assert t_mass.requires_vip_handling() is False


def test_manager_has_skill():
    m = Manager(
        id=1, name="Менеджер 1", position=Position.SENIOR_SPECIALIST,
        office_id=1, skills={"VIP", "ENG", "KZ"}, current_load=3,
    )
    assert m.has_skill("VIP") is True
    assert m.has_skill("ENG") is True
    assert m.has_skill("KZ") is True
    assert m.has_skill("UNKNOWN") is False


def test_manager_is_chief_specialist():
    chief = Manager(
        id=1, name="M1", position=Position.CHIEF_SPECIALIST,
        office_id=1, skills=set(), current_load=0,
    )
    assert chief.is_chief_specialist() is True

    senior = Manager(
        id=2, name="M2", position=Position.SENIOR_SPECIALIST,
        office_id=1, skills=set(), current_load=0,
    )
    assert senior.is_chief_specialist() is False
