import json
from pathlib import Path
from typing import Any


class WorkflowRunRepository:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def list_runs(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            content = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(content, list):
            return []
        return content

    def save_runs(self, runs: list[dict[str, Any]]) -> None:
        self.storage_path.write_text(
            json.dumps(runs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
