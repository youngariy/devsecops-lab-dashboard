from pathlib import Path
from uuid import uuid4

import pytest

from app import create_app


@pytest.fixture
def client():
    runs_path = Path(f"apps/api/tests/.testdata/runs-{uuid4().hex}.db")
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(
        {
            "TESTING": True,
            "RUNS_STORAGE_PATH": str(runs_path),
            "GITHUB_OWNER": "example",
            "GITHUB_REPO": "repo",
            "SYNC_TOKEN": "test-sync-token",
        }
    )
    return app.test_client()


def test_empty_runs(client):
    resp = client.get("/api/pipelines/runs")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["count"] == 0
    assert payload["filters"] == {"category": "", "branch": ""}
    assert payload["items"] == []


def test_empty_summary(client):
    resp = client.get("/api/pipelines/summary")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["total_runs"] == 0
    assert payload["category_status"]["ci"] == "unknown"
    assert payload["security_summary"]["severity_totals"]["high"] == 0
    assert payload["security_summary"]["secret_leak_detected"] is False


def test_empty_deployment(client):
    resp = client.get("/api/pipelines/deployment")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["has_cd_data"] is False
    assert payload["latest_cd_run"] is None


def test_empty_security_trends(client):
    resp = client.get("/api/pipelines/security-trends")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["points"] == []


def test_sync_then_summary(client, monkeypatch):
    from app.services.github_service import GithubService

    fake_runs = [
        {
            "id": 101,
            "name": "CI Pipeline",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "abc123",
            "run_started_at": "2026-02-15T10:00:00Z",
            "updated_at": "2026-02-15T10:02:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/101",
        },
        {
            "id": 102,
            "name": "Security Scan",
            "conclusion": "failure",
            "head_branch": "main",
            "head_sha": "def456",
            "run_started_at": "2026-02-15T10:03:00Z",
            "updated_at": "2026-02-15T10:06:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/102",
            "summary_json": {"tools": {"trivy": {"critical": 1, "high": 2}}},
        },
        {
            "id": 103,
            "name": "CD Build, Push & Deploy",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "xyz999",
            "run_started_at": "2026-02-15T10:07:00Z",
            "updated_at": "2026-02-15T10:10:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/103",
        },
    ]

    monkeypatch.setattr(GithubService, "list_workflow_runs", lambda self, per_page=30: fake_runs)
    monkeypatch.setattr(
        GithubService,
        "build_run_summary",
        lambda self, run_id: {
            "tools": {"trivy": {"high": 1}},
            "supply_chain": {
                "sbom_generated": True,
                "cosign_signed": True,
                "cosign_verified": True,
                "https_ok": True,
                "image_digest": "sha256:abc123",
                "image_tag": "v1.2.3",
            },
        },
    )
    sync_resp = client.post("/api/pipelines/sync", headers={"X-Sync-Token": "test-sync-token"})
    assert sync_resp.status_code == 200
    assert sync_resp.get_json()["synced_runs"] == 3

    runs_resp = client.get("/api/pipelines/runs")
    assert runs_resp.status_code == 200
    assert runs_resp.get_json()["count"] == 3
    assert runs_resp.get_json()["total"] == 3
    assert runs_resp.get_json()["page"] == 1
    assert runs_resp.get_json()["total_pages"] == 1
    assert runs_resp.get_json()["filters"] == {"category": "", "branch": ""}
    assert runs_resp.get_json()["items"][0]["summary_json"]["tools"]["trivy"]["high"] == 1

    filtered_category = client.get("/api/pipelines/runs?category=cd")
    filtered_category_payload = filtered_category.get_json()
    assert filtered_category_payload["count"] == 1
    assert filtered_category_payload["items"][0]["category"] == "cd"
    assert filtered_category_payload["filters"]["category"] == "cd"

    filtered_branch = client.get("/api/pipelines/runs?branch=main")
    filtered_branch_payload = filtered_branch.get_json()
    assert filtered_branch_payload["count"] == 3
    assert filtered_branch_payload["filters"]["branch"] == "main"

    paged_resp = client.get("/api/pipelines/runs?page=2&limit=2")
    assert paged_resp.status_code == 200
    paged_payload = paged_resp.get_json()
    assert paged_payload["count"] == 1
    assert paged_payload["total"] == 3
    assert paged_payload["page"] == 2
    assert paged_payload["total_pages"] == 2
    assert paged_payload["items"][0]["id"] == 103

    summary_resp = client.get("/api/pipelines/summary")
    payload = summary_resp.get_json()
    assert payload["total_runs"] == 3
    assert payload["status_counts"]["success"] == 2
    assert payload["status_counts"]["failure"] == 1
    assert payload["security_summary"]["severity_totals"]["high"] == 3
    assert payload["security_summary"]["tool_totals"]["trivy"] == 3

    deployment_resp = client.get("/api/pipelines/deployment")
    deployment_payload = deployment_resp.get_json()
    assert deployment_payload["has_cd_data"] is True
    assert deployment_payload["environment"] == "prod"
    assert deployment_payload["latest_cd_run"]["id"] == 103
    assert deployment_payload["supply_chain"]["cosign_verified"] is True
    assert deployment_payload["supply_chain"]["image_digest"] == "sha256:abc123"

    trend_resp = client.get("/api/pipelines/security-trends?days=3")
    trend_payload = trend_resp.get_json()
    assert trend_resp.status_code == 200
    assert trend_payload["days"] == 3
    assert len(trend_payload["points"]) == 3
    assert trend_payload["points"][-1]["total_findings"] == 3


