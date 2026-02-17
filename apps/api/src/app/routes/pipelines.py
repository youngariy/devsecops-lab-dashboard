from flask import Blueprint, current_app, jsonify, request

from ..repositories.workflow_run_repository import WorkflowRunRepository
from ..schemas.pipeline_schema import build_runs_response, build_sync_response
from ..services.github_service import GithubService, GithubServiceError
from ..services.pipeline_service import PipelineService

pipelines_bp = Blueprint("pipelines", __name__, url_prefix="/api/pipelines")


def _pipeline_service() -> PipelineService:
    repo = WorkflowRunRepository(current_app.config["RUNS_STORAGE_PATH"])
    github = GithubService(
        api_base=current_app.config["GITHUB_API_BASE"],
        owner=current_app.config["GITHUB_OWNER"],
        repo=current_app.config["GITHUB_REPO"],
        token=current_app.config["GITHUB_TOKEN"],
    )
    return PipelineService(repository=repo, github=github)


@pipelines_bp.get("/runs")
def get_runs():
    limit = request.args.get("limit", default=10, type=int)
    page = request.args.get("page", default=1, type=int)
    runs, total, total_pages = _pipeline_service().list_runs(limit=limit, page=page)
    return jsonify(
        build_runs_response(
            runs=runs,
            total=total,
            page=max(1, page),
            limit=max(1, min(limit, 100)),
            total_pages=total_pages,
        )
    )


@pipelines_bp.get("/summary")
def get_summary():
    return jsonify(_pipeline_service().summary())


@pipelines_bp.post("/sync")
def sync_runs():
    sync_token = current_app.config["SYNC_TOKEN"]
    if not sync_token:
        return jsonify({"error": "SYNC_TOKEN must be configured on server"}), 503

    provided_token = request.headers.get("X-Sync-Token", "")
    if provided_token != sync_token:
        return jsonify({"error": "Unauthorized sync request"}), 401

    owner = current_app.config["GITHUB_OWNER"]
    repo = current_app.config["GITHUB_REPO"]
    if not owner or not repo:
        return (
            jsonify(
                {
                    "error": "GITHUB_OWNER and GITHUB_REPO must be configured",
                }
            ),
            400,
        )

    per_page = request.args.get("per_page", default=30, type=int)
    try:
        result = _pipeline_service().sync(per_page=per_page)
    except GithubServiceError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(build_sync_response(result["synced"]))
