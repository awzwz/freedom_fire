"""AnalyzeTicketUseCase — enrich a single ticket via LLM."""

from __future__ import annotations

import logging

from app.application.ports.llm_port import LLMPort
from app.domain.entities.ai_analysis import AIAnalysis

logger = logging.getLogger(__name__)


class AnalyzeTicketUseCase:
    """Orchestrates LLM analysis of a single ticket."""

    def __init__(self, llm: LLMPort):
        self._llm = llm

    async def execute(
        self, ticket_id: int, description: str, attachments: str | None = None
    ) -> AIAnalysis:
        """Analyze a ticket and return enriched AIAnalysis.

        Args:
            ticket_id: DB id of the ticket.
            description: ticket text.
            attachments: optional attachment info.

        Returns:
            AIAnalysis with ticket_id set.
        """
        if not description or not description.strip():
            logger.warning("Ticket %d has empty description, using fallback", ticket_id)
            from app.adapters.llm.openai_adapter import OpenAIAdapter

            analysis = OpenAIAdapter._heuristic_fallback("")
            analysis.ticket_id = ticket_id
            return analysis

        analysis = await self._llm.analyze_ticket(description, attachments)
        analysis.ticket_id = ticket_id
        return analysis
