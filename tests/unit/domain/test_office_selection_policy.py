"""Tests for OfficeSelectionPolicy."""

import pytest

from app.domain.entities.office import Office
from app.domain.policies.office_selection import (
    select_fallback_office,
    select_nearest_office,
)
from app.domain.value_objects.geo_point import GeoPoint

# ─── Fixtures ────────────────────────────────────────────────────────


def _make_offices() -> list[Office]:
    """Create a small set of offices with known locations."""
    return [
        Office(
            id=1, name="Алматы ЦО", address="ул. Абая 1",
            location=GeoPoint(latitude=43.238949, longitude=76.945465),
        ),
        Office(
            id=2, name="Астана ЦО", address="пр. Мангилик Ел 1",
            location=GeoPoint(latitude=51.128207, longitude=71.430411),
        ),
        Office(
            id=3, name="Караганда", address="ул. Бухар Жырау 5",
            location=GeoPoint(latitude=49.806406, longitude=73.085485),
        ),
    ]


# ─── select_nearest_office ───────────────────────────────────────────


def test_nearest_office_almaty():
    """Client in Almaty should get Almaty office."""
    offices = _make_offices()
    client = GeoPoint(latitude=43.25, longitude=76.95)  # near Almaty
    result = select_nearest_office(client, offices)
    assert result.office.id == 1
    assert result.fallback_used is False
    assert result.distance_km is not None
    assert result.distance_km < 5  # very close


def test_nearest_office_astana():
    """Client in Astana should get Astana office."""
    offices = _make_offices()
    client = GeoPoint(latitude=51.1, longitude=71.4)  # near Astana
    result = select_nearest_office(client, offices)
    assert result.office.id == 2
    assert result.fallback_used is False


def test_nearest_office_karaganda():
    """Client near Karaganda should get Karaganda office."""
    offices = _make_offices()
    client = GeoPoint(latitude=49.8, longitude=73.1)
    result = select_nearest_office(client, offices)
    assert result.office.id == 3


def test_nearest_office_skips_offices_without_location():
    """Offices without coordinates should be ignored."""
    offices = [
        Office(id=1, name="No location", address="addr", location=None),
        Office(
            id=2, name="Has location", address="addr",
            location=GeoPoint(latitude=43.0, longitude=77.0),
        ),
    ]
    client = GeoPoint(latitude=43.0, longitude=77.0)
    result = select_nearest_office(client, offices)
    assert result.office.id == 2


def test_nearest_office_no_locations_raises():
    """Should raise ValueError if no office has a location."""
    offices = [
        Office(id=1, name="A", address="a", location=None),
        Office(id=2, name="B", address="b", location=None),
    ]
    with pytest.raises(ValueError, match="No offices with known locations"):
        select_nearest_office(GeoPoint(latitude=43.0, longitude=77.0), offices)


# ─── select_fallback_office ─────────────────────────────────────────


def test_fallback_returns_astana_or_almaty():
    """Fallback should always return one of the two hub offices."""
    offices = _make_offices()
    result = select_fallback_office("test-guid-123", offices)
    assert result.fallback_used is True
    assert result.distance_km is None
    assert result.office.id in (1, 2)  # Almaty or Astana


def test_fallback_is_deterministic():
    """Same GUID should always produce the same hub."""
    offices = _make_offices()
    r1 = select_fallback_office("guid-abc", offices)
    r2 = select_fallback_office("guid-abc", offices)
    assert r1.office.id == r2.office.id


def test_fallback_distributes_across_hubs():
    """Over many GUIDs, both hubs should appear (probabilistic but reliable)."""
    offices = _make_offices()
    chosen_ids = set()
    for i in range(100):
        result = select_fallback_office(f"guid-{i}", offices)
        chosen_ids.add(result.office.id)
    # Both Almaty (1) and Astana (2) should appear in 100 trials
    assert 1 in chosen_ids
    assert 2 in chosen_ids


def test_fallback_missing_hub_raises():
    """Should raise ValueError if hub offices are not found."""
    offices = [
        Office(id=1, name="Караганда", address="addr", location=None),
    ]
    with pytest.raises(ValueError, match="Hub offices not found"):
        select_fallback_office("guid-123", offices)
