"""
Centralized error handling. Two goals:

1. Every error response has the same JSON shape: {"error": "..."}.
2. Unhandled exceptions never leak a stack trace / internal detail to the
   client when FLASK_DEBUG is off -- they're logged server-side and turned
   into a generic 500 instead.
"""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("bookstacks")


class AppError(Exception):
    """Raise this for expected, user-facing errors ('book not found',
    'membership number already in use', ...). Routes can also just return
    jsonify(error=...), status directly -- this exists for service-layer
    code that doesn't have access to a response object."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify(error=err.message), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        # Covers 404s on unknown routes, 405 on wrong method, etc. -- keeps
        # the same {"error": ...} shape instead of Flask's default HTML page.
        return jsonify(error=err.description or err.name), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Unhandled exception")
        if app.config.get("FLASK_DEBUG"):
            # Local dev: still useful to see what broke.
            return jsonify(error=f"Internal error: {err}"), 500
        return jsonify(error="Internal server error"), 500
