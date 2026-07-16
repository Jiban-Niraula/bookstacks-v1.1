from flask import Blueprint

bp = Blueprint("dashboard", __name__, url_prefix="/api")

from app.dashboard import routes  # noqa: E402,F401
