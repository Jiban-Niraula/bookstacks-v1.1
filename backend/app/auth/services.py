from app.errors import AppError
from app.extensions import db
from app.jwt_utils import generate_token
from app.models import User


def register_user(username, email, password):
    if User.query.filter_by(username=username).first():
        raise AppError("that username is already taken", 409)
    if User.query.filter_by(email=email).first():
        raise AppError("that email is already registered", 409)

    user = User(username=username, email=email, role="member")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(username, password):
    username = (username or "").strip()
    user = User.query.filter_by(username=username).first()
    # Deliberately the same generic message whether the username doesn't
    # exist or the password is wrong -- avoids leaking which usernames
    # are registered (user enumeration).
    if not user or not user.check_password(password or ""):
        raise AppError("invalid username or password", 401)
    return user


def issue_token_response(user, status_code=200):
    return {"token": generate_token(user), "user": user.to_dict()}, status_code
