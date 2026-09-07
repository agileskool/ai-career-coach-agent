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
    """Run reassessment first, then atomically persist progress plus the new roadmap."""

    repo = _repository(repository)
    profile = repo.get_latest_profile(learner_id)
    if profile is None:
        raise KeyError(f"Unknown learner_id: {learner_id}")

    previous_roadmap = repo.get_latest_roadmap(learner_id)
    if previous_roadmap is None:
        raise ValueError("A baseline assessment is required before progress reassessment.")

    cleaned = progress.update_text.strip()
    existing_update_at = repo.get_progress_update_created_at(learner_id, cleaned)
    latest_assessment_at = repo.get_latest_assessment_created_at(learner_id)

    # A matching update at or before the latest assessment has already been consumed.
    # A newer matching update is an orphan left by an older failed reassessment and may retry.
    if (
        existing_update_at is not None
        and latest_assessment_at is not None
        and existing_update_at <= latest_assessment_at
    ):
        raise ValueError(
            "This progress update is identical to one already assessed. "
            "Add genuinely new evidence before reassessing."
        )

    progress_updates = repo.list_progress_updates(learner_id)
    if existing_update_at is None:
        progress_updates = [
            *progress_updates,
            {"update_text": cleaned, "created_at": "pending"},
        ]

    result = assess_learner(
        profile,
        _run_thread_id(learner_id),
        assessment_mode="reassessment",
        previous_roadmap=previous_roadmap,
        progress_updates=progress_updates,
    )

    # Persist only after a successful agent run. SQLite commits the progress and its
    # assessment together so retries cannot create half-saved longitudinal state.
    repo.save_reassessment(
        learner_id,
        cleaned,
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
