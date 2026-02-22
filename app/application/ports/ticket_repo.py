"""Port interface for ticket persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.ticket import Ticket


class TicketRepository(ABC):
    @abstractmethod
    async def save(self, ticket: Ticket) -> Ticket:
        ...

    @abstractmethod
    async def get_by_id(self, ticket_id: int) -> Ticket | None:
        ...

    @abstractmethod
    async def get_by_guid(self, guid: str) -> Ticket | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[Ticket]:
        ...

    @abstractmethod
    async def get_unprocessed(self) -> list[Ticket]:
        """Return tickets that don't have an AI analysis yet."""
        ...

    @abstractmethod
    async def update(self, ticket: Ticket) -> Ticket:
        ...
