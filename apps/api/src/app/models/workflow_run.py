from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _duration_seconds(started_at: str, completed_at: str) -> int | None:
    if not started_at or not completed_at:
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int((completed - started).total_seconds())


@dataclass
class WorkflowRun:
    id: int
    workflow_name: str
    category: str
    conclusion: str
    branch: str
    commit_sha: str
    started_at: str
    completed_at: str
    duration: int | None
    html_url: str
    summary_json: dict[str, Any] = field(default_factory=dict)
    synced_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_github_run(cls, run: dict[str, Any]) -> "WorkflowRun":
        started_at = run.get("run_started_at") or run.get("created_at") or ""
        completed_at = run.get("updated_at") or ""
        return cls(
            id=run["id"],
            workflow_name=run.get("name", "unknown"),
            category=run.get("category", "other"),
            conclusion=run.get("conclusion") or run.get("status", "unknown"),
            branch=run.get("head_branch", ""),
            commit_sha=run.get("head_sha", ""),
            started_at=started_at,
            completed_at=completed_at,
            duration=_duration_seconds(started_at, completed_at),
            html_url=run.get("html_url", ""),
            summary_json=run.get("summary_json", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
