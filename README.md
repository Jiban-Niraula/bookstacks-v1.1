# BookStacks

A small library app — three genuinely separate tiers, with real
authentication, roles, and borrow records tied to actual users. Meant to
be run locally. No Docker, no docker-compose, no CI/CD here — that part's
on you.

```
bookstacks/
├── frontend/     Node.js (Express)  — serves the UI, proxies API calls
│   ├── .env              local config (BACKEND_URL, PORT) — gitignored
│   ├── .env.example       template for the above
│   └── public/
│       ├── login.html     sign-in page
│       ├── register.html  create-account page
│       ├── index.html     the dashboard (catalog, loans, admin) — auth-gated
│       ├── css/styles.css shared stylesheet
│       └── js/
│           ├── session.js   shared token storage + authFetch helper
│           ├── login.js     login form handler
│           ├── register.js  register form handler
│           └── dashboard.js catalog / loans / admin logic
└── backend/      Python (Flask)     — auth, business logic, SQL
    ├── .env               local config (DATABASE_URL, SECRET_KEY, PORT) — gitignored
    ├── .env.example        template for the above
    ├── run.py               entry point: `python3 run.py`
    ├── app/                  modular Flask app (factory, blueprints, services)
    └── tests/                 pytest suite (64 tests, run with `python3 -m pytest`)
                                        (talks to Postgres over the network)
```

Backend internals were refactored from a single `app.py` into
`app/<module>/{routes,services,validators}.py` per domain (auth, books,
members, circulation, dashboard), plus a JWT/security audit and a pytest
suite. Every `/api/...` URL is unchanged, so this doesn't affect the
frontend at all. Details: `documentation/BACKEND_REFACTOR_AND_SECURITY_AUDIT.md`.

Login, registration, and the dashboard are three separate pages (not one
page with hidden sections) — `login.html`, `register.html`, and
`index.html`. Each guards itself: the dashboard redirects to `/login.html`
if there's no session, and the auth pages redirect straight to
`/index.html` if you're already signed in.

## How the pieces fit together

```
 Browser ── HTTP ──▶ frontend (Node, :3000) ── HTTP ──▶ backend (Python, :5000) ── SQL ──▶ Postgres (:5432)
```

