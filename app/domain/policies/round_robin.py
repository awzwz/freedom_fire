"""RoundRobinPolicy — deterministic load-balanced manager selection."""

from __future__ import annotations

from app.domain.entities.manager import Manager


def pick_next(candidates: list[Manager], counter: int) -> tuple[Manager, int]:
    """Deterministic round-robin pick from a sorted candidate list.

    1. Sort candidates by (current_load ASC, id ASC) for stable ordering.
    2. Use *counter mod len(candidates)* to select the index.
    3. Return the chosen manager and the incremented counter.

    Args:
        candidates: non-empty list of eligible managers.
        counter: current round-robin counter value.

    Returns:
        (chosen_manager, new_counter)

    Raises:
        ValueError: if candidates list is empty.
    """
    if not candidates:
        raise ValueError("Cannot pick from an empty candidate list")

    # Stable sort: lowest load first, then by id for determinism
    sorted_candidates = sorted(candidates, key=lambda m: (m.current_load, m.id))

    index = counter % len(sorted_candidates)
    chosen = sorted_candidates[index]

    return chosen, counter + 1
