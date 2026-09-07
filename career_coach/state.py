"""LangGraph state definition."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class CareerCoachState(TypedDict, total=False):
    """Shared working state that flows through one agent execution."""

    messages: Annotated[list[BaseMessage], operator.add]
    learner_profile: dict[str, Any]
    assessment_mode: Literal["baseline", "reassessment"]
    previous_roadmap: dict[str, Any] | None
    progress_updates: list[dict[str, str]]
    llm_calls: int
    final_roadmap: dict[str, Any]
