"""Manager entity — an employee who handles tickets."""

from dataclasses import dataclass, field

from app.domain.value_objects.enums import Position


@dataclass
class Manager:
    id: int | None
    name: str
    position: Position
    office_id: int
    skills: set[str] = field(default_factory=set)
    current_load: int = 0

    def has_skill(self, skill: str) -> bool:
        return skill in self.skills

    def is_chief_specialist(self) -> bool:
        return self.position == Position.CHIEF_SPECIALIST
