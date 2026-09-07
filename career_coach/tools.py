"""Deterministic capabilities the Career Coach agent may choose to use."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from langchain.tools import tool

_ROOT = Path(__file__).resolve().parent.parent
_ROLE_DATA_FILE = _ROOT / "data" / "role_blueprints.json"
_PATHWAY_DATA_FILE = _ROOT / "data" / "transformation_pathways.json"


@lru_cache(maxsize=1)
def _load_role_blueprints() -> dict[str, dict]:
    with _ROLE_DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_transformation_pathways() -> dict:
    with _PATHWAY_DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


@tool
def get_role_blueprint(target_role: str) -> dict:
    """Get the internal competency blueprint for a target AI role.

    Use this tool before assessing a learner against a target role. The blueprint is
    the product's internal competency model, not a claim about live job-market demand.

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


@tool
def get_transformation_pathway(
    current_role: str,
    target_role: str,
    years_experience: int,
) -> dict:
    """Get CareerPilot's internal transformation methodology for a career transition.

    This tool encodes the product's sequencing principles so the model does not invent
    a generic learning path from model memory alone.

    Args:
        current_role: Learner's current professional role.
        target_role: Learner's target AI role.
        years_experience: Total years of professional experience.
    """

    data = _load_transformation_pathways()
    normalized_current = current_role.strip().lower()
    normalized_target = target_role.strip().lower()

    best_match: tuple[str, dict] | None = None
    for pathway_name, pathway in data["pathways"].items():
        target_match = any(
            target.lower() == normalized_target for target in pathway.get("target_roles", [])
        )
        source_match = any(
            keyword in normalized_current for keyword in pathway.get("source_role_keywords", [])
        )
        if target_match and source_match:
            best_match = (pathway_name, pathway)
            break
        if target_match and best_match is None:
            best_match = (pathway_name, pathway)

    if best_match is None:
        pathway_name = "fallback"
        pathway = data["fallback"]
    else:
        pathway_name, pathway = best_match

    return {
        "matched_pathway": pathway_name,
        "experienced_professional": years_experience >= 5,
        "principles": data["principles"],
        "positioning": pathway["positioning"],
        "recommended_phases": pathway["phases"],
        "anti_patterns": pathway["anti_patterns"],
    }


TOOLS = [
    get_role_blueprint,
    calculate_learning_capacity,
    get_transformation_pathway,
]
