"""AI analysis result — output from LLM enrichment of a ticket."""

from dataclasses import dataclass

from app.domain.value_objects.enums import Language, Sentiment, TicketType


@dataclass
class AIAnalysis:
    id: int | None
    ticket_id: int
    ticket_type: TicketType
    sentiment: Sentiment
    priority_score: int
    language: Language
    summary: str
    llm_model: str | None = None
