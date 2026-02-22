"""Port interface for round-robin state persistence."""

from abc import ABC, abstractmethod


class RoundRobinRepository(ABC):
    @abstractmethod
    async def get_counter(self, rr_key: str) -> int:
        """Get the current counter for the given RR key. Creates entry if missing."""
        ...

    @abstractmethod
    async def increment_counter(self, rr_key: str) -> int:
        """Atomically increment the counter and return the OLD value (before increment).

        Must use row-level locking (SELECT ... FOR UPDATE) for safety.
        """
        ...
