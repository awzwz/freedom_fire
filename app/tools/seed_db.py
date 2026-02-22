"""Seed database from CSV files.

Usage:
    python -m app.tools.seed_db
    python -m app.tools.seed_db --data-dir data
    python -m app.tools.seed_db --drop  # drop existing data first
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.csv_loader.loader import load_managers, load_offices, load_tickets
from app.adapters.geocoder.nominatim_adapter import NominatimAdapter
from app.adapters.persistence.database import async_session_factory
from app.adapters.persistence.models import (
    AssignmentModel,
    ManagerModel,
    OfficeModel,
    RoundRobinStateModel,
    TicketAnalyticsModel,
    TicketModel,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Position normalization mapping
POSITION_MAP: dict[str, str] = {
    "специалист": "Специалист",
    "ведущий специалист": "Ведущий специалист",
    "главный специалист": "Главный специалист",
}


def _normalize_position(raw: str) -> str:
    """Normalize position string to canonical form."""
    key = raw.strip().lower()
    return POSITION_MAP.get(key, raw.strip())


def _parse_date(raw: str | None) -> date | None:
    """Parse dates in various formats."""
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date: %s", raw)
    return None


async def _drop_data(session: AsyncSession) -> None:
    """Delete all data in correct order (respecting FK constraints)."""
    for model in [
        AssignmentModel,
        TicketAnalyticsModel,
        RoundRobinStateModel,
        TicketModel,
        ManagerModel,
        OfficeModel,
    ]:
        await session.execute(delete(model))
    await session.commit()
    logger.info("Dropped all existing data")


async def seed(data_dir: Path, drop: bool = False) -> dict[str, int]:
    """Main seed function. Returns counts of seeded records."""
    counts = {"offices": 0, "managers": 0, "tickets": 0}

    # Discover CSV files
    # Our dataset uses business_units.csv for offices
    office_csv = _find_csv(data_dir, ["business_units", "business", "units", "offices", "офисы", "филиалы"])
    manager_csv = _find_csv(data_dir, ["managers", "менеджеры", "сотрудники"])
    ticket_csv = _find_csv(data_dir, ["tickets", "заявки", "тикеты", "обращения"])

    if not office_csv:
        raise FileNotFoundError(
            f"No offices CSV found in {data_dir}. Expected something like business_units.csv"
        )
    if not manager_csv:
        raise FileNotFoundError(
            f"No managers CSV found in {data_dir}. Expected something like managers.csv"
        )

    geocoder = NominatimAdapter()

    async with async_session_factory() as session:
        if drop:
            await _drop_data(session)

        # 1. Seed offices
        office_data = load_offices(office_csv)
        office_name_to_id: dict[str, int] = {}

        for od in office_data:
            # Check if office already exists
            existing = await session.execute(
                select(OfficeModel).where(OfficeModel.name == od["name"])
            )
            if existing.scalar_one_or_none():
                logger.debug("Office '%s' already exists, skipping", od["name"])
                continue

            lat = od["latitude"]
            lon = od["longitude"]
            if lat is None or lon is None:
                # business_units.csv doesn't have coordinates; derive them for distance calculations
                query = ", ".join([p for p in [od["name"], od["address"], "Казахстан"] if p])
                point = await geocoder.geocode(query)
                if point:
                    lat, lon = point.latitude, point.longitude

            office = OfficeModel(
                name=od["name"],
                address=od["address"],
                latitude=lat,
                longitude=lon,
            )
            session.add(office)
            await session.flush()
            office_name_to_id[od["name"]] = office.id
            counts["offices"] += 1

        await session.commit()

        # Refresh office map with all offices + validate coordinates
        result = await session.execute(select(OfficeModel))
        all_offices = result.scalars().all()
        missing_coords = 0
        for o in all_offices:
            office_name_to_id[o.name] = o.id
            # Retry geocoding for offices with missing coordinates
            if o.latitude is None or o.longitude is None:
                query = ", ".join([p for p in ["Казахстан", o.name, o.address] if p])
                point = await geocoder.geocode(query)
                if point:
                    o.latitude = point.latitude
                    o.longitude = point.longitude
                    logger.info("Geocoded office '%s' → (%f, %f)", o.name, point.latitude, point.longitude)
                else:
                    missing_coords += 1
                    logger.warning(
                        "Office '%s' has no coordinates after geocoding — "
                        "it will be excluded from nearest-office selection!",
                        o.name,
                    )
        if missing_coords:
            logger.warning(
                "%d office(s) still missing coordinates after geocoding retries",
                missing_coords,
            )
        await session.commit()
        logger.info("Office map: %d offices (%d with coords)", len(office_name_to_id), len(office_name_to_id) - missing_coords)

        # 2. Seed managers
        manager_data = load_managers(manager_csv)
        for md in manager_data:
            office_name = md["office_name"]
            office_id = _resolve_office_id(office_name, office_name_to_id)
            if office_id is None:
                logger.warning(
                    "Manager '%s': office '%s' not found, skipping",
                    md["name"], office_name,
                )
                continue

            # Check if manager already exists
            existing = await session.execute(
                select(ManagerModel).where(
                    ManagerModel.name == md["name"],
                    ManagerModel.office_id == office_id,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug("Manager '%s' already exists, skipping", md["name"])
                continue

            manager = ManagerModel(
                name=md["name"],
                position=_normalize_position(md["position"]),
                office_id=office_id,
                skills=sorted(md["skills"]),
                # IMPORTANT: keep initial load from CSV, otherwise RR and eligibility look broken.
                current_load=int(md.get("current_load") or 0),
            )
            session.add(manager)
            counts["managers"] += 1

        await session.commit()

        # 3. Seed tickets (if CSV exists)
        if ticket_csv:
            ticket_data = load_tickets(ticket_csv)
            for td in ticket_data:
                # Check if ticket already exists by GUID
                existing = await session.execute(
                    select(TicketModel).where(TicketModel.guid == td["guid"])
                )
                if existing.scalar_one_or_none():
                    logger.debug("Ticket '%s' already exists, skipping", td["guid"])
                    continue

                ticket = TicketModel(
                    guid=td["guid"],
                    gender=td["gender"],
                    birth_date=_parse_date(td["birth_date"]),
                    description=td["description"],
                    attachments=td["attachments"],
                    segment=td["segment"],
                    country=td["country"],
                    region=td["region"],
                    city=td["city"],
                    street=td["street"],
                    building=td["building"],
                    geo_status="pending",
                )
                session.add(ticket)
                counts["tickets"] += 1

            await session.commit()
        else:
            logger.info("No tickets CSV found — skipping ticket import")

        # 4. Initialize round-robin state if not exists
        existing_rr = await session.execute(
            select(RoundRobinStateModel).where(
                RoundRobinStateModel.rr_key == "global"
            )
        )
        if not existing_rr.scalar_one_or_none():
            session.add(RoundRobinStateModel(rr_key="global", counter=0))
            await session.commit()
            logger.info("Initialized global round-robin counter")

    logger.info(
        "Seed complete: %d offices, %d managers, %d tickets",
        counts["offices"], counts["managers"], counts["tickets"],
    )
    return counts


def _find_csv(data_dir: Path, name_hints: list[str]) -> Path | None:
    """Find a CSV file matching any of the name hints."""
    for f in data_dir.glob("*.csv"):
        fname_lower = f.stem.lower()
        for hint in name_hints:
            if hint in fname_lower:
                logger.info("Found CSV: %s (matched hint '%s')", f.name, hint)
                return f
    return None


def _resolve_office_id(
    office_name: str, office_map: dict[str, int]
) -> int | None:
    """Resolve office name to ID using fuzzy matching.

    Tries exact match first, then substring match.
    """
    if not office_name:
        return None

    # Exact match
    if office_name in office_map:
        return office_map[office_name]

    # Substring match (e.g., "Алматы" matches "Алматы ЦО")
    name_lower = office_name.strip().lower()
    for known_name, oid in office_map.items():
        if name_lower in known_name.lower() or known_name.lower() in name_lower:
            return oid

    return None


async def _verify_data() -> None:
    """Print sanity checks after seeding."""
    async with async_session_factory() as session:
        offices = (await session.execute(select(OfficeModel))).scalars().all()
        managers = (await session.execute(select(ManagerModel))).scalars().all()
        tickets = (await session.execute(select(TicketModel))).scalars().all()

        print(f"\n{'='*50}")
        print("SEED VERIFICATION")
        print(f"{'='*50}")
        print(f"Offices:  {len(offices)}")
        print(f"Managers: {len(managers)}")
        print(f"Tickets:  {len(tickets)}")

        # Check offices have coordinates
        with_coords = sum(1 for o in offices if o.latitude and o.longitude)
        print(f"Offices with coordinates: {with_coords}/{len(offices)}")

        # Check managers have skills
        with_skills = sum(1 for m in managers if m.skills and len(m.skills) > 0)
        print(f"Managers with skills: {with_skills}/{len(managers)}")

        # Check position distribution
        positions = {}
        for m in managers:
            positions[m.position] = positions.get(m.position, 0) + 1
        print(f"Position distribution: {positions}")

        # Check segment distribution
        segments = {}
        for t in tickets:
            segments[t.segment] = segments.get(t.segment, 0) + 1
        print(f"Segment distribution: {segments}")

        # Check for hub offices
        hub_names = [o.name for o in offices if "Астана" in o.name or "Алматы" in o.name]
        print(f"Hub offices found: {hub_names}")
        print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Seed FIRE database from CSV files")
    parser.add_argument(
        "--data-dir", type=str, default="data",
        help="Directory containing CSV files (default: data)",
    )
    parser.add_argument(
        "--drop", action="store_true",
        help="Drop existing data before seeding",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only run verification, don't seed",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not args.verify_only and not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        sys.exit(1)

    if args.verify_only:
        asyncio.run(_verify_data())
    else:
        async def run_all():
            await seed(data_dir, drop=args.drop)
            await _verify_data()
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
