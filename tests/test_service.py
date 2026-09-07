import pytest

from career_coach.persistence import CareerRepository
from career_coach.schemas import LearnerProfile, ProgressUpdate
from career_coach.service import create_initial_assessment, reassess_progress


def _profile() -> LearnerProfile:
    return LearnerProfile(
        current_role="Product Owner",
        years_experience=12,
        current_skills=["Product strategy", "Agile"],
        ai_experience="Basic GenAI experience",
        target_role="AI Product Manager",
        target_months=6,
        hours_per_week=8,
    )


def _result(profile, mode: str) -> dict:
    return {
        "final_roadmap": {
            "assessment_mode": mode,
            "executive_summary": f"{mode} result",
            "target_role": profile.target_role,
        },
        "llm_calls": 3,
        "messages": [],
    }


def test_service_reassessment_loads_saved_history(monkeypatch, tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    calls = []

    def fake_assess(profile, thread_id, **kwargs):
        calls.append(kwargs)
        return _result(profile, kwargs.get("assessment_mode", "baseline"))

    monkeypatch.setattr("career_coach.service.assess_learner", fake_assess)

    baseline = create_initial_assessment(_profile(), repo)
    learner_id = baseline["learner_id"]

    reassessed = reassess_progress(
        learner_id,
        ProgressUpdate(update_text="Built a RAG prototype with citations and evaluation."),
        repo,
    )

    assert calls[0]["assessment_mode"] == "baseline"
    assert calls[1]["assessment_mode"] == "reassessment"
    assert calls[1]["previous_roadmap"]["executive_summary"] == "baseline result"
    assert "RAG prototype" in calls[1]["progress_updates"][0]["update_text"]
    assert reassessed["result"]["final_roadmap"]["assessment_mode"] == "reassessment"
    assert repo.get_latest_roadmap(learner_id)["executive_summary"] == "reassessment result"
    assert len(repo.list_progress_updates(learner_id)) == 1


def test_failed_reassessment_does_not_persist_progress(monkeypatch, tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")

    def baseline_assess(profile, thread_id, **kwargs):
        return _result(profile, kwargs.get("assessment_mode", "baseline"))

    monkeypatch.setattr("career_coach.service.assess_learner", baseline_assess)
    learner_id = create_initial_assessment(_profile(), repo)["learner_id"]
    update = ProgressUpdate(update_text="Built an evaluation harness with ten gold cases.")

    def failing_assess(profile, thread_id, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("career_coach.service.assess_learner", failing_assess)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        reassess_progress(learner_id, update, repo)

    assert repo.list_progress_updates(learner_id) == []

    monkeypatch.setattr("career_coach.service.assess_learner", baseline_assess)
    reassess_progress(learner_id, update, repo)
    assert len(repo.list_progress_updates(learner_id)) == 1


def test_legacy_orphan_progress_can_be_retried(monkeypatch, tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")

    def fake_assess(profile, thread_id, **kwargs):
        return _result(profile, kwargs.get("assessment_mode", "baseline"))

    monkeypatch.setattr("career_coach.service.assess_learner", fake_assess)
    learner_id = create_initial_assessment(_profile(), repo)["learner_id"]
    update_text = "Built a LangGraph agent with tools and SQLite persistence."

    # Simulate the V0.2 bug: progress was saved but its reassessment never completed.
    repo.add_progress_update(learner_id, update_text)
    assert len(repo.list_progress_updates(learner_id)) == 1

    reassess_progress(learner_id, ProgressUpdate(update_text=update_text), repo)

    # Retry consumes the orphan without adding a second copy.
    assert len(repo.list_progress_updates(learner_id)) == 1
    assert repo.get_latest_roadmap(learner_id)["assessment_mode"] == "reassessment"


def test_duplicate_of_successfully_assessed_progress_is_rejected(monkeypatch, tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    calls = []

    def fake_assess(profile, thread_id, **kwargs):
        calls.append(kwargs)
        return _result(profile, kwargs.get("assessment_mode", "baseline"))

    monkeypatch.setattr("career_coach.service.assess_learner", fake_assess)
    learner_id = create_initial_assessment(_profile(), repo)["learner_id"]
    update = ProgressUpdate(update_text="Built a RAG prototype with citations.")

    reassess_progress(learner_id, update, repo)
    calls_after_success = len(calls)

    with pytest.raises(ValueError, match="identical to one already assessed"):
        reassess_progress(learner_id, update, repo)

    assert len(calls) == calls_after_success
    assert len(repo.list_progress_updates(learner_id)) == 1
