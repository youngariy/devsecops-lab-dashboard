import os
import threading
from typing import Any

from .github_service import GithubServiceError


def _sync_once(app) -> dict[str, Any] | None:
    owner = app.config.get("GITHUB_OWNER", "")
    repo = app.config.get("GITHUB_REPO", "")
    if not owner or not repo:
        app.logger.warning("Polling skipped: GITHUB_OWNER/GITHUB_REPO is not configured")
        return None

    per_page = int(app.config.get("POLLING_PER_PAGE", 30))
    factory = app.extensions.get("pipeline_service_factory")
    if not callable(factory):
        app.logger.warning("Polling skipped: pipeline_service_factory is not configured")
        return None
    service = factory()
    result = service.sync(per_page=per_page)
    return result


def start_sync_poller(app) -> None:
    if app.config.get("TESTING"):
        return
    # Avoid duplicate poller thread in Werkzeug reloader parent process.
    if app.debug and os.getenv("WERKZEUG_RUN_MAIN") != "true":
        return
    if not app.config.get("POLLING_ENABLED", False):
        return
    if "sync_poller_thread" in app.extensions:
        return

    interval = int(app.config.get("POLLING_INTERVAL_SECONDS", 300))
    stop_event = threading.Event()

    def _runner():
        while not stop_event.is_set():
            try:
                with app.app_context():
                    result = _sync_once(app)
                    if result is not None:
                        app.logger.info("Polling sync completed: %s runs", result.get("synced", 0))
            except GithubServiceError as exc:
                app.logger.warning("Polling sync failed (GitHub): %s", exc)
            except Exception:
                app.logger.exception("Polling sync failed unexpectedly")
            stop_event.wait(interval)

    thread = threading.Thread(target=_runner, name="sync-poller", daemon=True)
    thread.start()

    app.extensions["sync_poller_thread"] = thread
    app.extensions["sync_poller_stop_event"] = stop_event
