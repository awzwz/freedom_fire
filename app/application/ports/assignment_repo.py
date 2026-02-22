"""Port interface for assignment persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.assignment import Assignment


class AssignmentRepository(ABC):
    @abstractmethod
    async def save(self, assignment: Assignment) -> Assignment:
        ...

    @abstractmethod
    async def get_by_ticket(self, ticket_id: int) -> Assignment | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[Assignment]:
        ...
