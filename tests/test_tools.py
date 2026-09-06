from career_coach.tools import calculate_learning_capacity, get_role_blueprint


def test_get_role_blueprint_exact_match():
    result = get_role_blueprint.invoke({"target_role": "AI Product Manager"})
    assert result["matched_role"] == "AI Product Manager"
    assert "technical_literacy" in result["competencies"]


def test_get_role_blueprint_unknown_role_does_not_invent():
    result = get_role_blueprint.invoke({"target_role": "Quantum AI Wizard"})
    assert result["status"] == "not_found"
    assert "available_roles" in result


def test_learning_capacity_is_deterministic():
    result = calculate_learning_capacity.invoke({"hours_per_week": 8, "target_months": 6})
    assert result["approximate_total_hours"] == 209
    assert result["hours_per_week"] == 8
