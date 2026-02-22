"""Port interface for AI analytics persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.ai_analysis import AIAnalysis


class AnalyticsRepository(ABC):
    @abstractmethod
    async def save(self, analysis: AIAnalysis) -> AIAnalysis:
        ...

    @abstractmethod
    async def get_by_ticket(self, ticket_id: int) -> AIAnalysis | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[AIAnalysis]:
        ...
