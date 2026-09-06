import pytest
from pydantic import ValidationError

from career_coach.schemas import LearnerProfile


def test_learner_profile_normalizes_skills():
    profile = LearnerProfile(
        current_role="Product Owner",
        years_experience=10,
        current_skills=[" Agile ", "", "Stakeholder management"],
        ai_experience="Basic",
        target_role="AI Product Manager",
        target_months=6,
        hours_per_week=8,
    )
    assert profile.current_skills == ["Agile", "Stakeholder management"]


def test_learner_profile_rejects_zero_learning_hours():
    with pytest.raises(ValidationError):
        LearnerProfile(
            current_role="Developer",
            years_experience=5,
            current_skills=["Java"],
            ai_experience="Basic",
            target_role="AI Engineer",
            target_months=6,
            hours_per_week=0,
        )
