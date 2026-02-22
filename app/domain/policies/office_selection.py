"""OfficeSelectionPolicy — pick the nearest office or apply 50/50 fallback."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.domain.entities.office import Office
from app.domain.value_objects.geo_point import GeoPoint

# Well-known hub office names used for the 50/50 fallback
ASTANA_HUB = "Астана"
ALMATY_HUB = "Алматы"


@dataclass(frozen=True)
class OfficeSelection:
    """Result of the office selection policy."""

    office: Office
    distance_km: float | None  # None when fallback used
    fallback_used: bool
    reason: str


def select_nearest_office(
    client_location: GeoPoint,
    offices: list[Office],
) -> OfficeSelection:
    """Select the geographically nearest office that has a known location.

    Args:
        client_location: geocoded point of the client.
        offices: all offices (some may lack location).

    Returns:
        OfficeSelection with the nearest office.

    Raises:
        ValueError: if no office has a known location.
    """
    candidates = [(o, client_location.haversine_km(o.location)) for o in offices if o.location]
    if not candidates:
        raise ValueError("No offices with known locations available")

    best_office, best_distance = min(candidates, key=lambda x: x[1])
    return OfficeSelection(
        office=best_office,
        distance_km=round(best_distance, 2),
        fallback_used=False,
        reason=f"Nearest office: {best_office.name} ({best_distance:.1f} km)",
    )


def select_fallback_office(
    counter: int,
    offices: list[Office],
) -> OfficeSelection:
    """Deterministic 50/50 split between Астана and Алматы hub offices.

    Uses a round-robin counter to perfectly distribute tickets that have
    no known address or are from abroad.

    Args:
        counter: incrementing integer from a RoundRobin repository.
        offices: all available offices.

    Returns:
        OfficeSelection with fallback=True.
    """
    if not offices:
        raise ValueError("No offices available for fallback")

    hub_map: dict[str, Office] = {}
    for office in offices:
        if ASTANA_HUB in office.name:
            hub_map[ASTANA_HUB] = office
        if ALMATY_HUB in office.name:
            hub_map[ALMATY_HUB] = office

    # If we have both Astana and Almaty, use the 50/50 logic
    if ASTANA_HUB in hub_map and ALMATY_HUB in hub_map:
        pick_astana = counter % 2 == 0
        if pick_astana:
            chosen = hub_map[ASTANA_HUB]
            reason = f"Fallback 50/50 → {ASTANA_HUB} (round-robin)"
        else:
            chosen = hub_map[ALMATY_HUB]
            reason = f"Fallback 50/50 → {ALMATY_HUB} (round-robin)"
    else:
        # Graceful fallback if Astana/Almaty are missing from the DB
        sorted_offices = sorted(offices, key=lambda o: o.id)
        chosen = sorted_offices[counter % len(sorted_offices)]
        reason = f"Fallback → {chosen.name} (round-robin across all offices)"

    return OfficeSelection(
        office=chosen,
        distance_km=None,
        fallback_used=True,
        reason=reason,
    )
