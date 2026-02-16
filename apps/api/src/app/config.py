import os
from pathlib import Path


def apply_config(app):
    data_dir = Path(app.root_path).parents[1] / "data"
    app.config.setdefault("GITHUB_API_BASE", "https://api.github.com")
    app.config.setdefault("GITHUB_OWNER", os.getenv("GITHUB_OWNER", ""))
    app.config.setdefault("GITHUB_REPO", os.getenv("GITHUB_REPO", ""))
    app.config.setdefault("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN", ""))
    app.config.setdefault("SYNC_TOKEN", os.getenv("SYNC_TOKEN", ""))
    app.config.setdefault("RUNS_STORAGE_PATH", str(data_dir / "workflow_runs.json"))
