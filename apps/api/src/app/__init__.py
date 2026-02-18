from flask import Flask

from .config import apply_config
from .routes.health import health_bp
from .routes.pipelines import pipelines_bp
from .services.sync_poller import start_sync_poller


def create_app(test_config=None):
    app = Flask(__name__)
    apply_config(app)

    if test_config:
        app.config.update(test_config)

    app.register_blueprint(health_bp)
    app.register_blueprint(pipelines_bp)
    start_sync_poller(app)
    return app
