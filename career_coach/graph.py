"""Single-agent LangGraph implementation."""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from career_coach.model_provider import get_model
from career_coach.prompts import FINALIZER_PROMPT, SYSTEM_PROMPT
from career_coach.schemas import CareerRoadmap, LearnerProfile
from career_coach.state import CareerCoachState
from career_coach.tools import TOOLS, calculate_learning_capacity


def _build_context(state: CareerCoachState) -> str:
    profile = state.get("learner_profile", {})
    assessment_mode = state.get("assessment_mode", "baseline")
    previous_roadmap = state.get("previous_roadmap")
    progress_updates = state.get("progress_updates", [])

    sections = [
        f"Assessment mode: {assessment_mode}",
        "Learner profile supplied by the product UI:\n"
        f"{json.dumps(profile, indent=2, ensure_ascii=False)}",
    ]

    if previous_roadmap:
        sections.append(
            "Previous saved roadmap:\n"
            f"{json.dumps(previous_roadmap, indent=2, ensure_ascii=False)}"
        )

    if progress_updates:
        sections.append(
            "Learner progress updates since the saved plan:\n"
            f"{json.dumps(progress_updates, indent=2, ensure_ascii=False)}"
        )

    sections.append(
        "Work toward a recommendation. Use tools where required by policy and treat "
        "saved progress as evidence to reassess rather than as automatically validated skill."
    )
    return "\n\n".join(sections)


def _agent_node(state: CareerCoachState) -> dict:
    """Let the model reason over state and choose whether to call a tool."""

    model_with_tools = get_model().bind_tools(TOOLS)
    response = model_with_tools.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=_build_context(state))]
        + state.get("messages", [])
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def _route_after_agent(state: CareerCoachState) -> Literal["tools", "finalize"]:
    last_message = state["messages"][-1]
    return "tools" if getattr(last_message, "tool_calls", None) else "finalize"


def _enforce_deterministic_capacity(roadmap: CareerRoadmap, profile: dict) -> CareerRoadmap:
    """Keep product-owned capacity numbers deterministic even if model prose drifts."""

    if not profile:
        return roadmap

    capacity = calculate_learning_capacity.invoke(
        {
            "hours_per_week": int(profile["hours_per_week"]),
            "target_months": int(profile["target_months"]),
        }
    )
    roadmap.feasibility.available_hours = capacity["approximate_total_hours"]
    return roadmap


def _finalize_node(state: CareerCoachState) -> dict:
    """Turn the completed agent run into a typed product contract for the UI."""

    structured_model = get_model().with_structured_output(CareerRoadmap)
    roadmap = structured_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=FINALIZER_PROMPT),
            HumanMessage(content=_build_context(state)),
            *state.get("messages", []),
        ]
    )
    roadmap = _enforce_deterministic_capacity(roadmap, state.get("learner_profile", {}))
    return {
        "final_roadmap": roadmap.model_dump(),
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def build_graph(checkpointer=None):
    """Build the graph. Supplying the checkpointer makes execution state explicit/testable."""

    builder = StateGraph(CareerCoachState)
    builder.add_node("career_agent", _agent_node)
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_node("finalize", _finalize_node)

    builder.add_edge(START, "career_agent")
    builder.add_conditional_edges(
        "career_agent",
        _route_after_agent,
        {"tools": "tools", "finalize": "finalize"},
    )
    builder.add_edge("tools", "career_agent")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)


# Short-term graph checkpointing. Long-term learner state is stored separately in SQLite.
career_coach_graph = build_graph(checkpointer=InMemorySaver())


def assess_learner(
    profile: LearnerProfile,
    thread_id: str,
    *,
    assessment_mode: Literal["baseline", "reassessment"] = "baseline",
    previous_roadmap: dict | None = None,
    progress_updates: list[dict[str, str]] | None = None,
) -> dict:
    """Run a baseline assessment or longitudinal reassessment."""

    return career_coach_graph.invoke(
        {
            "learner_profile": profile.model_dump(),
            "assessment_mode": assessment_mode,
            "previous_roadmap": previous_roadmap,
            "progress_updates": progress_updates or [],
            "messages": [],
            "llm_calls": 0,
        },
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 14,
        },
    )
