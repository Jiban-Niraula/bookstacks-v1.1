"""
Auth decorators. login_required verifies the token; permission_required
additionally checks the role -> permission table (app/permissions.py).

Never check request.current_user["role"] == "librarian" in a route --
always go through permission_required(...) so app/permissions.py stays the
single source of truth for who can do what.
"""
from functools import wraps

import jwt
from flask import jsonify, request

from app.jwt_utils import decode_token
from app.permissions import role_has_permission


def _get_token_from_request():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def login_required(fn):
    """Requires a valid Bearer token. Sets request.current_user to the
    decoded payload ({"sub", "username", "role", "iat", "exp"})."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return jsonify(error="Authentication required"), 401
        try:
            request.current_user = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify(error="Session expired, please log in again"), 401
        except jwt.InvalidTokenError:
            # Covers a bad signature, tampered payload, wrong algorithm,
            # malformed token, missing/non-string "sub", etc.
            return jsonify(error="Invalid session"), 401
        return fn(*args, **kwargs)
    return wrapper


def permission_required(permission):
    """Requires a valid Bearer token AND that the user's role grants
    `permission` (see app/permissions.py for the role -> permission table).

    Usage: @permission_required("books:delete")
    """
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            role = request.current_user.get("role")
            if not role_has_permission(role, permission):
                return jsonify(error="You don't have permission to do that"), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user_id():
    """The authenticated user's database id, correctly converted from the
    string "sub" claim. Only call this inside a @login_required /
    @permission_required route."""
    return int(request.current_user["sub"])
