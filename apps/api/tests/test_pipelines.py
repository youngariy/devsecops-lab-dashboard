import json
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def client():
    runs_path = Path("apps/api/tests/.testdata/runs.json")
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    runs_path.write_text(json.dumps([]), encoding="utf-8")
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
    assert payload["items"] == []


def test_empty_summary(client):
    resp = client.get("/api/pipelines/summary")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["total_runs"] == 0
    assert payload["category_status"]["ci"] == "unknown"


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
    ]

    monkeypatch.setattr(GithubService, "list_workflow_runs", lambda self, per_page=30: fake_runs)

    sync_resp = client.post("/api/pipelines/sync", headers={"X-Sync-Token": "test-sync-token"})
    assert sync_resp.status_code == 200
    assert sync_resp.get_json()["synced_runs"] == 2

    runs_resp = client.get("/api/pipelines/runs")
    assert runs_resp.status_code == 200
    assert runs_resp.get_json()["count"] == 2

    summary_resp = client.get("/api/pipelines/summary")
    payload = summary_resp.get_json()
    assert payload["total_runs"] == 2
    assert payload["status_counts"]["success"] == 1
    assert payload["status_counts"]["failure"] == 1
    assert payload["security_summary"]["tools"]["trivy"]["critical"] == 1


def test_sync_requires_token(client):
    resp = client.post("/api/pipelines/sync")
    assert resp.status_code == 401
