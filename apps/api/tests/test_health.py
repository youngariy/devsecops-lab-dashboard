import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    return app.test_client()


def test_hello(client):
    resp = client.get("/")
    assert resp.data == b"Hello, Flask!"


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_poller_not_started_in_testing():
    app = create_app({"TESTING": True, "POLLING_ENABLED": True})
    assert "sync_poller_thread" not in app.extensions


def test_runs_storage_env_override(monkeypatch):
    monkeypatch.setenv("RUNS_STORAGE_PATH", "custom/path/runs.db")
    monkeypatch.setenv("RUNS_LEGACY_JSON_PATH", "custom/path/runs.json")
    app = create_app({"TESTING": True})
    assert app.config["RUNS_STORAGE_PATH"] == "custom/path/runs.db"
    assert app.config["RUNS_LEGACY_JSON_PATH"] == "custom/path/runs.json"
    monkeypatch.delenv("RUNS_STORAGE_PATH", raising=False)
    monkeypatch.delenv("RUNS_LEGACY_JSON_PATH", raising=False)
