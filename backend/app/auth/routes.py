from flask import current_app, jsonify, request

from app.auth import bp
from app.auth.services import authenticate, issue_token_response, register_user
from app.auth.validators import validate_registration
from app.decorators import current_user_id, login_required
from app.extensions import db, limiter
from app.models import User


@bp.post("/register")
@limiter.limit(lambda: current_app.config["RATELIMIT_REGISTER"])
def register():
    data = request.get_json(silent=True) or {}
    username, email, password = validate_registration(data)
    user = register_user(username, email, password)
    body, status = issue_token_response(user, status_code=201)
    return jsonify(**body), status


@bp.post("/login")
@limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN"])
def login():
    data = request.get_json(silent=True) or {}
    user = authenticate(data.get("username"), data.get("password"))
    body, status = issue_token_response(user)
    return jsonify(**body), status


@bp.get("/me")
@login_required
def me():
    user = db.session.get(User, current_user_id())
    if not user:
        return jsonify(error="user not found"), 404
    return jsonify(user.to_dict())
