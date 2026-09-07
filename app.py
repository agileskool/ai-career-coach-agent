"""Streamlit interface for the AI Career Coach showcase."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from career_coach.model_provider import DEFAULT_MODEL
from career_coach.presentation import build_execution_trace
from career_coach.schemas import CareerRoadmap, LearnerProfile, ProgressUpdate
from career_coach.service import (
    create_initial_assessment,
    load_learner_context,
    reassess_progress,
)

load_dotenv()

st.set_page_config(page_title="CareerPilot AI", page_icon="🧭", layout="wide")


def _require_api_key() -> None:
    if not os.getenv("NVIDIA_API_KEY"):
        st.error("Set NVIDIA_API_KEY before running the live agent.")
        st.stop()


def _render_roadmap(result: dict, learner_id: str | None = None) -> None:
    roadmap = CareerRoadmap.model_validate(result["final_roadmap"])

    st.success(
        "Reassessment complete"
        if roadmap.assessment_mode == "reassessment"
        else "Assessment complete"
    )
    if learner_id:
        st.caption("CareerPilot learner ID — keep this to return to the saved career state")
        st.code(learner_id, language=None)

    if roadmap.progress_summary:
        st.subheader("Progress since previous plan")
        st.write(roadmap.progress_summary)

    st.subheader("Executive assessment")
    st.write(roadmap.executive_summary)

    c1, c2, c3 = st.columns(3)
    c1.metric("Target role", roadmap.target_role)
    c2.metric("Timeline rating", roadmap.feasibility.rating.title())
    c3.metric("Available hours", roadmap.feasibility.available_hours)

    st.subheader("Transferable strengths")
    for strength in roadmap.transferable_strengths:
        st.markdown(f"- {strength}")

    st.subheader("Priority gaps")
    st.dataframe(
        [gap.model_dump() for gap in roadmap.priority_gaps],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Learning roadmap")
    for phase in roadmap.roadmap:
        with st.expander(f"{phase.phase} · ~{phase.estimated_hours} hours", expanded=True):
            st.write(phase.objective)
            st.markdown("**Topics**")
            st.markdown("\n".join(f"- {topic}" for topic in phase.topics))
            st.markdown("**Evidence to produce**")
            st.markdown("\n".join(f"- {item}" for item in phase.evidence_to_produce))

    st.subheader("Immediate actions")
    actions = roadmap.next_best_actions or roadmap.first_30_days
    for index, item in enumerate(actions, start=1):
        st.write(f"{index}. {item}")

    with st.expander("Agent execution trace"):
        st.caption(
            "Shows observable tool requests/results only; hidden model reasoning is not exposed."
        )
        st.json(build_execution_trace(result.get("messages", [])))
        st.caption(f"LLM calls in this run: {result.get('llm_calls', 0)}")


st.title("CareerPilot AI")
st.caption("A persistent, tool-using AI career agent for evidence-based career transitions")

with st.sidebar:
    st.subheader("Agent architecture")
    st.markdown(
        "**LangGraph** manages in-run state and routing.  \n"
        "**NVIDIA Nemotron** performs judgement.  \n"
        "**Tools** provide role/capacity/methodology evidence.  \n"
        "**SQLite** preserves learner career state across sessions."
    )
    st.caption(f"Model: {os.getenv('NVIDIA_MODEL', DEFAULT_MODEL)}")
    st.caption("V0.2 · Continuous career state")

new_tab, returning_tab = st.tabs(["New learner assessment", "Update progress / reassess"])

with new_tab:
    with st.form("career_assessment"):
        col1, col2 = st.columns(2)
        with col1:
            current_role = st.text_input("Current role", value="Product Owner")
            years_experience = st.number_input("Years of experience", 0, 50, 12)
            current_skills_text = st.text_area(
                "Current skills (comma-separated)",
                value="Product strategy, stakeholder management, Agile delivery, business analysis",
            )
            ai_experience = st.text_area(
                "Current AI experience",
                value=(
                    "Uses general-purpose GenAI assistants; understands basic GenAI concepts "
                    "but has limited hands-on agent engineering."
                ),
            )
            target_market = st.text_input("Target market", value="US / Global")

        with col2:
            target_role = st.selectbox(
                "Target AI role",
                ["AI Product Manager", "GenAI Engineer", "AI Engineer", "AI Solution Architect"],
            )
            target_months = st.number_input("Target timeline (months)", 1, 60, 6)
            hours_per_week = st.number_input("Learning hours per week", 1, 80, 8)
            learning_preferences = st.text_area(
                "Learning preferences",
                value="Hands-on projects, guided learning, interview-ready explanations",
            )
            additional_context = st.text_area(
                "Additional career context",
                value="Wants to reuse existing experience rather than restart as a fresher.",
            )

        submitted = st.form_submit_button("Create learner + run assessment", type="primary")

    if submitted:
        _require_api_key()
        profile = LearnerProfile(
            current_role=current_role,
            years_experience=int(years_experience),
            current_skills=[skill.strip() for skill in current_skills_text.split(",")],
            ai_experience=ai_experience,
            target_role=target_role,
            target_months=int(target_months),
            hours_per_week=int(hours_per_week),
            target_market=target_market,
            learning_preferences=learning_preferences or None,
            additional_context=additional_context or None,
        )
        with st.spinner("Career Coach agent is assessing and saving the learner..."):
            payload = create_initial_assessment(profile)
        st.session_state["last_learner_id"] = payload["learner_id"]
        _render_roadmap(payload["result"], payload["learner_id"])

with returning_tab:
    st.write(
        "Return with the learner ID, record what has actually changed, and let the agent "
        "reassess the saved roadmap rather than starting from zero."
    )
    learner_id = st.text_input(
        "Learner ID",
        value=st.session_state.get("last_learner_id", ""),
        key="returning_learner_id",
    ).strip()

    if st.button("Load saved career state"):
        if not learner_id:
            st.error("Enter a learner ID first.")
        else:
            context = load_learner_context(learner_id)
            if context is None:
                st.error("Learner ID not found.")
            else:
                st.session_state["loaded_context"] = context
                st.session_state["loaded_context_id"] = learner_id

    loaded_context = None
    if st.session_state.get("loaded_context_id") == learner_id:
        loaded_context = st.session_state.get("loaded_context")

    if loaded_context:
        profile = loaded_context["profile"]
        latest_roadmap = loaded_context.get("latest_roadmap") or {}
        c1, c2, c3 = st.columns(3)
        c1.metric("Current role", profile["current_role"])
        c2.metric("Target role", profile["target_role"])
        c3.metric("Saved progress updates", len(loaded_context.get("progress_updates", [])))
        if latest_roadmap.get("executive_summary"):
            st.caption("Latest saved assessment")
            st.write(latest_roadmap["executive_summary"])

    progress_text = st.text_area(
        "What changed since the last plan?",
        placeholder=(
            "Example: Completed Python/API exercises, built a small RAG app with citations, "
            "pushed it to GitHub, but still struggling with evaluation and deployment."
        ),
        height=140,
    )

    if st.button("Save progress + reassess", type="primary"):
        _require_api_key()
        if not learner_id:
            st.error("Enter a learner ID first.")
            st.stop()
        if not progress_text.strip():
            st.error("Describe what changed before running a reassessment.")
            st.stop()
        progress = ProgressUpdate(update_text=progress_text)
        try:
            with st.spinner("Loading saved career state and reassessing progress..."):
                payload = reassess_progress(learner_id, progress)
        except (KeyError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.session_state["last_learner_id"] = learner_id
            refreshed = load_learner_context(learner_id)
            st.session_state["loaded_context"] = refreshed
            st.session_state["loaded_context_id"] = learner_id
            _render_roadmap(payload["result"], learner_id)
