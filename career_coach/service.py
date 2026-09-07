"""Application service coordinating persistence and agent execution."""

from __future__ import annotations

import uuid
from typing import Any

from career_coach.graph import assess_learner
from career_coach.persistence import CareerRepository
from career_coach.schemas import LearnerProfile, ProgressUpdate


def _repository(repository: CareerRepository | None) -> CareerRepository:
    return repository or CareerRepository()


def _run_thread_id(learner_id: str) -> str:
    """Use a fresh graph thread per assessment while SQLite holds long-term memory."""

    return f"{learner_id}:{uuid.uuid4()}"


def create_initial_assessment(
    profile: LearnerProfile,
    repository: CareerRepository | None = None,
) -> dict[str, Any]:
    """Create a learner, run the baseline agent, and persist the roadmap."""

    repo = _repository(repository)
    learner_id = repo.create_learner(profile)
    result = assess_learner(
        profile,
        _run_thread_id(learner_id),
        assessment_mode="baseline",
    )
    repo.save_assessment(
        learner_id,
        result["final_roadmap"],
        int(result.get("llm_calls", 0)),
    )
    return {"learner_id": learner_id, "result": result}


def reassess_progress(
    learner_id: str,
    progress: ProgressUpdate,
    repository: CareerRepository | None = None,
) -> dict[str, Any]:
    """Persist progress, load career history, and run a longitudinal reassessment."""

    repo = _repository(repository)
    profile = repo.get_latest_profile(learner_id)
    if profile is None:
        raise KeyError(f"Unknown learner_id: {learner_id}")

    previous_roadmap = repo.get_latest_roadmap(learner_id)
    if previous_roadmap is None:
        raise ValueError("A baseline assessment is required before progress reassessment.")

    repo.add_progress_update(learner_id, progress.update_text)
    progress_updates = repo.list_progress_updates(learner_id)

    result = assess_learner(
        profile,
        _run_thread_id(learner_id),
        assessment_mode="reassessment",
        previous_roadmap=previous_roadmap,
        progress_updates=progress_updates,
    )
    repo.save_assessment(
        learner_id,
        result["final_roadmap"],
        int(result.get("llm_calls", 0)),
    )
    return {"learner_id": learner_id, "result": result}


def load_learner_context(
    learner_id: str,
    repository: CareerRepository | None = None,
) -> dict[str, Any] | None:
    """Return the saved career state used by the returning-learner UI."""

    return _repository(repository).get_history_summary(learner_id)
