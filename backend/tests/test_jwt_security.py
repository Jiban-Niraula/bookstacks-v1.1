"""
Regression suite for the PyJWT 2.13+ "sub must be a string" bug, plus the
general JWT attack surface (tampering, expiry, algorithm confusion).

The historical bug: generate_token() used to put an int in the "sub"
claim ("sub": user.id). Newer PyJWT enforces the JWT spec, which requires
"sub" to be a string, and raises InvalidSubjectError on decode otherwise --
so every authenticated request would 401. The fix is "sub": str(user.id) at
encode time and int(request.current_user["sub"]) wherever it's used as a
database id. This file exists so that regression can never silently come
back.
"""
import time
from datetime import datetime, timedelta

import jwt
import pytest

from app.decorators import current_user_id
from app.jwt_utils import decode_token, generate_token


def test_sub_claim_is_a_string_not_an_int(app, super_admin):
    with app.app_context():
        token = generate_token(super_admin)
        decoded = decode_token(token)
    assert isinstance(decoded["sub"], str)
    assert decoded["sub"] == str(super_admin.id)


def test_token_round_trips_through_decode_without_error(app, super_admin):
    """This is the exact failure mode of the historical bug: decode() used
    to raise InvalidSubjectError here on newer PyJWT."""
    with app.app_context():
        token = generate_token(super_admin)
        decoded = decode_token(token)  # must not raise
    assert int(decoded["sub"]) == super_admin.id


def test_authenticated_request_resolves_correct_user_id(client, make_headers, staff):
    resp = client.get("/api/auth/me", headers=make_headers(staff))
    assert resp.status_code == 200
    assert resp.get_json()["id"] == staff.id


def test_current_user_id_returns_int(app, super_admin):
    with app.test_request_context(
        "/api/auth/me", headers={"Authorization": f"Bearer {generate_token(super_admin)}"}
    ):
        from flask import request

        from app.jwt_utils import decode_token as _decode
        request.current_user = _decode(request.headers["Authorization"][7:])
        uid = current_user_id()
        assert isinstance(uid, int)
        assert uid == super_admin.id


# ---- Attack surface: tampering, expiry, malformed tokens ----

def test_rejects_missing_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_rejects_malformed_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert resp.status_code == 401


def test_rejects_token_with_wrong_signature(app, super_admin):
    with app.app_context():
        real_token = generate_token(super_admin)

    # Re-sign the same payload with a different key -- simulates an
    # attacker who knows the payload shape but not the server's secret.
    payload = jwt.decode(real_token, options={"verify_signature": False})
    forged = jwt.encode(payload, "attacker-controlled-key", algorithm="HS256")

    with app.app_context():
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(forged)


def test_rejects_expired_token(app, super_admin):
    with app.app_context():
        payload = {
            "sub": str(super_admin.id),
            "username": super_admin.username,
            "role": super_admin.role,
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired)


def test_expired_token_rejected_at_the_http_layer(app, client, super_admin):
    with app.app_context():
        payload = {
            "sub": str(super_admin.id),
            "username": super_admin.username,
            "role": super_admin.role,
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_rejects_alg_none_token(app, super_admin):
    """Algorithm-confusion attack: a token that declares alg=none and has
    no signature at all. decode_token pins algorithms=["HS256"] explicitly,
    which is what prevents this -- never let the token's own header choose
    the algorithm."""
    with app.app_context():
        payload = {
            "sub": str(super_admin.id),
            "username": super_admin.username,
            "role": "super_admin",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        forged = jwt.encode(payload, "", algorithm="none")
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(forged)


def test_role_tampering_is_caught_by_signature_check(app, staff):
    """A staff user cannot escalate to super_admin by editing the decoded
    payload and re-encoding without the server's real secret key."""
    with app.app_context():
        token = generate_token(staff)

    payload = jwt.decode(token, options={"verify_signature": False})
    payload["role"] = "super_admin"
    forged = jwt.encode(payload, "guessed-wrong-key", algorithm="HS256")

    with app.app_context():
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(forged)


def test_refuses_to_boot_with_dev_secret_in_production_mode():
    """SECRET_KEY signs every JWT including admin tokens -- shipping the
    documented dev default in a real deployment lets anyone forge a valid
    super_admin token. The app must refuse to start rather than silently
    running insecurely."""
    from app import create_app
    from app.config import Config

    class BadProdConfig(Config):
        FLASK_DEBUG = False
        SECRET_KEY = "dev-secret-change-me"

    with pytest.raises(RuntimeError):
        create_app(BadProdConfig)
