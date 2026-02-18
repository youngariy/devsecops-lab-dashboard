import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def apply_config(app):
    data_dir = Path(app.root_path).parents[1] / "data"
    app.config.setdefault("GITHUB_API_BASE", "https://api.github.com")
    app.config.setdefault("GITHUB_OWNER", os.getenv("GITHUB_OWNER", ""))
    app.config.setdefault("GITHUB_REPO", os.getenv("GITHUB_REPO", ""))
    app.config.setdefault("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN", ""))
    app.config.setdefault("SYNC_TOKEN", os.getenv("SYNC_TOKEN", ""))
    app.config.setdefault(
        "RUNS_STORAGE_PATH",
        os.getenv("RUNS_STORAGE_PATH", str(data_dir / "workflow_runs.db")),
    )
    app.config.setdefault(
        "RUNS_LEGACY_JSON_PATH",
        os.getenv("RUNS_LEGACY_JSON_PATH", str(data_dir / "workflow_runs.json")),
    )
    app.config.setdefault("POLLING_ENABLED", _env_bool("POLLING_ENABLED", True))
    app.config.setdefault("POLLING_INTERVAL_SECONDS", max(30, _env_int("POLLING_INTERVAL_SECONDS", 300)))
    app.config.setdefault("POLLING_PER_PAGE", max(1, min(_env_int("POLLING_PER_PAGE", 30), 100)))
