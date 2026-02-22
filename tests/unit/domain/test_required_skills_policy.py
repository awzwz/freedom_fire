"""Tests for RequiredSkillsPolicy."""

from app.domain.policies.required_skills import (
    SkillRequirement,
    determine_required_skills,
    manager_satisfies,
)
from app.domain.value_objects.enums import Language, Position, Segment, TicketType

# ─── determine_required_skills ───────────────────────────────────────


def test_vip_segment_requires_vip_skill():
    req = determine_required_skills(Segment.VIP, TicketType.CONSULTATION, Language.RU)
    assert "VIP" in req.required_skills


def test_priority_segment_requires_vip_skill():
    req = determine_required_skills(Segment.PRIORITY, TicketType.CONSULTATION, Language.RU)
    assert "VIP" in req.required_skills


def test_mass_segment_no_vip_skill():
    req = determine_required_skills(Segment.MASS, TicketType.CONSULTATION, Language.RU)
    assert "VIP" not in req.required_skills


def test_data_change_requires_chief_specialist():
    req = determine_required_skills(Segment.MASS, TicketType.DATA_CHANGE, Language.RU)
    assert req.min_position == Position.CHIEF_SPECIALIST


def test_non_data_change_no_position_requirement():
    for tt in TicketType:
        if tt == TicketType.DATA_CHANGE:
            continue
        req = determine_required_skills(Segment.MASS, tt, Language.RU)
        assert req.min_position is None, f"Unexpected min_position for {tt}"


def test_kz_language_requires_kz_skill():
    req = determine_required_skills(Segment.MASS, TicketType.CONSULTATION, Language.KZ)
    assert "KZ" in req.required_skills


def test_eng_language_requires_eng_skill():
    req = determine_required_skills(Segment.MASS, TicketType.CONSULTATION, Language.ENG)
    assert "ENG" in req.required_skills


def test_ru_language_no_language_skill():
    req = determine_required_skills(Segment.MASS, TicketType.CONSULTATION, Language.RU)
    assert "KZ" not in req.required_skills
    assert "ENG" not in req.required_skills


def test_vip_kz_requires_both_skills():
    """VIP ticket in Kazakh should require both VIP and KZ skills."""
    req = determine_required_skills(Segment.VIP, TicketType.COMPLAINT, Language.KZ)
    assert "VIP" in req.required_skills
    assert "KZ" in req.required_skills
    assert len(req.required_skills) == 2


def test_vip_data_change_eng_all_rules():
    """VIP + data-change + English: VIP skill, ENG skill, chief specialist."""
    req = determine_required_skills(Segment.VIP, TicketType.DATA_CHANGE, Language.ENG)
    assert "VIP" in req.required_skills
    assert "ENG" in req.required_skills
    assert req.min_position == Position.CHIEF_SPECIALIST


def test_mass_ru_consultation_empty_requirements():
    """Mass + RU + consultation → no special requirements."""
    req = determine_required_skills(Segment.MASS, TicketType.CONSULTATION, Language.RU)
    assert len(req.required_skills) == 0
    assert req.min_position is None


# ─── manager_satisfies ───────────────────────────────────────────────


def test_manager_satisfies_with_all_skills():
    req = SkillRequirement(required_skills=frozenset({"VIP", "KZ"}), min_position=None)
    assert manager_satisfies({"VIP", "KZ", "ENG"}, Position.SPECIALIST, req) is True


def test_manager_missing_skill():
    req = SkillRequirement(required_skills=frozenset({"VIP"}), min_position=None)
    assert manager_satisfies({"KZ"}, Position.SPECIALIST, req) is False


def test_manager_satisfies_chief_specialist():
    req = SkillRequirement(
        required_skills=frozenset(), min_position=Position.CHIEF_SPECIALIST
    )
    assert manager_satisfies(set(), Position.CHIEF_SPECIALIST, req) is True


def test_manager_not_chief_specialist_fails():
    req = SkillRequirement(
        required_skills=frozenset(), min_position=Position.CHIEF_SPECIALIST
    )
    assert manager_satisfies(set(), Position.SENIOR_SPECIALIST, req) is False
    assert manager_satisfies(set(), Position.SPECIALIST, req) is False


def test_manager_satisfies_empty_requirement():
    """No skills or position required — everyone qualifies."""
    req = SkillRequirement(required_skills=frozenset(), min_position=None)
    assert manager_satisfies(set(), Position.SPECIALIST, req) is True
