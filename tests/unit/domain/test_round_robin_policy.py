"""Tests for RoundRobinPolicy."""

import pytest

from app.domain.entities.manager import Manager
from app.domain.policies.round_robin import pick_next
from app.domain.value_objects.enums import Position


def _mgr(mid: int, load: int = 0) -> Manager:
    return Manager(
        id=mid, name=f"M{mid}", position=Position.SPECIALIST,
        office_id=1, skills=set(), current_load=load,
    )


def test_pick_single_candidate():
    m = _mgr(1)
    chosen, new_counter = pick_next([m], 0)
    assert chosen.id == 1
    assert new_counter == 1


def test_pick_alternates_between_two():
    """Counter 0 → first, counter 1 → second, counter 2 → first again."""
    candidates = [_mgr(1), _mgr(2)]
    ids = []
    counter = 0
    for _ in range(4):
        chosen, counter = pick_next(candidates, counter)
        ids.append(chosen.id)
    assert ids == [1, 2, 1, 2]


def test_pick_three_candidates_cycles():
    candidates = [_mgr(1), _mgr(2), _mgr(3)]
    ids = []
    counter = 0
    for _ in range(6):
        chosen, counter = pick_next(candidates, counter)
        ids.append(chosen.id)
    assert ids == [1, 2, 3, 1, 2, 3]


def test_pick_sorts_by_load_then_id():
    """Manager with lower load should come first in the sort order."""
    m1 = _mgr(1, load=5)
    m2 = _mgr(2, load=0)
    m3 = _mgr(3, load=0)
    chosen, _ = pick_next([m1, m2, m3], 0)
    # m2 and m3 have load=0, m2 has lower id → m2 is first
    assert chosen.id == 2


def test_pick_equal_load_sorted_by_id():
    m3 = _mgr(3, load=0)
    m1 = _mgr(1, load=0)
    m2 = _mgr(2, load=0)
    # Regardless of input order, sorted by id
    chosen, _ = pick_next([m3, m1, m2], 0)
    assert chosen.id == 1


def test_pick_empty_raises():
    with pytest.raises(ValueError, match="empty candidate list"):
        pick_next([], 0)


def test_counter_wraps_around():
    """Large counter value should still work via modulo."""
    candidates = [_mgr(1), _mgr(2)]
    chosen, new_counter = pick_next(candidates, 1000)
    assert chosen.id == 1  # 1000 % 2 == 0 → first candidate
    assert new_counter == 1001


def test_pick_respects_load_ordering_across_rounds():
    """Simulate load changes between rounds."""
    m1 = _mgr(1, load=0)
    m2 = _mgr(2, load=0)

    # Round 1 — both at load 0, counter=0 picks m1
    chosen, counter = pick_next([m1, m2], 0)
    assert chosen.id == 1

    # Simulate m1 got a ticket, load increases
    m1.current_load = 1

    # Round 2 — m2 has lower load now, sort puts m2 first
    chosen, counter = pick_next([m1, m2], 0)
    assert chosen.id == 2
