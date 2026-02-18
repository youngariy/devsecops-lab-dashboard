from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..models.workflow_run import WorkflowRun
from ..repositories.workflow_run_repository import WorkflowRunRepository
from .github_service import GithubService

EXCLUDED_WORKFLOWS = {"Dashboard Sync on Workflow Completion"}
SECURITY_TOOLS = ("trivy", "bandit", "semgrep", "pip_audit", "gitleaks")
SEVERITIES = ("critical", "high", "medium", "low", "unknown")


def _category_from_name(workflow_name: str) -> str:
    lowered = workflow_name.lower()
    if "security" in lowered:
        return "security"
    if "deploy" in lowered or "cd" in lowered:
        return "cd"
    if "ci" in lowered or "test" in lowered:
        return "ci"
    return "other"


def _blank_security_summary() -> dict[str, Any]:
    return {
        "severity_totals": {severity: 0 for severity in SEVERITIES},
        "tool_totals": {tool: 0 for tool in SECURITY_TOOLS},
        "tool_severity": {tool: {severity: 0 for severity in SEVERITIES} for tool in SECURITY_TOOLS},
        "secret_leak_detected": False,
        "supply_chain": {
            "sbom_generated": False,
            "cosign_signed": False,
            "cosign_verified": False,
        },
    }


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _build_security_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary = _blank_security_summary()
    for run in runs:
        summary_json = run.get("summary_json", {})
        if not isinstance(summary_json, dict):
            continue

        tools = summary_json.get("tools", {})
        if isinstance(tools, dict):
            for tool, severities in tools.items():
                if tool not in SECURITY_TOOLS or not isinstance(severities, dict):
                    continue
                for severity, count in severities.items():
                    if severity not in SEVERITIES:
                        continue
                    numeric = _as_int(count)
                    if numeric <= 0:
                        continue
                    summary["severity_totals"][severity] += numeric
                    summary["tool_severity"][tool][severity] += numeric
                    summary["tool_totals"][tool] += numeric

        supply_chain = summary_json.get("supply_chain", {})
        if isinstance(supply_chain, dict):
            for key in ("sbom_generated", "cosign_signed", "cosign_verified"):
                if bool(supply_chain.get(key)):
                    summary["supply_chain"][key] = True

    gitleaks_total = summary["tool_totals"]["gitleaks"]
    summary["secret_leak_detected"] = gitleaks_total > 0
    return summary


def _extract_run_date(run: dict[str, Any]) -> date | None:
    for field in ("started_at", "synced_at", "completed_at"):
        value = run.get(field)
        if not isinstance(value, str) or len(value) < 10:
            continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                continue
    return None


def _extract_run_datetime(run: dict[str, Any]) -> datetime | None:
    for field in ("started_at", "completed_at", "synced_at"):
        value = run.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _blank_deployment_summary() -> dict[str, Any]:
    return {
        "has_cd_data": False,
        "latest_cd_run": None,
        "environment": "unknown",
        "supply_chain": {
            "sbom_generated": False,
            "cosign_signed": False,
            "cosign_verified": False,
            "https_ok": None,
            "image_digest": "",
            "image_tag": "",
        },
    }


