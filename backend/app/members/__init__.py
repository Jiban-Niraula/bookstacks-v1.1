from flask import Blueprint

bp = Blueprint("members", __name__, url_prefix="/api/members")

from app.members import routes  # noqa: E402,F401
