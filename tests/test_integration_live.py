import os
import uuid

import pytest

from career_coach.graph import assess_learner
from career_coach.schemas import LearnerProfile


@pytest.mark.skipif(
    not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    reason="Live Gemini integration test requires an API key",
)
def test_live_agent_returns_structured_roadmap():
    profile = LearnerProfile(
        current_role="Product Owner",
        years_experience=12,
        current_skills=["Product strategy", "Agile", "Stakeholder management"],
        ai_experience="Basic GenAI usage",
        target_role="AI Product Manager",
        target_months=6,
        hours_per_week=8,
    )
    result = assess_learner(profile, str(uuid.uuid4()))
    assert result["final_roadmap"]["target_role"]
    assert result["final_roadmap"]["roadmap"]
