from typing import Any


def build_runs_response(
    runs: list[dict[str, Any]], total: int, page: int, limit: int, total_pages: int
) -> dict[str, Any]:
    return {
        "count": len(runs),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": runs,
    }


def build_sync_response(synced: int) -> dict[str, int]:
    return {"synced_runs": synced}
