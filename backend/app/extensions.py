"""
Shared extension instances. Created here (unbound), initialized in the app
factory (app/__init__.py) via .init_app(app) -- this is what lets tests spin
up a fresh app without any global state leaking between them.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

limiter = Limiter(key_func=get_remote_address)
