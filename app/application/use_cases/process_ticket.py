"""ProcessTicketUseCase — full pipeline: LLM → geocode → assign."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.application.ports.analytics_repo import AnalyticsRepository
from app.application.ports.assignment_repo import AssignmentRepository
from app.application.ports.geocoder_port import GeocoderPort
from app.application.ports.llm_port import LLMPort
from app.application.ports.manager_repo import ManagerRepository
from app.application.ports.office_repo import OfficeRepository
from app.application.ports.round_robin_repo import RoundRobinRepository
from app.application.ports.ticket_repo import TicketRepository
from app.domain.entities.assignment import Assignment
from app.domain.entities.ticket import Ticket
from app.domain.policies.office_selection import (
    select_fallback_office,
    select_nearest_office,
)
from app.domain.policies.required_skills import (
    determine_required_skills,
    manager_satisfies,
)
from app.domain.policies.round_robin import pick_next
from app.domain.value_objects.enums import GeoStatus, Position
from app.domain.value_objects.enums import TicketType

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Summary of one ticket's processing."""

    ticket_id: int
    ticket_guid: str
    assigned_manager: str | None
    assigned_office: str | None
    distance_km: float | None
    fallback_used: bool
    error: str | None = None


class ProcessTicketUseCase:
    """Orchestrates the full ticket processing pipeline."""

    def __init__(
        self,
        llm: LLMPort,
        geocoder: GeocoderPort,
        ticket_repo: TicketRepository,
        manager_repo: ManagerRepository,
        office_repo: OfficeRepository,
        assignment_repo: AssignmentRepository,
        analytics_repo: AnalyticsRepository,
        rr_repo: RoundRobinRepository,
    ):
        self._llm = llm
        self._geocoder = geocoder
        self._tickets = ticket_repo
        self._managers = manager_repo
        self._offices = office_repo
        self._assignments = assignment_repo
        self._analytics = analytics_repo
        self._rr = rr_repo

    async def execute(self, ticket: Ticket) -> ProcessingResult:
        """Process a single ticket end-to-end.

        Pipeline:
        1. LLM analysis (classify, sentiment, priority, language)
        2. Geocode client address
        3. Select office (nearest or 50/50 fallback)
        4. Filter managers by skills / position
        5. Round-robin pick
        6. Persist assignment
        """
        try:
            # Step 1: LLM analysis
            analysis = await self._llm.analyze_ticket(
                ticket.description or "", ticket.attachments
            )
            analysis.ticket_id = ticket.id
            await self._analytics.save(analysis)
            logger.info(
                "Ticket %s: type=%s, lang=%s, priority=%d",
                ticket.guid, analysis.ticket_type.value,
                analysis.language.value, analysis.priority_score,
            )

            # Spam should be ignored (no assignment). We still store analytics.
            if analysis.ticket_type == TicketType.SPAM:
                logger.info("Ticket %s classified as SPAM → skip assignment", ticket.guid)
                return ProcessingResult(
                    ticket_id=ticket.id,
                    ticket_guid=ticket.guid,
                    assigned_manager=None,
                    assigned_office=None,
                    distance_km=None,
                    fallback_used=False,
                    error=None,
                )

            # Step 2: Geocode
            if not ticket.is_address_known():
                address_str = ticket.build_address_string()
                if address_str and ticket.is_domestic():
                    point = await self._geocoder.geocode(address_str)
                    if point:
                        ticket.client_location = point
                        ticket.geo_status = GeoStatus.RESOLVED
                    else:
                        ticket.geo_status = GeoStatus.FAILED
                elif not ticket.is_domestic() and ticket.country:
                    ticket.geo_status = GeoStatus.ABROAD
                else:
                    ticket.geo_status = GeoStatus.FAILED
                await self._tickets.update(ticket)

            # Step 3: Select office
            offices = await self._offices.get_all()
            if ticket.is_address_known():
                office_sel = select_nearest_office(ticket.client_location, offices)
            else:
                fallback_counter = await self._rr.increment_counter("office-fallback-50-50")
                office_sel = select_fallback_office(fallback_counter, offices)

            logger.info("Ticket %s: office=%s (%s)", ticket.guid, office_sel.office.name, office_sel.reason)

            # Step 4: Filter managers by skills
            requirement = determine_required_skills(
                ticket.segment, analysis.ticket_type, analysis.language
            )
            all_managers = await self._managers.get_by_office(office_sel.office.id)
            eligible = [
                m for m in all_managers
                if manager_satisfies(m.skills, m.position, requirement)
            ]

            # If no eligible managers in the selected office, widen search
            if not eligible:
                logger.warning(
                    "Ticket %s: no eligible managers in office %s, widening search",
                    ticket.guid, office_sel.office.name,
                )
                all_managers = await self._managers.get_all()
                eligible = [
                    m for m in all_managers
                    if manager_satisfies(m.skills, m.position, requirement)
                ]

            if not eligible:
                # Last resort: relax skill requirements, keep only position check
                logger.warning(
                    "Ticket %s: no managers with required skills, relaxing to position-only",
                    ticket.guid,
                )
                all_managers = await self._managers.get_all()
                if requirement.min_position == Position.CHIEF_SPECIALIST:
                    eligible = [m for m in all_managers if m.is_chief_specialist()]
                else:
                    eligible = list(all_managers)

            if not eligible:
                return ProcessingResult(
                    ticket_id=ticket.id,
                    ticket_guid=ticket.guid,
                    assigned_manager=None,
                    assigned_office=None,
                    distance_km=None,
                    fallback_used=office_sel.fallback_used,
                    error="No eligible managers found",
                )

            # Step 5: pick TOP-2 by minimal load, then round-robin between them
            eligible_sorted = sorted(eligible, key=lambda m: (m.current_load, m.id))
            top2 = eligible_sorted[:2]

            # rr_key includes requirements so different queues don't interfere
            rr_key = (
                f"office-{office_sel.office.id}|"
                f"vip-{int('VIP' in requirement.required_skills)}|"
                f"lang-{analysis.language.value}|"
                f"type-{analysis.ticket_type.value}|"
                f"chief-{int(requirement.min_position == Position.CHIEF_SPECIALIST)}"
            )

            counter = await self._rr.increment_counter(rr_key)  # atomic: returns old value
            chosen_manager, _ = pick_next(top2, counter)

            # Step 6: Persist assignment
            assignment = Assignment(
                id=None,
                ticket_id=ticket.id,
                manager_id=chosen_manager.id,
                office_id=office_sel.office.id,
                distance_km=office_sel.distance_km,
                assignment_reason=office_sel.reason,
                fallback_used=office_sel.fallback_used,
            )
            await self._assignments.save(assignment)
            await self._managers.increment_load(chosen_manager.id)

            logger.info(
                "Ticket %s → Manager %s (office: %s, distance: %s km)",
                ticket.guid, chosen_manager.name,
                office_sel.office.name, office_sel.distance_km,
            )

            return ProcessingResult(
                ticket_id=ticket.id,
                ticket_guid=ticket.guid,
                assigned_manager=chosen_manager.name,
                assigned_office=office_sel.office.name,
                distance_km=office_sel.distance_km,
                fallback_used=office_sel.fallback_used,
            )

        except Exception as e:
            logger.exception("Error processing ticket %s", ticket.guid)
            return ProcessingResult(
                ticket_id=ticket.id,
                ticket_guid=ticket.guid,
                assigned_manager=None,
                assigned_office=None,
                distance_km=None,
                fallback_used=False,
                error=str(e),
            )


class BatchProcessUseCase:
    """Process all unprocessed tickets."""

    def __init__(
        self,
        process_ticket: ProcessTicketUseCase,
        ticket_repo: TicketRepository,
    ):
        self._process = process_ticket
        self._tickets = ticket_repo

    async def execute(self) -> list[ProcessingResult]:
        """Process all unprocessed tickets and return results."""
        tickets = await self._tickets.get_unprocessed()
        logger.info("Batch processing %d unprocessed tickets", len(tickets))

        results = []
        for ticket in tickets:
            result = await self._process.execute(ticket)
            results.append(result)

        successful = sum(1 for r in results if r.error is None)
        logger.info(
            "Batch complete: %d/%d successful", successful, len(results)
        )
        return results
