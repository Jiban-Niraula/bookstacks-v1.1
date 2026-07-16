from flask import current_app

from app.errors import AppError


def validate_registration(data):
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        raise AppError("username, email, and password are required", 400)
    if len(password) < current_app.config["MIN_PASSWORD_LENGTH"]:
        raise AppError(
            f"password must be at least {current_app.config['MIN_PASSWORD_LENGTH']} characters", 400
        )
    return username, email, password
