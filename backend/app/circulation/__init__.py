from flask import Blueprint

# No url_prefix: this blueprint intentionally owns three different URL
# namespaces that already exist in the public API contract --
# /api/books/<id>/borrow|return (self-service), /api/circulation/*
# (staff-mediated), and /api/my/loans (a user's own history). Splitting
# those across separate blueprints would just fragment one workflow.
bp = Blueprint("circulation", __name__)

from app.circulation import routes  # noqa: E402,F401
