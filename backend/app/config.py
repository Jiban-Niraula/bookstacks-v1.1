"""
Central configuration. All environment variables are read exactly once,
here -- nothing else in the codebase should call os.environ.get directly
for a setting that belongs in this table.
"""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

# Dev-only fallback. Config.validate_for_production() refuses to boot with
# this value once FLASK_DEBUG is off, so it can never end up signing tokens
# in anything that looks like a real deployment.
_DEV_SECRET_KEY = "dev-secret-change-me"


class Config:
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql://bookstacks:bookstacks@localhost:5432/bookstacks"
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY", _DEV_SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", 24))

    PORT = int(os.environ.get("PORT", 5000))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    # Brute-force protection on auth endpoints. See app/extensions.py.
    RATELIMIT_LOGIN = os.environ.get("RATELIMIT_LOGIN", "10 per minute")
    RATELIMIT_REGISTER = os.environ.get("RATELIMIT_REGISTER", "5 per minute")

    MIN_PASSWORD_LENGTH = 6

    @classmethod
    def validate_for_production(cls):
        """Called at startup when FLASK_DEBUG is false. Fails loudly rather
        than silently signing JWTs (including admin tokens) with a secret
        that ships in this repo's README."""
        if not cls.FLASK_DEBUG and cls.SECRET_KEY == _DEV_SECRET_KEY:
            raise RuntimeError(
                "Refusing to start: SECRET_KEY is still the dev default while "
                "FLASK_DEBUG=false. Set a real SECRET_KEY (e.g. "
                "`python3 -c \"import secrets; print(secrets.token_hex(32))\"`)."
            )


class TestConfig(Config):
    """Used by the pytest suite -- isolated in-memory SQLite, no reliance on
    a running Postgres instance, deterministic secret key."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-" + secrets.token_hex(8)
    FLASK_DEBUG = True
    TESTING = True
    RATELIMIT_ENABLED = False
