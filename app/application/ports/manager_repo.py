"""Port interface for manager persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.manager import Manager


class ManagerRepository(ABC):
    @abstractmethod
    async def save(self, manager: Manager) -> Manager:
        ...

    @abstractmethod
    async def get_by_id(self, manager_id: int) -> Manager | None:
        ...

    @abstractmethod
    async def get_by_office(self, office_id: int) -> list[Manager]:
        ...

    @abstractmethod
    async def get_all(self) -> list[Manager]:
        ...

    @abstractmethod
    async def increment_load(self, manager_id: int) -> None:
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Manager | None:
        ...
