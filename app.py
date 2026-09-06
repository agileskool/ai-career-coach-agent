"""Streamlit interface for the AI Career Coach showcase."""

from __future__ import annotations

import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from career_coach.graph import assess_learner
from career_coach.model_provider import DEFAULT_MODEL
from career_coach.presentation import build_execution_trace
from career_coach.schemas import CareerRoadmap, LearnerProfile

load_dotenv()

st.set_page_config(page_title="CareerPilot AI", page_icon="🧭", layout="wide")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

st.title("CareerPilot AI")
st.caption("A stateful, tool-using single agent for evidence-based AI career transitions")

with st.sidebar:
    st.subheader("Agent architecture")
    st.markdown(
        "**LangGraph** manages state and routing.  \n"
        "**NVIDIA Nemotron** performs judgement.  \n"
        "**Tools** provide deterministic role/capacity data."
    )
    model = os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)
    st.caption(f"Model: {model}")

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

    submitted = st.form_submit_button("Run agent assessment", type="primary")

if submitted:
    if not os.getenv("NVIDIA_API_KEY"):
        st.error("Set NVIDIA_API_KEY before running the live agent.")
        st.stop()

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

    with st.spinner("Career Coach agent is assessing the learner..."):
        result = assess_learner(profile, st.session_state.thread_id)

    roadmap = CareerRoadmap.model_validate(result["final_roadmap"])

    st.success("Assessment complete")
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

    st.subheader("First 30 days")
    for index, item in enumerate(roadmap.first_30_days, start=1):
        st.write(f"{index}. {item}")

    with st.expander("Agent execution trace"):
        st.caption(
            "Shows observable tool requests/results only; hidden model reasoning is not exposed."
        )
        trace = build_execution_trace(result.get("messages", []))
        st.json(trace)
        st.caption(f"LLM calls in this run: {result.get('llm_calls', 0)}")
