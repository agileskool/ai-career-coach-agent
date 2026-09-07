from career_coach.graph import (
    _dedupe_progress_updates,
    _enforce_deterministic_capacity,
    _sanitize_previous_roadmap,
)
from career_coach.schemas import CareerRoadmap, FeasibilityAssessment


def _roadmap() -> CareerRoadmap:
    return CareerRoadmap(
        assessment_mode="reassessment",
        executive_summary=(
            "Progress recorded. About 150 hours remaining over 20 weeks. "
            "RAG and evaluation remain priorities."
        ),
        current_position="Product Owner",
        target_role="AI Product Manager",
        transferable_strengths=[],
        priority_gaps=[],
        feasibility=FeasibilityAssessment(
            rating="realistic",
            available_hours=150,
            estimated_required_hours=120,
            explanation="There are 20 weeks left with 150 hours remaining.",
        ),
        roadmap=[],
        first_30_days=[],
        evidence_plan=[],
        assumptions=[],
        progress_summary="Reported progress with 150 hours remaining.",
        next_best_actions=[],
    )


def test_final_output_uses_deterministic_full_plan_capacity():
    corrected = _enforce_deterministic_capacity(
        _roadmap(),
        {"hours_per_week": 8, "target_months": 6},
    )

    assert corrected.feasibility.available_hours == 209
    assert "150 hours remaining" not in corrected.executive_summary
    assert "150 hours remaining" not in corrected.progress_summary
    assert "20 weeks left" not in corrected.feasibility.explanation
    assert any("does not infer elapsed-time" in item for item in corrected.assumptions)


def test_previous_roadmap_drops_old_model_narrative():
    sanitized = _sanitize_previous_roadmap(
        {
            "executive_summary": "Old unsupported claim: 150 hours remaining.",
            "progress_summary": "Completed all LLM fundamentals.",
            "target_role": "AI Product Manager",
            "priority_gaps": [
                {
                    "competency": "RAG",
                    "current_evidence": "Old model inference",
                    "target_expectation": "Working literacy",
                    "priority": "high",
                    "rationale": "Needed for target role",
                }
            ],
            "roadmap": [{"phase": "RAG"}],
            "evidence_plan": ["RAG prototype"],
        }
    )

    assert "executive_summary" not in sanitized
    assert "progress_summary" not in sanitized
    assert "current_evidence" not in sanitized["priority_gaps"][0]
    assert sanitized["roadmap"] == [{"phase": "RAG"}]


def test_duplicate_progress_updates_are_collapsed_for_agent_context():
    updates = [
        {"update_text": "Built a LangGraph agent.", "created_at": "2026-09-01"},
        {"update_text": "  Built   a LangGraph agent. ", "created_at": "2026-09-02"},
        {"update_text": "Added RAG evaluation.", "created_at": "2026-09-03"},
    ]

    deduped = _dedupe_progress_updates(updates)

    assert deduped == [
        {"update_text": "Built a LangGraph agent."},
        {"update_text": "Added RAG evaluation."},
    ]
