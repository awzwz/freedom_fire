"""Tests for CSV loader functions."""

import csv
import tempfile
from pathlib import Path

from app.adapters.csv_loader.loader import load_managers, load_offices, load_tickets


def _write_csv(rows: list[dict], path: Path, encoding: str = "utf-8-sig") -> None:
    """Helper to write a test CSV file."""
    if not rows:
        return
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_load_offices_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "offices.csv"
        _write_csv([
            {"Название": "Алматы ЦО", "Адрес": "ул. Абая 1", "Широта": "43.238", "Долгота": "76.945"},
            {"Название": "Астана ЦО", "Адрес": "пр. Мангилик 1", "Широта": "51.128", "Долгота": "71.430"},
        ], csv_path)

        offices = load_offices(csv_path)
        assert len(offices) == 2
        assert offices[0]["name"] == "Алматы ЦО"
        assert offices[0]["latitude"] == 43.238
        assert offices[1]["name"] == "Астана ЦО"


def test_load_offices_missing_coords():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "offices.csv"
        _write_csv([
            {"Название": "Тест", "Адрес": "адрес", "Широта": "", "Долгота": ""},
        ], csv_path)

        offices = load_offices(csv_path)
        assert offices[0]["latitude"] is None
        assert offices[0]["longitude"] is None


def test_load_managers_with_skills():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "managers.csv"
        _write_csv([
            {"ФИО": "Иванов И.И.", "Должность": "Ведущий специалист", "Филиал": "Алматы", "Навыки": "VIP, KZ"},
            {"ФИО": "Петров П.П.", "Должность": "Специалист", "Филиал": "Астана", "Навыки": ""},
        ], csv_path)

        managers = load_managers(csv_path)
        assert len(managers) == 2
        assert managers[0]["name"] == "Иванов И.И."
        assert managers[0]["skills"] == {"VIP", "KZ"}
        assert managers[1]["skills"] == set()


def test_load_tickets_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "tickets.csv"
        _write_csv([
            {
                "GUID": "abc-123", "Пол": "М", "Дата рождения": "1990-01-01",
                "Описание": "Тест", "Вложения": "", "Сегмент": "Mass",
                "Страна": "Казахстан", "Регион": "Алматинская", "Город": "Алматы",
                "Улица": "ул. Абая", "Дом": "10",
            },
        ], csv_path)

        tickets = load_tickets(csv_path)
        assert len(tickets) == 1
        assert tickets[0]["guid"] == "abc-123"
        assert tickets[0]["segment"] == "Mass"
        assert tickets[0]["country"] == "Казахстан"


def test_load_offices_from_business_units_format():
    """Dataset business_units.csv uses columns: 'Офис','Адрес'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "business_units.csv"
        _write_csv([
            {"Офис": "Алматы", "Адрес": "пр-т Аль-Фараби, 77"},
            {"Офис": "Астана", "Адрес": "Достык 16"},
        ], csv_path)

        offices = load_offices(csv_path)
        assert len(offices) == 2
        assert offices[0]["name"] == "Алматы"
        assert offices[0]["address"]


def test_load_tickets_dataset_headers_guid_clienta():
    """Dataset tickets.csv uses GUID клиента / Пол клиента / Сегмент клиента / Населённый пункт."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "tickets.csv"
        _write_csv([
            {
                "GUID клиента": "abc-123",
                "Пол клиента": "Мужской",
                "Дата рождения": "1998-10-02 0:00",
                "Описание ": "Срочно! Счета заблокированы",
                "Вложения": "",
                "Сегмент клиента": "Mass",
                "Страна": "Казахстан",
                "Область": "Акмолинская",
                "Населённый пункт": "Красный Яр",
                "Улица": "ул. Северная",
                "Дом": "9.0",
            }
        ], csv_path)

        tickets = load_tickets(csv_path)
        assert tickets[0]["guid"] == "abc-123"
        assert tickets[0]["city"] == "Красный Яр"
        assert tickets[0]["building"] == "9"


def test_semicolon_delimiter_sniffing_for_excel_ru():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "managers.csv"
        # Write semicolon-separated CSV
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("ФИО;Должность ;Офис;Навыки;Количество обращений в работе\n")
            f.write("Менеджер 1;Ведущий специалист;Алматы;VIP, ENG;4\n")

        managers = load_managers(csv_path)
        assert managers[0]["name"] == "Менеджер 1"
        assert managers[0]["current_load"] == 4


def test_load_with_bom_and_trailing_spaces():
    """CSV with BOM encoding and trailing spaces in column names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "offices.csv"
        # Manually write with BOM and trailing spaces in headers
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("Название  ,Адрес ,Широта,Долгота \n")
            f.write("Тест,адрес,43.0,77.0\n")

        offices = load_offices(csv_path)
        assert len(offices) == 1
        assert offices[0]["name"] == "Тест"


def test_load_comma_in_latitude():
    """European-style decimal separator (comma instead of dot)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "offices.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("Название;Адрес;Широта;Долгота\n")
            # Note: can't use DictReader with ; for this test since csv default is comma
            # This tests _parse_float with comma decimal
        # For _parse_float directly:
        from app.adapters.csv_loader.loader import _parse_float
        assert _parse_float("43,238") == 43.238
        assert _parse_float("76.945") == 76.945
        assert _parse_float(None) is None
        assert _parse_float("") is None