- **frontend/** serves the GUI and proxies anything under `/api/*` to the
  backend, forwarding the `Authorization` header along with it. It holds
  no business logic and makes no auth decisions of its own.
- **backend/** owns everything: authentication, roles, the schema,
  borrow/return rules, search, and stats. It issues and verifies JWTs,
  hashes passwords, and talks to Postgres via SQLAlchemy.
- **database**: PostgreSQL, a real client-server database — started
  independently of the app, same as it will be as its own container once
  you write the compose file.

Because the browser only talks to the frontend, and the frontend
forwards to the backend server-to-server, no CORS configuration is
needed anywhere.

---

## What's actually in here now

- **Registration & login** — passwords are hashed (never stored in
  plain text), sessions are stateless JWTs (no server-side session
  store to keep in sync)
- **Roles & permissions** — `super_admin`, `librarian`, and `staff` are
  the real system roles, enforced via a permission table
  (`backend/permissions.py`) rather than scattered role checks:
  - **Super Admin** — everything
  - **Librarian** — full book/member/circulation management + reports
  - **Staff** — can issue/return books and look up books/members, but
    can't delete anything or manage settings
  - `member` still exists as a legacy self-registered login role (see
    "Members vs. self-service accounts" below) — it has no permissions
    in the new table by design
- **Members module** — patron records (`backend/models.py::Member`)
  that staff create and manage: membership number, contact info,
  status (active/suspended/archived), and full loan history. This is
  separate from `User` login accounts — see `/members.html`
- **Staff-mediated circulation** — `POST /api/circulation/issue` and
  `POST /api/circulation/return/<loan_id>` let Staff/Librarian/Super
  Admin issue or receive a book on behalf of a Member (the real "staff
  works the circulation desk" workflow), distinct from the
  self-service `/api/books/<id>/borrow|return` below
- **Real borrow records** — instead of a simple "available copies"
  counter, every borrow creates a row in a `loans` table tied to a
  book and either a `user_id` (self-service) or `member_id`
  (staff-issued), with a due date and return timestamp. Availability
  is *derived* from active loans, not tracked separately — one source
  of truth, no way for the numbers to drift apart
- **"My borrowed books"** — self-service users see their own active
  loans, with overdue ones flagged (14-day loan period)
- **Delete protection** — a book can't be deleted while it's currently
  borrowed by anyone; a member can't be archived while they have books
  checked out (archiving is a soft-delete — loan history is kept)

### Members vs. self-service accounts

This project currently has two separate ways someone ends up borrowing
a book, and it's worth knowing which is which:

1. **Self-service** — anyone can register a login at `/register.html`
   and borrow/return books for themselves from the dashboard. Simple,
   but doesn't match how most school/college libraries actually run
   (patrons don't usually get their own login).
2. **Staff-managed Members** — the `/members.html` page, where
   Librarian/Staff create a Member record (no login needed) and issue
   books to them from the desk. This is the realistic workflow for a
   commercial deployment.

Both currently coexist. Whether to keep self-service login around
long-term (as a patron portal) or retire it in favor of Members-only
circulation is still an open decision.

A seeded **super admin** account is created automatically on first run:
```
username: admin
password: admin123
```
Change or remove this in any real deployment — it exists purely so you
can log in and test every role's actions without hand-editing the
database.

---

## Prerequisites

- **Node.js 18+**
- **Python 3.9+** and **pip**
- **PostgreSQL 13+** — installed locally, or run ad-hoc via Docker
  (below). Either way, this isn't the app's own Dockerfile/compose —
  just an existing Postgres image to have a database to point at.

---

## 1. Get a Postgres server running

### Option A — quickest: Postgres via Docker

```bash
docker run --name bookstacks-db \
  -e POSTGRES_USER=bookstacks \
  -e POSTGRES_PASSWORD=bookstacks \
  -e POSTGRES_DB=bookstacks \
  -p 5432:5432 \
  -d postgres:16
```

### Option B — install natively

```bash
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER bookstacks WITH PASSWORD 'bookstacks';"
sudo -u postgres psql -c "CREATE DATABASE bookstacks OWNER bookstacks;"
```

Either way you should end up with Postgres on `localhost:5432`, database
`bookstacks`, user `bookstacks`, password `bookstacks` — the backend's
defaults. See Configuration below to use different ones.

---

## 2. Run the backend

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python3 run.py
```

`backend/.env` already ships with working local defaults (matching the
Postgres container/user above) and is loaded automatically — you don't
need to export anything by hand for local dev. See **Configuration**
below before this goes anywhere other people can reach it.

On first run it creates the `users`, `books`, and `loans` tables, seeds
the three sample books and the admin account. If Postgres isn't ready
yet, it retries a few times with a short delay — you may see
`Database not ready yet (attempt X/10)` right after starting a fresh
Postgres container; that's expected.

**Leave this running in its own terminal.**

```bash
curl http://localhost:5000/api/health
```

---

## 3. Run the frontend

In a **new terminal**:

```bash
cd frontend
npm install
node index.js
```

`frontend/.env` ships with local defaults too (`BACKEND_URL=http://localhost:5000`,
`PORT=3000`) and is loaded automatically via `dotenv`.

Open **http://localhost:3000** — this loads `login.html`. Log in with the
seeded admin account, or register a new (member) account from
`http://localhost:3000/register.html`.

---

## Configuration

Both apps read their settings from a `.env` file in their own folder
(`backend/.env`, `frontend/.env`), loaded automatically on startup. Each
folder also has a `.env.example` — copy it to `.env` if you ever need to
start from scratch:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**`backend/.env`**:
- `DATABASE_URL` — defaults to the local Postgres setup above
- `SECRET_KEY` — signs JWTs; ships with a dev-only placeholder value.
  **Set this to something real in any deployment** — anyone who knows
  this value can forge valid tokens, including admin tokens. Generate one
  with `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `PORT` — what port Flask listens on (default `5000`)
- `FLASK_DEBUG` — `true` for local dev, `false` anywhere shared

You can still override any of these with real environment variables at
launch time (they take precedence over `.env`):
```bash
SECRET_KEY=something-long-and-random python3 run.py
```

**`frontend/.env`**:
- `BACKEND_URL` — where the Flask API is listening (default `http://localhost:5000`)
- `PORT` — what port this Express server listens on (default `3000`)

```bash
PORT=3001 BACKEND_URL=http://localhost:5000 node index.js
```

`.env` files are gitignored — don't commit real secrets in them.

---

## API reference

Public (no token required):

| Method | Path                       | Notes                            |
|--------|----------------------------|-----------------------------------|
| GET    | `/api/health`               | backend liveness check            |
| GET    | `/api/stats`                 | totals across all books           |
| GET    | `/api/books`                 | list all books                    |
| GET    | `/api/books/search?q=...`    | matches title, author, or genre   |
| POST   | `/api/auth/register`         | `{ username, email, password }` (password ≥ 6 chars) |
| POST   | `/api/auth/login`            | `{ username, password }` → `{ token, user }` |

Requires `Authorization: Bearer <token>`:

| Method | Path                          | Permission required           | Notes                                          |
|--------|-------------------------------|--------------------------------|--------------------------------------------------|
| GET    | `/api/auth/me`                 | any logged-in user             | current user's own info                          |
| GET    | `/api/my/loans`                 | any logged-in user             | the current user's self-service borrow history   |
| POST   | `/api/books/:id/borrow`         | any logged-in user (self-service) | fails if no copies left, or you already have it |
| POST   | `/api/books/:id/return`         | any logged-in user (self-service) | non-staff: only their own loans; anyone with `circulation:return`: any loan |
| POST   | `/api/books`                     | `books:create`                | `{ title, author, genre?, copies? }`            |
| DELETE | `/api/books/:id`                 | `books:delete`                | fails if the book is currently borrowed          |
| GET    | `/api/members`                   | `members:read`                | `?q=` searches name/membership#/phone/email      |
| POST   | `/api/members`                   | `members:create`              | `{ membershipNumber, fullName, email?, phone?, address?, notes? }` |
| GET    | `/api/members/:id`                | `members:read`                | includes full loan history                       |
| PUT    | `/api/members/:id`                | `members:update`              | partial update; `status` must be active\|suspended\|archived |
| DELETE | `/api/members/:id`                | `members:delete`              | soft-delete (archives); fails if active loans     |
| POST   | `/api/circulation/issue`          | `circulation:issue`           | `{ bookId, memberId }` — staff issues a book to a member |
| POST   | `/api/circulation/return/:loan_id` | `circulation:return`         | staff receives a returned book                    |

See `backend/permissions.py` for exactly which roles grant which permission.

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -X POST http://localhost:5000/api/books \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","genre":"Dystopian","copies":2}'

curl http://localhost:5000/api/my/loans -H "Authorization: Bearer $TOKEN"
```

---

## Resetting the database

```bash
psql postgresql://bookstacks:bookstacks@localhost:5432/bookstacks \
  -c "DROP TABLE IF EXISTS loans, books, users CASCADE;"
# then restart the backend — tables + seed data are recreated automatically
```

Or, if using the Docker option: `docker rm -f bookstacks-db` and re-run
the `docker run` command from step 1.

---

## Troubleshooting

- **"Database not ready yet" repeats then fails** → Postgres isn't
  running, or `DATABASE_URL` is wrong. Check with
  `psql $DATABASE_URL -c '\dt'`.
- **401 on every protected request right after logging in** → check the
  browser's dev tools → Application → Local Storage for `bookstacks_token`.
  If it's missing, login didn't complete; check the Network tab for the
  actual error from `/api/auth/login`.
- **"Admin access required" but you're logged in as admin** → the seeded
  admin's token was issued before you changed `SECRET_KEY`, or you're
  actually logged in as a different (member) account — log out and back
  in.
- **Frontend loads but nothing populates** → backend isn't running, or
  `BACKEND_URL` doesn't match where it's listening.

---

## Notes for later (CI/CD, Docker)

Deliberately left out — build these yourself:
- Dockerfiles for `frontend/` and `backend/`
- `docker-compose.yml` wiring `frontend`, `backend`, and a `postgres`
  service — remember `DATABASE_URL` needs to point at the **service
  name** (e.g. `db`), not `localhost`, once everything's on the same
  Docker network
- A named volume for Postgres so data survives `docker compose down`
- **Set a real `SECRET_KEY`** via compose env vars or a secrets
  mechanism — don't ship the dev default
- Any CI workflow / deploy script