class PipelineService:
    def __init__(self, repository: WorkflowRunRepository, github: GithubService):
        self.repository = repository
        self.github = github

    def list_runs(
        self,
        limit: int = 30,
        page: int = 1,
        category: str = "",
        branch: str = "",
    ) -> tuple[list[dict[str, Any]], int, int]:
        runs = self.repository.list_runs()
        normalized_category = category.strip().lower()
        normalized_branch = branch.strip().lower()
        if normalized_category:
            runs = [run for run in runs if str(run.get("category", "")).lower() == normalized_category]
        if normalized_branch:
            runs = [run for run in runs if str(run.get("branch", "")).lower() == normalized_branch]
        safe_limit = max(1, min(limit, 100))
        safe_page = max(1, page)
        total = len(runs)
        total_pages = max(1, (total + safe_limit - 1) // safe_limit)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
        return runs[start:end], total, total_pages

    def summary(self) -> dict[str, Any]:
        runs = self.repository.list_runs()
        if not runs:
            return {
                "total_runs": 0,
                "status_counts": {},
                "category_status": {"ci": "unknown", "security": "unknown", "cd": "unknown"},
                "recent_failures": [],
                "security_summary": _blank_security_summary(),
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
            "security_summary": _build_security_summary(runs),
        }

    def deployment_summary(self) -> dict[str, Any]:
        runs = self.repository.list_runs()
        cd_runs = [run for run in runs if run.get("category") == "cd"]
        if not cd_runs:
            return _blank_deployment_summary()

        latest = max(
            cd_runs,
            key=lambda run: _extract_run_datetime(run) or datetime.min.replace(tzinfo=timezone.utc),
        )
        summary = _blank_deployment_summary()
        summary["has_cd_data"] = True
        summary["latest_cd_run"] = {
            "id": latest.get("id"),
            "workflow_name": latest.get("workflow_name", ""),
            "conclusion": latest.get("conclusion", "unknown"),
            "branch": latest.get("branch", ""),
            "commit_sha": latest.get("commit_sha", ""),
            "duration": latest.get("duration"),
            "started_at": latest.get("started_at", ""),
            "completed_at": latest.get("completed_at", ""),
            "html_url": latest.get("html_url", ""),
        }

        branch = str(latest.get("branch", "")).lower()
        summary["environment"] = "prod" if branch in {"main", "master", "prod", "production"} else "dev"

        summary_json = latest.get("summary_json", {})
        if isinstance(summary_json, dict):
            supply_chain = summary_json.get("supply_chain", {})
            if isinstance(supply_chain, dict):
                for key in ("sbom_generated", "cosign_signed", "cosign_verified"):
                    summary["supply_chain"][key] = bool(supply_chain.get(key))
                https_ok = supply_chain.get("https_ok")
                if isinstance(https_ok, bool):
                    summary["supply_chain"]["https_ok"] = https_ok
                image_digest = supply_chain.get("image_digest")
                if isinstance(image_digest, str):
                    summary["supply_chain"]["image_digest"] = image_digest
                image_tag = supply_chain.get("image_tag")
                if isinstance(image_tag, str):
                    summary["supply_chain"]["image_tag"] = image_tag
        return summary

    def security_trends(self, days: int = 14) -> dict[str, Any]:
        safe_days = max(1, min(days, 90))
        runs = self.repository.list_runs()
        if not runs:
            return {"days": safe_days, "points": []}

        run_dates = [d for d in (_extract_run_date(run) for run in runs) if d is not None]
        if not run_dates:
            return {"days": safe_days, "points": []}

        end_day = max(run_dates)
        start_day = end_day - timedelta(days=safe_days - 1)
        points_by_date: dict[str, dict[str, Any]] = {}

        for offset in range(safe_days):
            current = start_day + timedelta(days=offset)
            key = current.isoformat()
            points_by_date[key] = {
                "date": key,
                "total_findings": 0,
                "severity_totals": {severity: 0 for severity in SEVERITIES},
            }

        for run in runs:
            run_day = _extract_run_date(run)
            if run_day is None:
                continue
            day_key = run_day.isoformat()
            point = points_by_date.get(day_key)
            if point is None:
                continue
            summary_json = run.get("summary_json", {})
            if not isinstance(summary_json, dict):
                continue
            tools = summary_json.get("tools", {})
            if not isinstance(tools, dict):
                continue
            for severities in tools.values():
                if not isinstance(severities, dict):
                    continue
                for severity, count in severities.items():
                    if severity not in SEVERITIES:
                        continue
                    numeric = _as_int(count)
                    if numeric <= 0:
                        continue
                    point["severity_totals"][severity] += numeric
                    point["total_findings"] += numeric

        points = [points_by_date[key] for key in sorted(points_by_date.keys())]
        return {"days": safe_days, "points": points}

    def sync(self, per_page: int = 30) -> dict[str, Any]:
        raw_runs = self.github.list_workflow_runs(per_page=per_page)
        transformed: list[dict[str, Any]] = []
        for raw in raw_runs:
            if raw.get("name", "") in EXCLUDED_WORKFLOWS:
                continue
            run_id = raw.get("id")
            if isinstance(run_id, int):
                raw["summary_json"] = self.github.build_run_summary(run_id=run_id)
            raw["category"] = _category_from_name(raw.get("name", ""))
            transformed.append(WorkflowRun.from_github_run(raw).to_dict())
        self.repository.save_runs(transformed)
        return {"synced": len(transformed)}
