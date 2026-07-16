import jwt
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models import Book, Member, User


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


def _make_user(db, username, role, password="password123"):
    user = User(username=username, email=f"{username}@test.local", role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def super_admin(db):
    return _make_user(db, "super_admin_1", "super_admin")


@pytest.fixture()
def librarian(db):
    return _make_user(db, "librarian_1", "librarian")


@pytest.fixture()
def staff(db):
    return _make_user(db, "staff_1", "staff")


@pytest.fixture()
def member_role_user(db):
    """A self-registered patron account with the legacy 'member' role
    (no RBAC permissions) -- distinct from the Member model below."""
    return _make_user(db, "patron_1", "member")


@pytest.fixture()
def make_headers(app):
    """Returns a function that builds a valid Authorization header for a
    given user, evaluated inside the app's context."""
    def _make(user):
        from app.jwt_utils import generate_token
        with app.app_context():
            token = generate_token(user)
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture()
def sample_book(db):
    book = Book(title="Test-Driven Development", author="Kent Beck", genre="Software", total_copies=2)
    db.session.add(book)
    db.session.commit()
    return book


@pytest.fixture()
def sample_member(db):
    member = Member(membership_number="M-0001", full_name="Ada Lovelace", status="active")
    db.session.add(member)
    db.session.commit()
    return member
