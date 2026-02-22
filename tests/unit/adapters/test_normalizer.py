"""Tests for CSV normalizer functions."""

from app.adapters.csv_loader.normalizer import (
    clean_string,
    normalize_column_name,
    parse_skills,
)

# ─── normalize_column_name ───────────────────────────────────────────


def test_strip_trailing_spaces():
    assert normalize_column_name("  Город  ") == "город"


def test_remove_bom():
    assert normalize_column_name("\ufeffНазвание") == "название"


def test_replace_spaces_with_underscore():
    assert normalize_column_name("Дата рождения") == "дата_рождения"


def test_non_breaking_space():
    assert normalize_column_name("Дата\u00a0рождения") == "дата_рождения"


def test_multiple_spaces():
    assert normalize_column_name("Имя   Фамилия") == "имя_фамилия"


def test_lowercase():
    assert normalize_column_name("GUID") == "guid"


def test_bom_plus_trailing_space():
    """Combined BOM + trailing spaces (common in real-world CSV)."""
    assert normalize_column_name("\ufeff  Описание  ") == "описание"


# ─── clean_string ────────────────────────────────────────────────────


def test_clean_string_strips():
    assert clean_string("  hello  ") == "hello"


def test_clean_string_empty_to_none():
    assert clean_string("   ") is None
    assert clean_string("") is None


def test_clean_string_none():
    assert clean_string(None) is None


def test_clean_string_normal():
    assert clean_string("Алматы") == "Алматы"


# ─── parse_skills ────────────────────────────────────────────────────


def test_parse_skills_comma_separated():
    assert parse_skills("VIP, KZ, ENG") == {"VIP", "KZ", "ENG"}


def test_parse_skills_semicolon():
    assert parse_skills("VIP;KZ;ENG") == {"VIP", "KZ", "ENG"}


def test_parse_skills_space_separated():
    assert parse_skills("VIP KZ ENG") == {"VIP", "KZ", "ENG"}


def test_parse_skills_mixed():
    assert parse_skills("VIP, KZ; ENG") == {"VIP", "KZ", "ENG"}


def test_parse_skills_empty():
    assert parse_skills("") == set()
    assert parse_skills(None) == set()


def test_parse_skills_lowercase_normalized():
    assert parse_skills("vip, kz") == {"VIP", "KZ"}


def test_parse_skills_whitespace_around():
    assert parse_skills("  VIP , KZ  ") == {"VIP", "KZ"}
