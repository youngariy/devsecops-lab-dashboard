from hmac import compare_digest

from flask import Blueprint, current_app, jsonify, request

from ..schemas.pipeline_schema import build_runs_response, build_sync_response
from ..services.github_service import GithubServiceError
from ..services.pipeline_service import PipelineService

pipelines_bp = Blueprint("pipelines", __name__, url_prefix="/api/pipelines")


def _pipeline_service() -> PipelineService:
    factory = current_app.extensions.get("pipeline_service_factory")
    if callable(factory):
        return factory()
    raise RuntimeError("pipeline_service_factory is not configured")


@pipelines_bp.get("/runs")
def get_runs():
    limit = request.args.get("limit", default=10, type=int)
    page = request.args.get("page", default=1, type=int)
    category = request.args.get("category", default="", type=str)
    branch = request.args.get("branch", default="", type=str)
    runs, total, total_pages = _pipeline_service().list_runs(
        limit=limit,
        page=page,
        category=category,
        branch=branch,
    )
    return jsonify(
        build_runs_response(
            runs=runs,
            total=total,
            page=max(1, page),
            limit=max(1, min(limit, 100)),
            total_pages=total_pages,
            filters={
                "category": category.strip().lower(),
                "branch": branch.strip(),
            },
        )
    )


@pipelines_bp.get("/summary")
def get_summary():
    return jsonify(_pipeline_service().summary())


@pipelines_bp.get("/deployment")
def get_deployment():
    return jsonify(_pipeline_service().deployment_summary())


@pipelines_bp.get("/security-trends")
def get_security_trends():
    days = request.args.get("days", default=14, type=int)
    return jsonify(_pipeline_service().security_trends(days=days))


@pipelines_bp.post("/sync")
def sync_runs():
    sync_token = current_app.config["SYNC_TOKEN"]
    if not sync_token:
        return jsonify({"error": "SYNC_TOKEN must be configured on server"}), 503

    provided_token = request.headers.get("X-Sync-Token", "")
    if not compare_digest(str(provided_token), str(sync_token)):
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
    per_page = max(1, min(per_page, 100))
    try:
        result = _pipeline_service().sync(per_page=per_page)
    except GithubServiceError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(build_sync_response(result["synced"]))
