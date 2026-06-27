from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.schemas import QueryRequest, TimelineEvent, utcnow_iso


class QueryRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def init(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queries (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    current_message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    pass_count INTEGER NOT NULL DEFAULT 0,
                    max_passes INTEGER NOT NULL DEFAULT 2,
                    confidence_threshold REAL NOT NULL DEFAULT 0.74,
                    confidence_score REAL,
                    mode TEXT NOT NULL DEFAULT 'pending',
                    simulated_research INTEGER NOT NULL DEFAULT 0,
                    timeline_json TEXT NOT NULL DEFAULT '[]',
                    state_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT,
                    error_message TEXT
                )
                """
            )
            connection.commit()

    def create_query(self, query_id: str, request: QueryRequest, max_passes: int, threshold: float) -> dict[str, Any]:
        now = utcnow_iso()
        initial_timeline = [
            TimelineEvent(
                agent="System",
                stage="system",
                status="pending",
                title="Council convened",
                detail="QUORUM created a new council session and is preparing the chair agent.",
                pass_index=1,
            ).model_dump(mode="json")
        ]
        initial_state = {
            "investigation_plan": [],
            "sources": [],
            "evidence_cards": [],
            "contradiction_cards": [],
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO queries (
                    id, question, status, current_stage, current_message, created_at, updated_at,
                    pass_count, max_passes, confidence_threshold, mode, simulated_research,
                    timeline_json, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    request.question.strip(),
                    "queued",
                    "queued",
                    "Waiting for the chair agent to begin planning.",
                    now,
                    now,
                    0,
                    max_passes,
                    threshold,
                    "pending",
                    0,
                    json.dumps(initial_timeline),
                    json.dumps(initial_state),
                ),
            )
            connection.commit()
        return self.get_query(query_id) or {}

    def get_query(self, query_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def update_query(
        self,
        query_id: str,
        *,
        status: str | None = None,
        current_stage: str | None = None,
        current_message: str | None = None,
        pass_count: int | None = None,
        confidence_score: float | None = None,
        mode: str | None = None,
        simulated_research: bool | None = None,
        append_timeline: list[dict[str, Any]] | None = None,
        state_patch: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            current = connection.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
            if current is None:
                raise KeyError(f"Query {query_id} not found")

            current_state = json.loads(current["state_json"] or "{}")
            current_timeline = json.loads(current["timeline_json"] or "[]")

            if state_patch:
                current_state.update(state_patch)
            if append_timeline:
                current_timeline.extend(append_timeline)

            updated_at = utcnow_iso()
            connection.execute(
                """
                UPDATE queries
                SET status = ?,
                    current_stage = ?,
                    current_message = ?,
                    updated_at = ?,
                    pass_count = ?,
                    confidence_score = ?,
                    mode = ?,
                    simulated_research = ?,
                    timeline_json = ?,
                    state_json = ?,
                    result_json = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    status or current["status"],
                    current_stage or current["current_stage"],
                    current_message or current["current_message"],
                    updated_at,
                    pass_count if pass_count is not None else current["pass_count"],
                    confidence_score if confidence_score is not None else current["confidence_score"],
                    mode or current["mode"],
                    int(simulated_research) if simulated_research is not None else current["simulated_research"],
                    json.dumps(current_timeline),
                    json.dumps(current_state),
                    json.dumps(result) if result is not None else current["result_json"],
                    error_message if error_message is not None else current["error_message"],
                    query_id,
                ),
            )
            connection.commit()
            refreshed = connection.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()

        return self._row_to_dict(refreshed)

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "question": row["question"],
            "status": row["status"],
            "current_stage": row["current_stage"],
            "current_message": row["current_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "pass_count": row["pass_count"],
            "max_passes": row["max_passes"],
            "confidence_threshold": row["confidence_threshold"],
            "confidence_score": row["confidence_score"],
            "mode": row["mode"],
            "simulated_research": bool(row["simulated_research"]),
            "timeline_json": row["timeline_json"],
            "state_json": row["state_json"],
            "result_json": row["result_json"],
            "error_message": row["error_message"],
        }

