"""Port interface for LLM-based ticket analysis."""

from abc import ABC, abstractmethod

from app.domain.entities.ai_analysis import AIAnalysis


class LLMPort(ABC):
    @abstractmethod
    async def analyze_ticket(self, description: str, attachments: str | None) -> AIAnalysis:
        """Analyze ticket text and return structured AI result.

        The returned AIAnalysis will have id=None and ticket_id=0
        (to be set by the caller before persistence).
        """
        ...
