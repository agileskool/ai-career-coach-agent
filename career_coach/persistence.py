"""SQLite persistence for long-term learner career state."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from career_coach.schemas import LearnerProfile

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "careerpilot.db"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class CareerRepository:
    """Persist learner profiles, assessments, and progress updates in SQLite."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        configured = db_path or os.getenv("CAREERPILOT_DB_PATH") or _DEFAULT_DB
        self.db_path = Path(configured)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS learners (
                    learner_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS learner_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learner_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
                );

                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learner_id TEXT NOT NULL,
                    roadmap_json TEXT NOT NULL,
                    llm_calls INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
                );

                CREATE TABLE IF NOT EXISTS progress_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learner_id TEXT NOT NULL,
                    update_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
                );
                """
            )

    def create_learner(self, profile: LearnerProfile) -> str:
        learner_id = str(uuid.uuid4())
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO learners (learner_id, created_at, updated_at) VALUES (?, ?, ?)",
                (learner_id, now, now),
            )
            connection.execute(
                (
                    "INSERT INTO learner_profiles "
                    "(learner_id, profile_json, created_at) VALUES (?, ?, ?)"
                ),
                (learner_id, profile.model_dump_json(), now),
            )
        return learner_id

    def learner_exists(self, learner_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM learners WHERE learner_id = ?",
                (learner_id,),
            ).fetchone()
        return row is not None

    def save_profile(self, learner_id: str, profile: LearnerProfile) -> None:
        if not self.learner_exists(learner_id):
            raise KeyError(f"Unknown learner_id: {learner_id}")
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                (
                    "INSERT INTO learner_profiles "
                    "(learner_id, profile_json, created_at) VALUES (?, ?, ?)"
                ),
                (learner_id, profile.model_dump_json(), now),
            )
            connection.execute(
                "UPDATE learners SET updated_at = ? WHERE learner_id = ?",
                (now, learner_id),
            )

    def get_latest_profile(self, learner_id: str) -> LearnerProfile | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT profile_json
                FROM learner_profiles
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (learner_id,),
            ).fetchone()
        if row is None:
            return None
        return LearnerProfile.model_validate_json(row["profile_json"])

    def save_assessment(self, learner_id: str, roadmap: dict[str, Any], llm_calls: int) -> None:
        if not self.learner_exists(learner_id):
            raise KeyError(f"Unknown learner_id: {learner_id}")
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assessments (learner_id, roadmap_json, llm_calls, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (learner_id, json.dumps(roadmap), llm_calls, now),
            )
            connection.execute(
                "UPDATE learners SET updated_at = ? WHERE learner_id = ?",
                (now, learner_id),
            )

    def get_latest_roadmap(self, learner_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT roadmap_json
                FROM assessments
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (learner_id,),
            ).fetchone()
        return json.loads(row["roadmap_json"]) if row else None

    def has_progress_update(self, learner_id: str, update_text: str) -> bool:
        cleaned = update_text.strip()
        if not cleaned:
            return False
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM progress_updates
                WHERE learner_id = ? AND update_text = ?
                LIMIT 1
                """,
                (learner_id, cleaned),
            ).fetchone()
        return row is not None

    def add_progress_update(self, learner_id: str, update_text: str) -> None:
        cleaned = update_text.strip()
        if not cleaned:
            raise ValueError("Progress update cannot be empty.")
        if not self.learner_exists(learner_id):
            raise KeyError(f"Unknown learner_id: {learner_id}")
        if self.has_progress_update(learner_id, cleaned):
            raise ValueError(
                "This progress update is identical to one already saved. "
                "Add genuinely new evidence before reassessing."
            )
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                (
                    "INSERT INTO progress_updates "
                    "(learner_id, update_text, created_at) VALUES (?, ?, ?)"
                ),
                (learner_id, cleaned, now),
            )
            connection.execute(
                "UPDATE learners SET updated_at = ? WHERE learner_id = ?",
                (now, learner_id),
            )

    def list_progress_updates(self, learner_id: str, limit: int = 20) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT update_text, created_at
                FROM progress_updates
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (learner_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def get_history_summary(self, learner_id: str) -> dict[str, Any] | None:
        profile = self.get_latest_profile(learner_id)
        if profile is None:
            return None
        return {
            "learner_id": learner_id,
            "profile": profile.model_dump(),
            "latest_roadmap": self.get_latest_roadmap(learner_id),
            "progress_updates": self.list_progress_updates(learner_id),
        }
