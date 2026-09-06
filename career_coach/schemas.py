"""Typed product contracts shared across UI, agent, and tests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LearnerProfile(BaseModel):
    """Structured learner context supplied to the Career Coach."""

    current_role: str = Field(min_length=2)
    years_experience: int = Field(ge=0, le=50)
    current_skills: list[str] = Field(min_length=1)
    ai_experience: str = Field(min_length=2)
    target_role: str = Field(min_length=2)
    target_months: int = Field(ge=1, le=60)
    hours_per_week: int = Field(ge=1, le=80)
    target_market: str = Field(default="Global")
    learning_preferences: str | None = None
    additional_context: str | None = None

    @field_validator("current_skills")
    @classmethod
    def normalize_skills(cls, value: list[str]) -> list[str]:
        cleaned = [skill.strip() for skill in value if skill.strip()]
        if not cleaned:
            raise ValueError("At least one current skill is required.")
        return cleaned


class SkillGap(BaseModel):
    competency: str
    current_evidence: str
    target_expectation: str
    priority: Literal["critical", "high", "medium", "low"]
    rationale: str


class RoadmapPhase(BaseModel):
    phase: str
    objective: str
    topics: list[str]
    evidence_to_produce: list[str]
    estimated_hours: int = Field(ge=1)


class FeasibilityAssessment(BaseModel):
    rating: Literal["realistic", "stretch", "unlikely"]
    available_hours: int
    estimated_required_hours: int
    explanation: str


class CareerRoadmap(BaseModel):
    """Machine-readable final output rendered by the UI."""

    executive_summary: str
    current_position: str
    target_role: str
    transferable_strengths: list[str]
    priority_gaps: list[SkillGap]
    feasibility: FeasibilityAssessment
    roadmap: list[RoadmapPhase]
    first_30_days: list[str]
    evidence_plan: list[str]
    assumptions: list[str]
