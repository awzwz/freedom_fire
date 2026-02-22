"""Tests for GeoPoint value object."""

from app.domain.value_objects.geo_point import GeoPoint


def test_haversine_same_point():
    """Distance from a point to itself should be 0."""
    p = GeoPoint(latitude=43.238949, longitude=76.945465)
    assert p.haversine_km(p) == 0.0


def test_haversine_almaty_to_astana():
    """Almaty to Astana is approximately 970 km (straight line)."""
    almaty = GeoPoint(latitude=43.238949, longitude=76.945465)
    astana = GeoPoint(latitude=51.128207, longitude=71.430411)
    distance = almaty.haversine_km(astana)
    # Haversine straight-line distance is ~970 km (road distance is longer)
    assert 900 < distance < 1050


def test_haversine_almaty_to_karaganda():
    """Almaty to Karaganda is approximately 850 km."""
    almaty = GeoPoint(latitude=43.238949, longitude=76.945465)
    karaganda = GeoPoint(latitude=49.806406, longitude=73.085485)
    distance = almaty.haversine_km(karaganda)
    assert 700 < distance < 1000


def test_geo_point_is_frozen():
    """GeoPoint should be immutable."""
    p = GeoPoint(latitude=43.0, longitude=76.0)
    try:
        p.latitude = 50.0
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
