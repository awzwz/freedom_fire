"""CSV loader — reads and normalizes CSV data files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from app.adapters.csv_loader.normalizer import (
    clean_string,
    normalize_column_name,
    parse_skills,
)

logger = logging.getLogger(__name__)


def _sniff_dialect(sample: str) -> csv.Dialect:
    """Try to detect delimiter (comma/semicolon/tab) to support Excel RU exports."""
    # Excel RU exports often use ';'
    if not sample:
        return csv.get_dialect("excel")

    first_line = sample.splitlines()[0] if sample else ""
    delims = [";", ",", "\t"]
    counts = {d: first_line.count(d) for d in delims}
    best_delim = max(counts, key=counts.get)

    if counts[best_delim] > 0:
        class DynamicDialect(csv.excel):
            delimiter = best_delim
        return DynamicDialect
    
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
        return dialect
    except Exception:
        return csv.get_dialect("excel")


def _read_csv(file_path: Path, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    """Read a CSV file with BOM handling and column normalization.

    Args:
        file_path: path to the CSV file.
        encoding: file encoding (utf-8-sig strips BOM automatically).

    Returns:
        List of dicts with normalized column names.
    """
    with open(file_path, encoding=encoding, newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = _sniff_dialect(sample)
        reader = csv.DictReader(f, dialect=dialect)
        # Normalize column names
        if reader.fieldnames is None:
            raise ValueError(f"CSV file {file_path} has no header row")

        col_map = {col: normalize_column_name(col) for col in reader.fieldnames}
        rows = []
        for raw_row in reader:
            row = {col_map[k]: clean_string(v) for k, v in raw_row.items() if k is not None}
            rows.append(row)

    logger.info("Loaded %d rows from %s (columns: %s)", len(rows), file_path.name, list(col_map.values()))
    return rows


def load_offices(file_path: Path) -> list[dict]:
    """Load and normalize the offices CSV.

    Expected columns (after normalization):
        id, название (name), адрес (address), широта (latitude), долгота (longitude)
    """
    rows = _read_csv(file_path)
    offices = []
    for row in rows:
        office = {
            # business_units.csv uses "Офис" / "Адрес"
            "name": clean_string(
                row.get("офис")
                or row.get("название")
                or row.get("name")
                or ""
            ),
            "address": clean_string(row.get("адрес") or row.get("address") or "") or "",
            "latitude": _parse_float(row.get("широта") or row.get("latitude")),
            "longitude": _parse_float(row.get("долгота") or row.get("longitude")),
        }
        offices.append(office)
    logger.info("Parsed %d offices", len(offices))
    return offices


def load_managers(file_path: Path) -> list[dict]:
    """Load and normalize the managers CSV.

    Expected columns (after normalization):
        id, фио (name), должность (position), филиал/офис (office_name), навыки (skills)
    """
    rows = _read_csv(file_path)
    managers = []
    for row in rows:
        # Try multiple possible column names (Cyrillic or English)
        name = (
            clean_string(row.get("фио"))
            or clean_string(row.get("имя"))
            or clean_string(row.get("name"))
            or ""
        )
        position = (
            clean_string(row.get("должность"))
            or clean_string(row.get("position"))
            or ""
        )
        office_name = (
            clean_string(row.get("филиал"))
            or clean_string(row.get("офис"))
            or clean_string(row.get("филиал_офис"))
            or clean_string(row.get("office"))
            or ""
        )
        raw_skills = (
            clean_string(row.get("навыки"))
            or clean_string(row.get("skills"))
            or ""
        )
        current_load = _parse_int(
            row.get("количество_обращений_в_работе")
            or row.get("current_load")
            or row.get("load")
        )

        managers.append({
            "name": name,
            "position": position,
            "office_name": office_name,
            "skills": parse_skills(raw_skills),
            "current_load": current_load,
        })
    logger.info("Parsed %d managers", len(managers))
    return managers


def load_tickets(file_path: Path) -> list[dict]:
    """Load and normalize the tickets CSV.

    Expected columns (after normalization):
        guid, пол (gender), дата_рождения (birth_date), описание (description),
        вложения (attachments), сегмент (segment), страна (country),
        регион (region), город (city), улица (street), дом (building)
    """
    rows = _read_csv(file_path)
    tickets = []
    for row in rows:
        # tickets.csv uses: GUID клиента, Пол клиента, Дата рождения, Описание, ...
        ticket = {
            "guid": clean_string(
                row.get("guid_клиента")
                or row.get("guid")
                or row.get("id")
                or row.get("№")
                or ""
            )
            or "",
            "gender": clean_string(row.get("пол_клиента") or row.get("пол") or row.get("gender")),
            "birth_date": clean_string(row.get("дата_рождения") or row.get("birth_date")),
            "description": clean_string(row.get("описание") or row.get("description")),
            "attachments": clean_string(row.get("вложения") or row.get("attachments")),
            "segment": clean_string(
                row.get("сегмент_клиента")
                or row.get("сегмент")
                or row.get("segment")
            )
            or "Mass",
            "country": clean_string(row.get("страна") or row.get("country")),
            "region": clean_string(row.get("область") or row.get("регион") or row.get("region")),
            "city": clean_string(
                row.get("населённый_пункт")
                or row.get("населенный_пункт")
                or row.get("город")
                or row.get("city")
            ),
            "street": clean_string(row.get("улица") or row.get("street")),
            "building": _normalize_building(clean_string(row.get("дом") or row.get("building"))),
        }
        tickets.append(ticket)
    logger.info("Parsed %d tickets", len(tickets))
    return tickets


def _parse_float(value: str | None) -> float | None:
    """Safely parse a float from a string."""
    if not value:
        return None
    try:
        return float(value.replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def _parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        # handle "4", "4.0"
        return int(float(str(value).replace(",", ".").strip()))
    except Exception:
        return 0


def _normalize_building(value: str | None) -> str | None:
    if not value:
        return value
    v = str(value).strip()
    # if comes like "9.0" -> "9"
    try:
        f = float(v.replace(",", "."))
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return v
