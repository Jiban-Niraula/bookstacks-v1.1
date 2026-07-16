"""
JWT issuing/verification. Isolated from Flask request handling so it can be
unit-tested directly (tamper with a token, feed it a wrong key, etc.)
without spinning up routes.
"""
from datetime import datetime, timedelta

import jwt
from flask import current_app


def generate_token(user):
    payload = {
        # PyJWT 2.13+ requires "sub" to be a string per the JWT spec --
        # decode() raises InvalidSubjectError if it's an int. Always convert
        # back with int(...) wherever the sub claim is used as a database id
        # (see app/decorators.py::current_user_id()).
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=current_app.config["TOKEN_EXPIRY_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=current_app.config["JWT_ALGORITHM"])


def decode_token(token):
    # algorithms is passed explicitly (not "whatever the token header says")
    # -- this is what prevents an alg-confusion attack where a tampered
    # token claims a different/weaker algorithm.
    return jwt.decode(
        token,
        current_app.config["SECRET_KEY"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )
