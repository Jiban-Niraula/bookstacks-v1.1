# Backend Refactor & Security Audit

Scope of this pass: **backend structure, JWT/auth security audit, automated
tests.** Frontend, new feature modules (reports, notifications, settings,
barcode/QR, etc.) are follow-up work, not covered here.

## 1. JWT bug audit

The brief's headline concern — `"sub": user.id` (int) vs. `"sub": str(user.id)`
— was **already fixed** in the version I received: `auth.py` set `"sub":
str(user.id)` and every route reading it did `int(request.current_user["sub"])`.
I audited every route that used `request.current_user` and confirmed there
was no remaining int-`sub` call site.

To make sure it can't quietly regress:

- The conversion now lives in one place — `app/decorators.py::current_user_id()`
  — instead of being repeated inline at each call site. Every route that
  needs the caller's numeric id calls this function instead of touching
  `request.current_user["sub"]` directly.
- `tests/test_jwt_security.py` pins this down with dedicated regression
  tests (`test_sub_claim_is_a_string_not_an_int`,
  `test_token_round_trips_through_decode_without_error`,
  `test_current_user_id_returns_int`), plus the wider JWT attack surface:
  expired tokens, tampered signatures, `alg=none` confusion, and role
  tampering. All fail the way a real attack would fail (401 / `InvalidTokenError`).

## 2. What changed structurally

Old layout: a single 446-line `app.py` plus `models.py` / `auth.py` /
`permissions.py`. New layout:

```
backend/
  run.py                  entry point (was: app.py's __main__ block)
  app/
    __init__.py            app factory — create_app(config)
    config.py               Config / TestConfig, env vars read exactly once here
    extensions.py            db, limiter (unbound, .init_app'd in the factory)
    errors.py                AppError + centralized error handlers
    decorators.py             login_required, permission_required, current_user_id()
    jwt_utils.py               generate_token / decode_token
    permissions.py             role -> permission table (unchanged logic)
    seed.py                    init_db_with_retry, seed_if_empty
    models/                    one file per table (user, member, book, loan)
    auth/  books/  members/  circulation/  dashboard/
      __init__.py               blueprint definition
      routes.py                  HTTP layer only — request in, jsonify out
      services.py                 business logic, DB queries
      validators.py                input validation (where applicable)
  tests/
    conftest.py                fixtures: app/client/db, role users, auth headers
    test_health.py
    test_auth.py
    test_jwt_security.py       <- the regression suite described above
    test_rbac.py                permission matrix per role
    test_books.py  test_members.py  test_circulation.py
```

**Every URL path is unchanged** (`/api/books`, `/api/members/<id>`,
`/api/circulation/issue`, `/api/my/loans`, etc.) — confirmed by diffing the
old `app.py` routes against `app.url_map` and grepping the frontend's JS for
every `/api/...` string it calls. The frontend needed zero changes.

Business logic that used to live inline in route handlers (borrow rules,
member-status checks, soft-delete-on-archive, "one loan per book per
borrower") moved into `services.py` per module — that's what made the
service layer independently testable without going through HTTP each time,
and it's the extension point for anything about to grow into a "reports"
or "notifications" module.

## 3. Security audit findings & fixes

| Area | Finding | Fix |
|---|---|---|
| JWT `sub` type | Already fixed on arrival | Centralized in `current_user_id()`, regression-tested |
| JWT algorithm | `decode()` already pinned `algorithms=["HS256"]` | Kept, added a test that an `alg=none` token is rejected |
| Prod secret key | `.env` ships a placeholder `SECRET_KEY`; nothing stopped `FLASK_DEBUG=false` running with the literal dev default | `Config.validate_for_production()` now refuses to boot if `FLASK_DEBUG=false` and `SECRET_KEY` is still `"dev-secret-change-me"` |
| Brute force on login/register | No rate limiting | Added `Flask-Limiter` (`10/min` login, `5/min` register by default, configurable via env) |
| User enumeration | N/A — already generic "invalid username or password" for both cases | Added a test asserting the two failure paths return an identical message |
| Unhandled exceptions | Flask default error page could leak stack traces if `FLASK_DEBUG` were left on in prod | `app/errors.py` catches everything, logs server-side, returns a generic `{"error": "Internal server error"}` in non-debug mode |
| SQL injection | All queries go through SQLAlchemy's ORM / parameterized `ilike()` — no raw string-built SQL anywhere | No change needed; confirmed by audit |
| RBAC coverage | Permissions table looked complete but wasn't exercised by tests | `test_rbac.py` — matrix of role × protected action, including confirming 401 (not logged in) is distinct from 403 (logged in, wrong role) |
| Soft-delete correctness | Member archive-on-delete existed but untested | Covered in `test_members.py` (archived from default list, still fetchable, loan history intact) |

Not yet done (flagged, not silently skipped): file upload validation (no
upload endpoints exist yet — will matter once cover images / logos land),
CSRF (not applicable yet — this is a pure JSON API, no cookie-based
sessions), production-grade rate-limit storage (currently in-memory, which
Flask-Limiter itself warns doesn't survive multiple worker processes — swap
for Redis when you're ready to run more than one backend process).

## 4. Test results

```
64 passed
Coverage: 93% overall (100% on every module except app/seed.py, which
needs a live Postgres retry loop to exercise meaningfully, and a handful of
defensive branches in error handlers / service edge cases)
```

Run it yourself:

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python3 -m pytest --cov=app --cov-report=term-missing
```

Tests run against in-memory SQLite (`app/config.py::TestConfig`) — no
Postgres required to run the suite.

## 5. Known pre-existing item not touched (flagging, not fixing)

`datetime.utcnow()` is used throughout (models, services) and raises a
`DeprecationWarning` on Python 3.12 (superseded by
`datetime.now(datetime.UTC)`). This was already the case before this pass,
it doesn't affect correctness today, and touching every call site is a
larger diff than "refactor + JWT audit + tests" scope — flagging it here as
a follow-up rather than bundling it into this change.
