"""Office entity — a business unit with a physical location."""

from dataclasses import dataclass

from app.domain.value_objects.geo_point import GeoPoint


@dataclass
class Office:
    id: int | None
    name: str
    address: str
    location: GeoPoint | None = None
