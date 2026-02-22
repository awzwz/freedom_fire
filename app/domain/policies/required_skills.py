"""RequiredSkillsPolicy — determines what skills / position a manager must have."""

from dataclasses import dataclass

from app.domain.value_objects.enums import Language, Position, Segment, TicketType


@dataclass(frozen=True)
class SkillRequirement:
    """Result of the policy evaluation."""

    required_skills: frozenset[str]
    min_position: Position | None  # None = any position is fine


def determine_required_skills(
    segment: Segment,
    ticket_type: TicketType,
    language: Language,
) -> SkillRequirement:
    """Pure function: given ticket attributes, return skill/position requirements.

    Business rules:
      1. VIP / Priority segment  →  manager must have "VIP" skill.
      2. ticket_type == "Смена данных"  →  only Главный специалист can handle.
      3. language == KZ  →  manager must have "KZ" skill.
      4. language == ENG  →  manager must have "ENG" skill.
      5. language == RU  →  no extra language skill required.

    Rules are *additive*: a VIP ticket in Kazakh requires both "VIP" and "KZ".
    """
    skills: set[str] = set()
    min_position: Position | None = None

    # Rule 1 — VIP / Priority segment
    if segment in (Segment.VIP, Segment.PRIORITY):
        skills.add("VIP")

    # Rule 2 — Data-change tickets require chief specialist
    if ticket_type == TicketType.DATA_CHANGE:
        min_position = Position.CHIEF_SPECIALIST

    # Rule 3/4 — Language-specific skill
    if language == Language.KZ:
        skills.add("KZ")
    elif language == Language.ENG:
        skills.add("ENG")
    # RU — no extra skill required

    return SkillRequirement(
        required_skills=frozenset(skills),
        min_position=min_position,
    )


def manager_satisfies(
    manager_skills: set[str],
    manager_position: Position,
    requirement: SkillRequirement,
) -> bool:
    """Check whether a manager meets the requirement."""
    # All required skills must be present
    if not requirement.required_skills.issubset(manager_skills):
        return False

    # Position check
    if requirement.min_position is not None:
        if requirement.min_position == Position.CHIEF_SPECIALIST:
            if manager_position != Position.CHIEF_SPECIALIST:
                return False

    return True
