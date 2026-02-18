from flask import Flask

from .config import apply_config
from .repositories.workflow_run_repository import WorkflowRunRepository
from .routes.health import health_bp
from .routes.pipelines import pipelines_bp
from .services.github_service import GithubService
from .services.pipeline_service import PipelineService
from .services.sync_poller import start_sync_poller


def _build_pipeline_service(app: Flask) -> PipelineService:
    repository = WorkflowRunRepository(
        storage_path=app.config["RUNS_STORAGE_PATH"],
        legacy_json_path=app.config.get("RUNS_LEGACY_JSON_PATH"),
    )
    github = GithubService(
        api_base=app.config["GITHUB_API_BASE"],
        owner=app.config["GITHUB_OWNER"],
        repo=app.config["GITHUB_REPO"],
        token=app.config["GITHUB_TOKEN"],
    )
    return PipelineService(repository=repository, github=github)


def create_app(test_config=None):
    app = Flask(__name__)
    apply_config(app)

    if test_config:
        app.config.update(test_config)

    app.extensions["pipeline_service_factory"] = lambda: _build_pipeline_service(app)
    app.register_blueprint(health_bp)
    app.register_blueprint(pipelines_bp)
    start_sync_poller(app)
    return app
