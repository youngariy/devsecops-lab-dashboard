from typing import Any


def build_runs_response(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"count": len(runs), "items": runs}


def build_sync_response(synced: int) -> dict[str, int]:
    return {"synced_runs": synced}
