"""
Application factory. Nothing in this package should import a concrete
Config at module load time -- everything goes through create_app(config)
so tests can build an isolated app (SQLite, rate limiting off) without
touching the real Postgres-backed one.
"""
import logging

from flask import Flask

from app.config import Config
from app.extensions import db, limiter
from app.errors import register_error_handlers


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.validate_for_production()

    logging.basicConfig(level=logging.INFO if not app.config["FLASK_DEBUG"] else logging.DEBUG)

    db.init_app(app)
    limiter.init_app(app)
    register_error_handlers(app)

    from app.auth import bp as auth_bp
    from app.books import bp as books_bp
    from app.circulation import bp as circulation_bp
    from app.dashboard import bp as dashboard_bp
    from app.members import bp as members_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(circulation_bp)
    app.register_blueprint(dashboard_bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "bookstacks-backend"}

    return app
