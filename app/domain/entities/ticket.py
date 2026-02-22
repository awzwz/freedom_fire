"""Ticket entity — a customer request received during off-hours."""

from dataclasses import dataclass
from datetime import date

from app.domain.value_objects.enums import GeoStatus, Segment
from app.domain.value_objects.geo_point import GeoPoint


@dataclass
class Ticket:
    id: int | None
    guid: str
    gender: str | None
    birth_date: date | None
    description: str | None
    attachments: str | None
    segment: Segment
    country: str | None
    region: str | None
    city: str | None
    street: str | None
    building: str | None
    client_location: GeoPoint | None = None
    geo_status: GeoStatus = GeoStatus.PENDING

    def build_address_string(self) -> str | None:
        """Build a structured geocoding query for Nominatim.

        Format: "Kazakhstan, {region}, {city}, {street} {house}"
        Street and building are combined into a single part for better
        geocoding accuracy.
        """
        # Combine street + building into one part
        street_part = " ".join(
            p.strip() for p in [self.street, self.building] if p and p.strip()
        ) or None

        parts = [
            self.country or "Казахстан",
            self.region,
            self.city,
            street_part,
        ]
        non_empty = [p.strip() for p in parts if p and p.strip()]
        return ", ".join(non_empty) if len(non_empty) > 1 else None

    def is_address_known(self) -> bool:
        return self.client_location is not None

    def is_domestic(self) -> bool:
        if self.country:
            return self.country.strip().lower() == "казахстан"
            
        # If country is missing, try to infer it from city or region
        # Comprehensive dictionary of Kazakhstani cities/regions (Cyrillic & Latin/Translit)
        kz_identifiers = {
            # Major cities
            "алматы", "almaty", "астана", "astana", "нур-султан", "nur-sultan", 
            "шымкент", "shymkent", "караганда", "karaganda", "qaraghandy",
            "актобе", "aktobe", "aqtobe", "тараз", "taraz", "павлодар", "pavlodar",
            "усть-каменогорск", "ust-kamenogorsk", "oskemen", "семей", "semey",
            "атырау", "atyrau", "костанай", "kostanay", "кызылорда", "kyzylorda",
            "актау", "aktau", "aqtau", "уральск", "uralsk", "oral", 
            "петропавловск", "petropavlovsk", "petropavl", "туркестан", "turkestan",
            "кокшетау", "kokshetau", "талдыкорган", "taldykorgan", "жезказган", "zhezkazgan",
            "экибастуз", "ekibastuz", "темиртау", "temirtau", "рудный", "rudny",
            
            # Regions
            "акмолинская", "akmola", "алматинская", "almaty obl", "атырауская", "atyrau obl",
            "актюбинская", "aktobe obl", "жамбылская", "zhambyl", "карагандинская", "karaganda obl",
            "костанайская", "kostanay obl", "кызылординская", "kyzylorda obl", 
            "мангистауская", "mangystau", "mangystau obl.", "павлодарская", "pavlodar obl",
            "северо-казахстанская", "sko", "туркестанская", "turkestan obl", 
            "восточно-казахстанская", "vko", "западная", "zko", "абайская", "abai",
            "улытауская", "ulytau", "жетысуская", "zhetysu"
        }
        
        city_norm = self.city.strip().lower() if self.city else ""
        region_norm = self.region.strip().lower() if self.region else ""
        
        # Check exact matches or if the known identifier is a substring (e.g. "mangystau obl." contains "mangystau")
        for identifier in kz_identifiers:
            if (city_norm and identifier in city_norm) or \
               (region_norm and identifier in region_norm):
                return True
                
        return False

    def requires_vip_handling(self) -> bool:
        return self.segment in (Segment.VIP, Segment.PRIORITY)
