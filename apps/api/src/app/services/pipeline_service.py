from collections import Counter
from typing import Any

from ..models.workflow_run import WorkflowRun
from ..repositories.workflow_run_repository import WorkflowRunRepository
from .github_service import GithubService


def _category_from_name(workflow_name: str) -> str:
    lowered = workflow_name.lower()
    if "security" in lowered:
        return "security"
    if "deploy" in lowered or "cd" in lowered:
        return "cd"
    if "ci" in lowered or "test" in lowered:
        return "ci"
    return "other"


def _tool_counter(runs: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counters: dict[str, dict[str, int]] = {
        "trivy": {"critical": 0, "high": 0},
        "bandit": {"high": 0},
        "semgrep": {"findings": 0},
        "pip_audit": {"vuln_packages": 0},
        "gitleaks": {"leaks": 0},
    }
    for run in runs:
        tools = run.get("summary_json", {}).get("tools", {})
        for key, fields in counters.items():
            src = tools.get(key, {})
            for field in fields:
                fields[field] += int(src.get(field, 0) or 0)
    return counters


class PipelineService:
    def __init__(self, repository: WorkflowRunRepository, github: GithubService):
        self.repository = repository
        self.github = github

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        runs = self.repository.list_runs()
        return runs[: max(1, min(limit, 100))]

    def summary(self) -> dict[str, Any]:
        runs = self.repository.list_runs()
        if not runs:
            return {
                "total_runs": 0,
                "status_counts": {},
                "category_status": {"ci": "unknown", "security": "unknown", "cd": "unknown"},
                "recent_failures": [],
                "security_summary": {"tools": _tool_counter([])},
            }

        status_counts = Counter((r.get("conclusion") or "unknown") for r in runs)
        recent_failures = [r for r in runs if r.get("conclusion") == "failure"][:5]

        def latest_for(category: str) -> str:
            for run in runs:
                if run.get("category") == category:
                    return run.get("conclusion", "unknown")
            return "unknown"

        return {
            "total_runs": len(runs),
            "status_counts": dict(status_counts),
            "category_status": {
                "ci": latest_for("ci"),
                "security": latest_for("security"),
                "cd": latest_for("cd"),
            },
            "recent_failures": recent_failures,
            "security_summary": {"tools": _tool_counter(runs)},
        }

    def sync(self, per_page: int = 30) -> dict[str, Any]:
        raw_runs = self.github.list_workflow_runs(per_page=per_page)
        transformed: list[dict[str, Any]] = []
        for raw in raw_runs:
            raw["category"] = _category_from_name(raw.get("name", ""))
            transformed.append(WorkflowRun.from_github_run(raw).to_dict())
        self.repository.save_runs(transformed)
        return {"synced": len(transformed)}
