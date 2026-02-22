import asyncio
import logging
import sys

from app.adapters.persistence.database import async_session_factory
from app.infrastructure.api.dependencies import get_batch_process_uc, get_process_ticket_uc
from app.adapters.persistence.repositories import SqlTicketRepository, SqlManagerRepository, SqlOfficeRepository, SqlAssignmentRepository, SqlAnalyticsRepository, SqlRoundRobinRepository
from app.application.use_cases.process_ticket import ProcessTicketUseCase, BatchProcessUseCase
from app.adapters.llm.openai_adapter import OpenAIAdapter
from app.adapters.geocoder.nominatim_adapter import NominatimAdapter

logging.basicConfig(level=logging.DEBUG)

async def test():
    async with async_session_factory() as session:
        # manual DI
        llm = OpenAIAdapter()
        geo = NominatimAdapter()
        
        process_uc = ProcessTicketUseCase(
            llm=llm,
            geocoder=geo,
            ticket_repo=SqlTicketRepository(session),
            manager_repo=SqlManagerRepository(session),
            office_repo=SqlOfficeRepository(session),
            assignment_repo=SqlAssignmentRepository(session),
            analytics_repo=SqlAnalyticsRepository(session),
            rr_repo=SqlRoundRobinRepository(session),
        )
        
        batch_uc = BatchProcessUseCase(
            process_ticket=process_uc,
            ticket_repo=SqlTicketRepository(session)
        )
        
        tickets = await SqlTicketRepository(session).get_unprocessed()
        print(f"Unprocessed tickets: {len(tickets)}")
        if not tickets:
            print("No tickets to process")
            return

        t = tickets[0]
        print(f"Processing ticket: {t.id}")
        
        res = await process_uc.execute(t)
        print(f"Result: {res}")
        
        print("Committing...")
        try:
            await session.commit()
            print("Commit successful!")
        except Exception as e:
            print(f"Commit failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(test())
