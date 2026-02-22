"""CSV column normalization — handles BOM, trailing spaces, encoding quirks."""

from __future__ import annotations

import re


def normalize_column_name(name: str) -> str:
    """Normalize a CSV column name.

    - Strips leading/trailing whitespace
    - Removes BOM characters (\\ufeff)
    - Replaces multiple spaces / non-breaking spaces with single underscore
    - Lowercases
    - Strips non-alphanumeric characters (except underscore)
    """
    # Remove BOM
    name = name.replace("\ufeff", "")
    # Strip whitespace
    name = name.strip()
    # Replace spaces, non-breaking spaces, tabs with underscore
    name = re.sub(r"[\s\u00a0]+", "_", name)
    # Lowercase
    name = name.lower()
    # Remove anything that's not alphanumeric or underscore (keep Cyrillic)
    name = re.sub(r"[^\w]", "", name, flags=re.UNICODE)
    return name


def normalize_columns(columns: list[str]) -> dict[str, str]:
    """Return mapping of original column names to normalized names."""
    return {col: normalize_column_name(col) for col in columns}


def clean_string(value: str | None) -> str | None:
    """Strip whitespace and return None for empty strings."""
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def parse_skills(raw: str | None) -> set[str]:
    """Parse skill strings like 'VIP, KZ, ENG' into a set of skill codes.

    Handles various separators (comma, semicolon, space) and normalizes each skill.
    """
    if not raw:
        return set()
    # Split by comma, semicolon, or whitespace
    parts = re.split(r"[,;\s]+", raw.strip())
    return {p.strip().upper() for p in parts if p.strip()}
