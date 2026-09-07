from career_coach.graph import _enforce_deterministic_capacity
from career_coach.schemas import CareerRoadmap, FeasibilityAssessment


def test_final_output_uses_deterministic_full_plan_capacity():
    roadmap = CareerRoadmap(
        assessment_mode="reassessment",
        executive_summary="Progress recorded.",
        current_position="Product Owner",
        target_role="AI Product Manager",
        transferable_strengths=[],
        priority_gaps=[],
        feasibility=FeasibilityAssessment(
            rating="realistic",
            available_hours=150,
            estimated_required_hours=120,
            explanation="Model incorrectly inferred elapsed time.",
        ),
        roadmap=[],
        first_30_days=[],
        evidence_plan=[],
        assumptions=[],
        progress_summary="Reported progress.",
        next_best_actions=[],
    )

    corrected = _enforce_deterministic_capacity(
        roadmap,
        {"hours_per_week": 8, "target_months": 6},
    )

    assert corrected.feasibility.available_hours == 209
