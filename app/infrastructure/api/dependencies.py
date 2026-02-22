"""FastAPI dependency injection — wires adapters into use cases."""

from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.geocoder.nominatim_adapter import NominatimAdapter
from app.adapters.geocoder.google_maps_adapter import GoogleMapsAdapter
from app.adapters.llm.openai_adapter import OpenAIAdapter
from app.adapters.persistence.database import get_session
from app.config import settings
from app.adapters.persistence.repositories import (
    SqlAnalyticsRepository,
    SqlAssignmentRepository,
    SqlManagerRepository,
    SqlOfficeRepository,
    SqlRoundRobinRepository,
    SqlTicketRepository,
)
from app.application.use_cases.analyze_ticket import AnalyzeTicketUseCase
from app.application.use_cases.process_ticket import (
    BatchProcessUseCase,
    ProcessTicketUseCase,
)

# Re-export session dependency
get_db_session = get_session

# Singleton adapters (stateless or with internal caching)
_llm_adapter = OpenAIAdapter()

if settings.google_maps_api_key:
    _geocoder_adapter = GoogleMapsAdapter()
    logger = logging.getLogger(__name__)
    logger.info("Using Google Maps for geocoding")
else:
    _geocoder_adapter = NominatimAdapter()


def get_ticket_repo(session: AsyncSession = Depends(get_session)) -> SqlTicketRepository:
    return SqlTicketRepository(session)


def get_manager_repo(session: AsyncSession = Depends(get_session)) -> SqlManagerRepository:
    return SqlManagerRepository(session)


def get_office_repo(session: AsyncSession = Depends(get_session)) -> SqlOfficeRepository:
    return SqlOfficeRepository(session)


def get_assignment_repo(session: AsyncSession = Depends(get_session)) -> SqlAssignmentRepository:
    return SqlAssignmentRepository(session)


def get_analytics_repo(session: AsyncSession = Depends(get_session)) -> SqlAnalyticsRepository:
    return SqlAnalyticsRepository(session)


def get_rr_repo(session: AsyncSession = Depends(get_session)) -> SqlRoundRobinRepository:
    return SqlRoundRobinRepository(session)


def get_process_ticket_uc(
    session: AsyncSession = Depends(get_session),
) -> ProcessTicketUseCase:
    return ProcessTicketUseCase(
        llm=_llm_adapter,
        geocoder=_geocoder_adapter,
        ticket_repo=SqlTicketRepository(session),
        manager_repo=SqlManagerRepository(session),
        office_repo=SqlOfficeRepository(session),
        assignment_repo=SqlAssignmentRepository(session),
        analytics_repo=SqlAnalyticsRepository(session),
        rr_repo=SqlRoundRobinRepository(session),
    )


def get_batch_process_uc(
    session: AsyncSession = Depends(get_session),
) -> BatchProcessUseCase:
    process_uc = ProcessTicketUseCase(
        llm=_llm_adapter,
        geocoder=_geocoder_adapter,
        ticket_repo=SqlTicketRepository(session),
        manager_repo=SqlManagerRepository(session),
        office_repo=SqlOfficeRepository(session),
        assignment_repo=SqlAssignmentRepository(session),
        analytics_repo=SqlAnalyticsRepository(session),
        rr_repo=SqlRoundRobinRepository(session),
    )
    return BatchProcessUseCase(
        process_ticket=process_uc,
        ticket_repo=SqlTicketRepository(session),
    )


def get_analyze_ticket_uc() -> AnalyzeTicketUseCase:
    return AnalyzeTicketUseCase(llm=_llm_adapter)
