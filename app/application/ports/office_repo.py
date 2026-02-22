"""Port interface for office persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.office import Office


class OfficeRepository(ABC):
    @abstractmethod
    async def save(self, office: Office) -> Office:
        ...

    @abstractmethod
    async def get_by_id(self, office_id: int) -> Office | None:
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Office | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[Office]:
        ...
