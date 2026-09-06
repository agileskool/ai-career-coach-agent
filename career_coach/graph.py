"""Single-agent LangGraph implementation."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from career_coach.prompts import FINALIZER_PROMPT, SYSTEM_PROMPT
from career_coach.schemas import CareerRoadmap, LearnerProfile
from career_coach.state import CareerCoachState
from career_coach.tools import TOOLS


@lru_cache(maxsize=1)
def _model() -> ChatGoogleGenerativeAI:
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=1.0,
        max_retries=2,
    )


def _agent_node(state: CareerCoachState) -> dict:
    """Let the model reason over state and choose whether to call a tool."""

    model_with_tools = _model().bind_tools(TOOLS)
    profile = state.get("learner_profile", {})
    profile_context = (
        "Learner profile supplied by the product UI:\n"
        f"{profile}\n\n"
        "Work toward a recommendation. Use tools where required by your policy."
    )

    response = model_with_tools.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=profile_context)]
        + state.get("messages", [])
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def _route_after_agent(state: CareerCoachState) -> Literal["tools", "finalize"]:
    last_message = state["messages"][-1]
    return "tools" if getattr(last_message, "tool_calls", None) else "finalize"


def _finalize_node(state: CareerCoachState) -> dict:
    """Turn the completed agent run into a typed product contract for the UI."""

    structured_model = _model().with_structured_output(
        schema=CareerRoadmap.model_json_schema(),
        method="json_schema",
    )
    response = structured_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=FINALIZER_PROMPT),
            HumanMessage(content=f"Learner profile: {state.get('learner_profile', {})}"),
            *state.get("messages", []),
        ]
    )
    roadmap = CareerRoadmap.model_validate(response)
    return {
        "final_roadmap": roadmap.model_dump(),
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def build_graph(checkpointer=None):
    """Build the graph. Supplying the checkpointer makes persistence explicit/testable."""

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


# In-memory thread persistence for V1. Replace with Postgres/SQLite for production durability.
career_coach_graph = build_graph(checkpointer=InMemorySaver())


def assess_learner(profile: LearnerProfile, thread_id: str) -> dict:
    """Public application service used by Streamlit or a future API."""

    return career_coach_graph.invoke(
        {
            "learner_profile": profile.model_dump(),
            "messages": [],
            "llm_calls": 0,
        },
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 12,
        },
    )
