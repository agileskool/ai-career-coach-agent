"""Deterministic capabilities the Career Coach agent may choose to use."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from langchain.tools import tool

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "role_blueprints.json"


@lru_cache(maxsize=1)
def _load_role_blueprints() -> dict[str, dict]:
    with _DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


@tool
def get_role_blueprint(target_role: str) -> dict:
    """Get the internal competency blueprint for a target AI role.

    Use this tool before assessing a learner against a target role. The blueprint is
    the product's V1 competency model, not a claim about live job-market demand.

    Args:
        target_role: Target role name, for example 'AI Product Manager'.
    """

    blueprints = _load_role_blueprints()

    if target_role in blueprints:
        return {"matched_role": target_role, **blueprints[target_role]}

    normalized = target_role.strip().lower()
    for role, blueprint in blueprints.items():
        if normalized in role.lower() or role.lower() in normalized:
            return {"matched_role": role, **blueprint}

    return {
        "status": "not_found",
        "available_roles": sorted(blueprints.keys()),
        "instruction": (
            "Do not invent a blueprint. Explain the limitation and use the closest role "
            "only if the learner explicitly accepts it."
        ),
    }


@tool
def calculate_learning_capacity(hours_per_week: int, target_months: int) -> dict:
    """Calculate the learner's approximate study capacity for the target timeline.

    Args:
        hours_per_week: Realistic learning hours available each week.
        target_months: Number of months available for the transition plan.
    """

    if hours_per_week <= 0:
        raise ValueError("hours_per_week must be greater than zero")
    if target_months <= 0:
        raise ValueError("target_months must be greater than zero")

    weeks = round(target_months * 4.345, 1)
    total_hours = round(hours_per_week * weeks)
    return {
        "weeks": weeks,
        "hours_per_week": hours_per_week,
        "approximate_total_hours": total_hours,
        "note": (
            "Capacity is an approximation; actual progress depends on prior knowledge, "
            "practice quality, and project complexity."
        ),
    }


TOOLS = [get_role_blueprint, calculate_learning_capacity]
