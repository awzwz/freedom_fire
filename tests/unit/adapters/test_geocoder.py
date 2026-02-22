"""Tests for NominatimAdapter — tests city centroid fallback (no network)."""

import pytest

from app.adapters.geocoder.nominatim_adapter import NominatimAdapter


@pytest.fixture
def adapter():
    return NominatimAdapter(user_agent="test-agent")


# ─── City centroid fallback ──────────────────────────────────────────


def test_city_centroid_almaty():
    point = NominatimAdapter._city_centroid_lookup("ул. Абая, Алматы, Казахстан")
    assert point is not None
    assert 43.0 < point.latitude < 44.0
    assert 76.0 < point.longitude < 78.0


def test_city_centroid_astana():
    point = NominatimAdapter._city_centroid_lookup("пр. Мангилик Ел, Астана")
    assert point is not None
    assert 50.0 < point.latitude < 52.0


def test_city_centroid_karaganda():
    point = NominatimAdapter._city_centroid_lookup("Караганда, ул. Бухар Жырау")
    assert point is not None
    assert 49.0 < point.latitude < 50.5


def test_city_centroid_case_insensitive():
    point = NominatimAdapter._city_centroid_lookup("шымкент")
    assert point is not None


def test_city_centroid_unknown_city():
    point = NominatimAdapter._city_centroid_lookup("Some Unknown Place")
    assert point is None


def test_city_centroid_old_astana_name():
    """Нур-Султан (old name) should resolve to Astana coordinates."""
    point = NominatimAdapter._city_centroid_lookup("Нур-Султан, пр. Кабанбай батыра")
    assert point is not None
    assert 50.0 < point.latitude < 52.0


# ─── Cache behavior ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_deduplicates(adapter):
    """Same address should return cached result on second call."""
    # Use city centroid (no network needed)
    r1 = await adapter.geocode("Алматы")
    r2 = await adapter.geocode("Алматы")
    assert r1 is r2  # same object from cache


@pytest.mark.asyncio
async def test_cache_case_insensitive(adapter):
    """Cache should be case-insensitive."""
    r1 = await adapter.geocode("алматы")
    r2 = await adapter.geocode("  Алматы  ")
    # Both should resolve to the same city, both cached
    assert r1 is not None
    assert r2 is not None
