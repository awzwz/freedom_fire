"""Nominatim geocoder adapter — implements GeocoderPort."""

from __future__ import annotations

import logging

import httpx

from app.application.ports.geocoder_port import GeocoderPort
from app.config import settings
from app.domain.value_objects.geo_point import GeoPoint

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# City centroid fallback: major Kazakhstan cities
CITY_CENTROIDS: dict[str, GeoPoint] = {
    "алматы": GeoPoint(latitude=43.238949, longitude=76.945465),
    "астана": GeoPoint(latitude=51.128207, longitude=71.430411),
    "караганда": GeoPoint(latitude=49.806406, longitude=73.085485),
    "шымкент": GeoPoint(latitude=42.315514, longitude=69.596428),
    "актобе": GeoPoint(latitude=50.283935, longitude=57.166978),
    "тараз": GeoPoint(latitude=42.901183, longitude=71.378309),
    "павлодар": GeoPoint(latitude=52.287430, longitude=76.967454),
    "усть-каменогорск": GeoPoint(latitude=49.948759, longitude=82.627808),
    "семей": GeoPoint(latitude=50.411137, longitude=80.227607),
    "атырау": GeoPoint(latitude=47.106700, longitude=51.903538),
    "костанай": GeoPoint(latitude=53.214773, longitude=63.631557),
    "кызылорда": GeoPoint(latitude=44.842614, longitude=65.502530),
    "актау": GeoPoint(latitude=43.635100, longitude=51.169300),
    "петропавловск": GeoPoint(latitude=54.865559, longitude=69.135552),
    "туркестан": GeoPoint(latitude=43.297222, longitude=68.241389),
    "кокшетау": GeoPoint(latitude=53.283333, longitude=69.383333),
    "талдыкорган": GeoPoint(latitude=45.015833, longitude=78.373611),
    "жезказган": GeoPoint(latitude=47.783333, longitude=67.766667),
    "экибастуз": GeoPoint(latitude=51.723667, longitude=75.322278),
    "темиртау": GeoPoint(latitude=50.054722, longitude=72.964722),
    "нур-султан": GeoPoint(latitude=51.128207, longitude=71.430411),  # old name for Astana
}

# Region centroid fallback (useful for villages not present in OSM search results)
# We map regions to the nearest major city / regional center.
REGION_CENTROIDS: dict[str, GeoPoint] = {
    "акмолинская": CITY_CENTROIDS["кокшетау"],
    "алматинская": CITY_CENTROIDS["алматы"],
    "атырауская": CITY_CENTROIDS["атырау"],
    "актюбинская": CITY_CENTROIDS["актобе"],
    "жамбылская": CITY_CENTROIDS["тараз"],
    "карагандинская": CITY_CENTROIDS["караганда"],
    "костанайская": CITY_CENTROIDS["костанай"],
    "кызылординская": CITY_CENTROIDS["кызылорда"],
    "мангистауская": CITY_CENTROIDS["актау"],
    "павлодарская": CITY_CENTROIDS["павлодар"],
    "северо-казахстанская": CITY_CENTROIDS["петропавловск"],
    "туркестанская": CITY_CENTROIDS["туркестан"],
    "восточно-казахстанская": CITY_CENTROIDS["усть-каменогорск"],
}


class NominatimAdapter(GeocoderPort):
    """Nominatim geocoding with city centroid fallback and caching."""

    def __init__(self, user_agent: str | None = None, timeout: float = 10.0):
        self._user_agent = user_agent or settings.geocoder_user_agent
        self._timeout = timeout
        self._cache: dict[str, GeoPoint | None] = {}

    async def geocode(self, address: str) -> GeoPoint | None:
        """Geocode an address string to GeoPoint.

        Strategy:
        1. Check in-memory cache
        2. Try Nominatim API
        3. Fall back to city centroid lookup
        """
        cache_key = address.strip().lower()

        if cache_key in self._cache:
            logger.debug("Cache hit for '%s'", address)
            return self._cache[cache_key]

        # Try Nominatim first
        point = await self._nominatim_lookup(address)
        if point:
            self._cache[cache_key] = point
            return point

        # Fallback: try to match city name in address
        point = self._city_centroid_lookup(address)
        if point:
            self._cache[cache_key] = point
            return point

        # Region centroid fallback
        point = self._region_centroid_lookup(address)
        self._cache[cache_key] = point
        return point

    async def _nominatim_lookup(self, address: str) -> GeoPoint | None:
        """Query Nominatim API."""
        try:
            async with httpx.AsyncClient() as client:
                for query in self._build_queries(address):
                    response = await client.get(
                        NOMINATIM_URL,
                        params={
                            "q": query,
                            "format": "json",
                            "limit": 1,
                            "countrycodes": "kz",
                        },
                        headers={"User-Agent": self._user_agent},
                        timeout=self._timeout,
                    )
                    response.raise_for_status()
                    results = response.json()

                    if results and len(results) > 0:
                        lat = float(results[0]["lat"])
                        lon = float(results[0]["lon"])
                        logger.info("Nominatim resolved '%s' (q='%s') → (%f, %f)", address, query, lat, lon)
                        return GeoPoint(latitude=lat, longitude=lon)

                logger.info("Nominatim returned no results for '%s'", address)
                return None

        except Exception:
            logger.exception("Nominatim API error for '%s'", address)
            return None

    @staticmethod
    def _city_centroid_lookup(address: str) -> GeoPoint | None:
        """Try to match a city name in the address for centroid fallback."""
        address_lower = address.lower()
        for city, point in CITY_CENTROIDS.items():
            if city in address_lower:
                logger.info("City centroid fallback: '%s' → %s", address, city)
                return point
        logger.warning("No geocoding result for '%s'", address)
        return None

    @staticmethod
    def _region_centroid_lookup(address: str) -> GeoPoint | None:
        address_lower = address.lower()
        for region, point in REGION_CENTROIDS.items():
            if region in address_lower:
                logger.info("Region centroid fallback: '%s' → %s", address, region)
                return point
        return None

    @staticmethod
    def _build_queries(address: str) -> list[str]:
        """Build a few query variants for better hit rate.

        1) full address
        2) without house number / street keywords (more robust for villages)
        """
        q1 = address.strip()
        # Remove common street prefixes and house numbers for a broader query
        q2 = (
            q1.lower()
            .replace("ул.", "")
            .replace("улица", "")
            .replace("пр-т", "")
            .replace("проспект", "")
        )
        q2 = " ".join([p for p in q2.replace(",", " ").split() if not any(ch.isdigit() for ch in p)])
        q2 = q2.strip()
        queries = [q1]
        if q2 and q2 != q1.lower():
            queries.append(q2)
        return queries
