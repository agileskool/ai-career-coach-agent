"""LangGraph state definition."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class CareerCoachState(TypedDict, total=False):
    """Shared working state that flows through the graph."""

    messages: Annotated[list[BaseMessage], operator.add]
    learner_profile: dict[str, Any]
    llm_calls: int
    final_roadmap: dict[str, Any]
