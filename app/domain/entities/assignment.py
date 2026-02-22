"""Assignment entity — the result of routing a ticket to a manager."""

from dataclasses import dataclass, field


@dataclass
class Assignment:
    id: int | None
    ticket_id: int
    manager_id: int
    office_id: int
    distance_km: float | None = None
    assignment_reason: str | None = None
    fallback_used: bool = False
    rule_trace: dict | None = field(default=None)

