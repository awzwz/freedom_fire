"""Domain enums — pure Python, no external dependencies."""

from enum import Enum


class TicketType(str, Enum):
    COMPLAINT = "Жалоба"
    DATA_CHANGE = "Смена данных"
    CONSULTATION = "Консультация"
    CLAIM = "Претензия"
    APP_MALFUNCTION = "Неработоспособность приложения"
    FRAUD = "Мошеннические действия"
    SPAM = "Спам"


class Sentiment(str, Enum):
    POSITIVE = "Позитивный"
    NEUTRAL = "Нейтральный"
    NEGATIVE = "Негативный"


class Language(str, Enum):
    KZ = "KZ"
    ENG = "ENG"
    RU = "RU"


class Segment(str, Enum):
    MASS = "Mass"
    VIP = "VIP"
    PRIORITY = "Priority"


class Position(str, Enum):
    SPECIALIST = "Специалист"
    SENIOR_SPECIALIST = "Ведущий специалист"
    CHIEF_SPECIALIST = "Главный специалист"


class GeoStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    FAILED = "failed"
    ABROAD = "abroad"
