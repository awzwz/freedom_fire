"""Tests for domain enums."""

from app.domain.value_objects.enums import (
    Language,
    Position,
    Segment,
    Sentiment,
    TicketType,
)


def test_ticket_types_count():
    assert len(TicketType) == 7


def test_sentiment_values():
    assert Sentiment.POSITIVE.value == "Позитивный"
    assert Sentiment.NEUTRAL.value == "Нейтральный"
    assert Sentiment.NEGATIVE.value == "Негативный"


def test_language_values():
    assert Language.KZ.value == "KZ"
    assert Language.ENG.value == "ENG"
    assert Language.RU.value == "RU"


def test_segment_values():
    assert Segment.MASS.value == "Mass"
    assert Segment.VIP.value == "VIP"
    assert Segment.PRIORITY.value == "Priority"


def test_position_values():
    assert Position.SPECIALIST.value == "Специалист"
    assert Position.SENIOR_SPECIALIST.value == "Ведущий специалист"
    assert Position.CHIEF_SPECIALIST.value == "Главный специалист"
