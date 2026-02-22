"""Tests for AnalyzeTicketUseCase and LLM adapter heuristics."""

import pytest

from app.adapters.llm.openai_adapter import OpenAIAdapter
from app.application.ports.llm_port import LLMPort
from app.application.use_cases.analyze_ticket import AnalyzeTicketUseCase
from app.domain.entities.ai_analysis import AIAnalysis
from app.domain.value_objects.enums import Language, Sentiment, TicketType

# ─── Heuristic fallback tests ───────────────────────────────────────


def test_heuristic_detects_fraud():
    result = OpenAIAdapter._heuristic_fallback("Мошеннические действия с моим счётом")
    assert result.ticket_type == TicketType.FRAUD
    assert result.sentiment == Sentiment.NEGATIVE
    assert result.priority_score == 9


def test_heuristic_detects_complaint():
    result = OpenAIAdapter._heuristic_fallback("Хочу подать жалобу на обслуживание")
    assert result.ticket_type == TicketType.COMPLAINT
    assert result.priority_score == 7


def test_heuristic_detects_data_change():
    result = OpenAIAdapter._heuristic_fallback("Прошу смена данных в моём профиле")
    assert result.ticket_type == TicketType.DATA_CHANGE
    assert result.priority_score == 5


def test_heuristic_detects_app_malfunction():
    result = OpenAIAdapter._heuristic_fallback("Приложение не работает, ошибка при входе")
    assert result.ticket_type == TicketType.APP_MALFUNCTION


def test_heuristic_default_consultation():
    result = OpenAIAdapter._heuristic_fallback("Расскажите про тарифы")
    assert result.ticket_type == TicketType.CONSULTATION


def test_heuristic_detects_kazakh():
    result = OpenAIAdapter._heuristic_fallback("Сәлем, маған көмек керек")
    assert result.language == Language.KZ


def test_heuristic_detects_english():
    result = OpenAIAdapter._heuristic_fallback("Hello, I need help with my account")
    assert result.language == Language.ENG


def test_heuristic_default_russian():
    result = OpenAIAdapter._heuristic_fallback("Здравствуйте, расскажите про услуги")
    assert result.language == Language.RU


# ─── OpenAIAdapter._map_to_analysis ─────────────────────────────────


def test_map_to_analysis_valid():
    adapter = OpenAIAdapter.__new__(OpenAIAdapter)
    adapter._model = "test-model"
    parsed = {
        "ticket_type": "Жалоба",
        "sentiment": "Негативный",
        "priority_score": 8,
        "language": "RU",
        "summary": "Клиент жалуется на обслуживание",
    }
    result = adapter._map_to_analysis(parsed)
    assert result.ticket_type == TicketType.COMPLAINT
    assert result.sentiment == Sentiment.NEGATIVE
    assert result.priority_score == 8
    assert result.language == Language.RU
    assert result.llm_model == "test-model"


def test_map_to_analysis_unknown_values_default():
    adapter = OpenAIAdapter.__new__(OpenAIAdapter)
    adapter._model = "test-model"
    parsed = {
        "ticket_type": "UNKNOWN",
        "sentiment": "UNKNOWN",
        "priority_score": 5,
        "language": "UNKNOWN",
        "summary": "test",
    }
    result = adapter._map_to_analysis(parsed)
    # Should fall back to defaults
    assert result.ticket_type == TicketType.CONSULTATION
    assert result.sentiment == Sentiment.NEUTRAL
    assert result.language == Language.RU


def test_map_to_analysis_clamps_priority():
    adapter = OpenAIAdapter.__new__(OpenAIAdapter)
    adapter._model = "test"
    # Priority > 10 should clamp to 10
    result = adapter._map_to_analysis({
        "ticket_type": "Консультация", "sentiment": "Нейтральный",
        "priority_score": 99, "language": "RU", "summary": "test",
    })
    assert result.priority_score == 10

    # Priority < 1 should clamp to 1
    result = adapter._map_to_analysis({
        "ticket_type": "Консультация", "sentiment": "Нейтральный",
        "priority_score": -5, "language": "RU", "summary": "test",
    })
    assert result.priority_score == 1


# ─── AnalyzeTicketUseCase ───────────────────────────────────────────


class FakeLLM(LLMPort):
    """Fake LLM for testing."""

    def __init__(self, response: AIAnalysis):
        self._response = response

    async def analyze_ticket(self, description: str, attachments: str | None) -> AIAnalysis:
        return self._response


@pytest.mark.asyncio
async def test_use_case_sets_ticket_id():
    fake_analysis = AIAnalysis(
        id=None, ticket_id=0, ticket_type=TicketType.CONSULTATION,
        sentiment=Sentiment.NEUTRAL, priority_score=5,
        language=Language.RU, summary="test",
    )
    use_case = AnalyzeTicketUseCase(llm=FakeLLM(fake_analysis))
    result = await use_case.execute(ticket_id=42, description="Тестовая заявка")
    assert result.ticket_id == 42


@pytest.mark.asyncio
async def test_use_case_empty_description_uses_fallback():
    fake_analysis = AIAnalysis(
        id=None, ticket_id=0, ticket_type=TicketType.FRAUD,
        sentiment=Sentiment.NEGATIVE, priority_score=9,
        language=Language.RU, summary="should not be used",
    )
    use_case = AnalyzeTicketUseCase(llm=FakeLLM(fake_analysis))
    result = await use_case.execute(ticket_id=1, description="")
    # Empty description → heuristic fallback, not the fake LLM
    assert result.ticket_id == 1
    assert result.llm_model == "heuristic-fallback"
