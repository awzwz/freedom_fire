"""Google Maps geocoder adapter — implements GeocoderPort."""

from __future__ import annotations

import logging
import httpx

from app.application.ports.geocoder_port import GeocoderPort
from app.config import settings
from app.domain.value_objects.geo_point import GeoPoint

logger = logging.getLogger(__name__)

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

class GoogleMapsAdapter(GeocoderPort):
    """Google Maps implementation of GeocoderPort."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.google_maps_api_key
        self._cache: dict[str, GeoPoint | None] = {}

    async def geocode(self, address: str) -> GeoPoint | None:
        """Geocode address using Google Maps Geocoding API."""
        if not self._api_key:
            logger.warning("Google Maps API key is not set. Skipping geocoding.")
            return None

        cache_key = address.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    GOOGLE_GEOCODE_URL,
                    params={
                        "address": address,
                        "key": self._api_key,
                        "region": "kz",
                        "language": "ru"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data["status"] == "OK":
                    loc = data["results"][0]["geometry"]["location"]
                    point = GeoPoint(latitude=loc["lat"], longitude=loc["lng"])
                    logger.info("Google Maps resolved '%s' → (%f, %f)", address, point.latitude, point.longitude)
                    self._cache[cache_key] = point
                    return point
                
                logger.warning("Google Maps could not resolve '%s': %s", address, data["status"])
                self._cache[cache_key] = None
                return None

        except Exception:
            logger.exception("Google Maps API error for '%s'", address)
            return None
