from flask import Blueprint

bp = Blueprint("books", __name__, url_prefix="/api/books")

from app.books import routes  # noqa: E402,F401
