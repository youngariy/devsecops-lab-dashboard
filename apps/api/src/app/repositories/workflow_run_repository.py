import json
import sqlite3
from pathlib import Path
from typing import Any


class WorkflowRunRepository:
    def __init__(self, storage_path: str, legacy_json_path: str | None = None):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_json_path = Path(legacy_json_path) if legacy_json_path else None
        self._init_db()
        self._migrate_legacy_json_once()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.storage_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id INTEGER PRIMARY KEY,
                    seq INTEGER NOT NULL,
                    workflow_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    conclusion TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration INTEGER,
                    html_url TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    synced_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_seq
                ON workflow_runs (seq)
                """
            )

    def _migrate_legacy_json_once(self) -> None:
        if self.legacy_json_path is None:
            return
        if not self.legacy_json_path.exists():
            return
        with self._connect() as conn:
            current_count = conn.execute("SELECT COUNT(1) AS cnt FROM workflow_runs").fetchone()["cnt"]
        if current_count > 0:
            return
        try:
            content = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        if not isinstance(content, list):
            return
        self.save_runs(content)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, workflow_name, category, conclusion, branch, commit_sha,
                       started_at, completed_at, duration, html_url, summary_json, synced_at
                FROM workflow_runs
                ORDER BY seq ASC
                """
            ).fetchall()
        runs: list[dict[str, Any]] = []
        for row in rows:
            try:
                summary_json = json.loads(row["summary_json"])
            except json.JSONDecodeError:
                summary_json = {}
            if not isinstance(summary_json, dict):
                summary_json = {}
            runs.append(
                {
                    "id": row["run_id"],
                    "workflow_name": row["workflow_name"],
                    "category": row["category"],
                    "conclusion": row["conclusion"],
                    "branch": row["branch"],
                    "commit_sha": row["commit_sha"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "duration": row["duration"],
                    "html_url": row["html_url"],
                    "summary_json": summary_json,
                    "synced_at": row["synced_at"],
                }
            )
        return runs

    def save_runs(self, runs: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM workflow_runs")
            payload = []
            for idx, run in enumerate(runs):
                run_id = run.get("id")
                if not isinstance(run_id, int):
                    continue
                payload.append(
                    (
                        run_id,
                        idx,
                        run.get("workflow_name", "unknown"),
                        run.get("category", "other"),
                        run.get("conclusion", "unknown"),
                        run.get("branch", ""),
                        run.get("commit_sha", ""),
                        run.get("started_at", ""),
                        run.get("completed_at", ""),
                        run.get("duration"),
                        run.get("html_url", ""),
                        json.dumps(run.get("summary_json", {}), ensure_ascii=False),
                        run.get("synced_at", ""),
                    )
                )
            conn.executemany(
                """
                INSERT INTO workflow_runs (
                    run_id, seq, workflow_name, category, conclusion, branch, commit_sha,
                    started_at, completed_at, duration, html_url, summary_json, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