def test_deployment_uses_latest_cd_by_timestamp(client, monkeypatch):
    from app.services.github_service import GithubService

    fake_runs = [
        {
            "id": 201,
            "name": "CD Build, Push & Deploy",
            "conclusion": "failure",
            "head_branch": "main",
            "head_sha": "old",
            "run_started_at": "2026-02-15T08:00:00Z",
            "updated_at": "2026-02-15T08:02:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/201",
        },
        {
            "id": 202,
            "name": "CD Build, Push & Deploy",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "new",
            "run_started_at": "2026-02-15T09:00:00Z",
            "updated_at": "2026-02-15T09:01:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/202",
        },
    ]

    monkeypatch.setattr(GithubService, "list_workflow_runs", lambda self, per_page=30: fake_runs)
    monkeypatch.setattr(GithubService, "build_run_summary", lambda self, run_id: {})
    sync_resp = client.post("/api/pipelines/sync", headers={"X-Sync-Token": "test-sync-token"})
    assert sync_resp.status_code == 200

    deployment_resp = client.get("/api/pipelines/deployment")
    deployment_payload = deployment_resp.get_json()
    assert deployment_payload["latest_cd_run"]["id"] == 202
    assert deployment_payload["latest_cd_run"]["conclusion"] == "success"


def test_sync_requires_token(client):
    resp = client.post("/api/pipelines/sync")
    assert resp.status_code == 401


def test_sync_per_page_is_clamped(client, monkeypatch):
    from app.services.github_service import GithubService

    captured = []

    def _fake_list_runs(self, per_page=30):
        captured.append(per_page)
        return []

    monkeypatch.setattr(GithubService, "list_workflow_runs", _fake_list_runs)
    monkeypatch.setattr(GithubService, "build_run_summary", lambda self, run_id: {})

    high_resp = client.post(
        "/api/pipelines/sync?per_page=9999",
        headers={"X-Sync-Token": "test-sync-token"},
    )
    assert high_resp.status_code == 200
    assert high_resp.get_json()["synced_runs"] == 0

    low_resp = client.post(
        "/api/pipelines/sync?per_page=-5",
        headers={"X-Sync-Token": "test-sync-token"},
    )
    assert low_resp.status_code == 200
    assert low_resp.get_json()["synced_runs"] == 0

    assert captured == [100, 1]


def test_legacy_json_is_migrated_once():
    from app.repositories.workflow_run_repository import WorkflowRunRepository

    base = Path(f"apps/api/tests/.testdata/migrate-{uuid4().hex}")
    base.mkdir(parents=True, exist_ok=True)
    db_path = base / "runs.db"
    legacy_path = base / "workflow_runs.json"
    legacy_path.write_text(
        '[{"id":1,"workflow_name":"CI","category":"ci","conclusion":"success","branch":"main","commit_sha":"a","started_at":"","completed_at":"","duration":1,"html_url":"","summary_json":{},"synced_at":"2026-02-18T00:00:00Z"}]',
        encoding="utf-8",
    )

    repo = WorkflowRunRepository(str(db_path), str(legacy_path))
    runs = repo.list_runs()
    assert len(runs) == 1
    assert runs[0]["id"] == 1
