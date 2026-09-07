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


def test_service_reassessment_loads_saved_history(monkeypatch, tmp_path):
    repo = CareerRepository(tmp_path / "careerpilot-test.db")
    calls = []

    def fake_assess(profile, thread_id, **kwargs):
        calls.append(kwargs)
        mode = kwargs.get("assessment_mode", "baseline")
        return {
            "final_roadmap": {
                "assessment_mode": mode,
                "executive_summary": f"{mode} result",
                "target_role": profile.target_role,
            },
            "llm_calls": 3,
            "messages": [],
        }

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
