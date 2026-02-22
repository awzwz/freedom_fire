"""Port interface for geocoding addresses to coordinates."""

from abc import ABC, abstractmethod

from app.domain.value_objects.geo_point import GeoPoint


class GeocoderPort(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> GeoPoint | None:
        """Convert address string to lat/lon coordinates.

        Returns None if the address cannot be resolved.
        """
        ...
