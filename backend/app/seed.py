"""
Startup DB bootstrap: retry-tolerant table creation + first-run seed data.
Kept separate from the app factory so tests can skip it entirely (the test
fixture creates tables directly against SQLite with no seed data, or seeds
explicitly per-test).
"""
import logging
import time

from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import Book, User

logger = logging.getLogger("bookstacks")


def init_db_with_retry(app, max_retries=10, delay_seconds=2):
    """Postgres often isn't accepting connections the instant it starts --
    retry instead of crashing on the first attempt."""
    for attempt in range(1, max_retries + 1):
        try:
            db.create_all()
            return
        except OperationalError as exc:
            logger.warning("Database not ready yet (attempt %s/%s): %s", attempt, max_retries, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(
        f"Could not connect to the database at {app.config['SQLALCHEMY_DATABASE_URI']} "
        f"after {max_retries} attempts. Is Postgres running?"
    )


def seed_if_empty():
    if User.query.count() == 0:
        admin = User(username="admin", email="admin@bookstacks.local", role="super_admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if Book.query.count() == 0:
        db.session.add_all([
            Book(title="Clean Code", author="Robert C. Martin", genre="Software", total_copies=2),
            Book(title="The Pragmatic Programmer", author="Andrew Hunt", genre="Software", total_copies=1),
            Book(title="Dune", author="Frank Herbert", genre="Sci-Fi", total_copies=3),
        ])

    db.session.commit()
