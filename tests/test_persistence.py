import pytest

from career_coach.persistence import CareerRepository
from career_coach.schemas import LearnerProfile


def _profile() -> LearnerProfile:
    return LearnerProfile(
        current_role="Product Owner",
        years_experience=12,
        current_skills=["Product strategy", "Agile"],
        ai_experience="Built one small LLM app",
        target_role="AI Product Manager",
        target_months=6,
        hours_per_week=8,
    )


def test_repository_persists_profile_roadmap_and_progress(tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    learner_id = repo.create_learner(_profile())

    assert repo.learner_exists(learner_id)
    assert repo.get_latest_profile(learner_id).current_role == "Product Owner"

    repo.save_assessment(
        learner_id,
        {"executive_summary": "Baseline roadmap", "target_role": "AI Product Manager"},
        llm_calls=3,
    )
    repo.add_progress_update(learner_id, "Built a RAG prototype and pushed it to GitHub.")

    assert repo.get_latest_roadmap(learner_id)["executive_summary"] == "Baseline roadmap"
    updates = repo.list_progress_updates(learner_id)
    assert len(updates) == 1
    assert "RAG prototype" in updates[0]["update_text"]

    history = repo.get_history_summary(learner_id)
    assert history["learner_id"] == learner_id
    assert history["profile"]["target_role"] == "AI Product Manager"


def test_repository_rejects_identical_progress_update(tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    learner_id = repo.create_learner(_profile())
    progress = "Built a LangGraph agent with SQLite persistence."

    repo.add_progress_update(learner_id, progress)

    with pytest.raises(ValueError, match="identical"):
        repo.add_progress_update(learner_id, progress)

    assert len(repo.list_progress_updates(learner_id)) == 1


def test_repository_returns_none_for_unknown_learner(tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    assert repo.get_history_summary("missing-id") is None
