"""
Entry point. `python3 run.py` for local dev (mirrors the old `python3
app.py`); a real deployment should run this behind a WSGI server (gunicorn
`run:app`) instead of Flask's dev server.
"""
from app import create_app
from app.config import Config
from app.extensions import db
from app.seed import init_db_with_retry, seed_if_empty

app = create_app(Config)

with app.app_context():
    init_db_with_retry(app)
    seed_if_empty()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["FLASK_DEBUG"])
