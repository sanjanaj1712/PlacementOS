# PlacementOS

PlacementOS is a placement preparation tracker for students. You set placement goals, work through subject learning paths (DSA, Operating Systems, Computer Networks, DBMS), track job applications through the hiring pipeline, and see all of it on one dashboard.

## Features

| Feature | What it does |
| --- | --- |
| Authentication | Sign up and log in with Supabase Auth. App pages require a session, and the Flask API verifies every Supabase access token itself. |
| Profile | View and update name, education, college, graduation year and preferred roles. |
| Goals | Create, view, edit and delete goals: target role, company type, target companies, target date, status and progress. |
| Learning paths | Browse subjects, open a path, see topics and subtopics, and mark them complete. Progress is saved per user. |
| Preparation tracking | Completion per subject and overall. |
| Applications | Add companies and roles with details (type, location, job URL, dates, notes). Move them through the pipeline **Interested → Applied → OA → Interview → Offer / Rejected**. Invalid moves (for example Rejected → Offer) are refused. |
| Dashboard | Current goal, topic completion, application pipeline counts, per-subject progress and recent activity. |

## Architecture

```
Next.js (frontend/)  ──Bearer token──▶  Flask REST API (backend/)  ──SQL──▶  PostgreSQL (Supabase)
        │                                      │
        └── Supabase Auth (sign up / log in)   └── verifies Supabase JWTs locally (HS256 secret or JWKS)
```

- **frontend/**: Next.js 16 (App Router) with Tailwind CSS. `supabase-js` handles sign-in and keeps the session refreshed. `src/lib/api.js` sends the current access token to Flask on every request.
- **backend/**: a Flask API in `app.py`, using `psycopg` for PostgreSQL. Every query is scoped to the user ID from the verified token, so one user can't read or change another user's data.
- **backend/db/**: `schema.sql` (tables, cascading foreign keys, row level security), `seed.sql` (learning path catalogue) and `migrations/` (for databases created before these changes).

### API

All endpoints except `/` and `/login` need `Authorization: Bearer <supabase access token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/me` | Current user |
| GET, PATCH | `/profile` | Read or update the profile (created automatically on first access) |
| GET, POST | `/goals` | List or create goals |
| PATCH, DELETE | `/goals/<id>` | Update or delete a goal |
| GET | `/learning-paths` | Paths with the user's topic counts and completion |
| GET | `/learning-paths/<id>/topics` | Topics and subtopics with the user's progress |
| GET, POST | `/progress` | List progress, or create or update progress for a topic (upsert) |
| PATCH, DELETE | `/progress/<id>` | Update or delete a progress record |
| GET, POST | `/applications` | List or create applications |
| PATCH, DELETE | `/applications/<id>` | Update (including pipeline status) or delete an application |
| GET | `/dashboard` | All dashboard numbers in one request |

## Setup

### Prerequisites

- Python 3.11+ (developed on 3.13)
- Node.js 20+
- A Supabase project
- PostgreSQL 15+ (only needed to run the backend tests locally)

### 1. Database

In the Supabase dashboard, open **SQL editor** and run, in order:

1. `backend/db/schema.sql`
2. `backend/db/seed.sql`

If your database was created with an earlier version of this project, run `backend/db/migrations/001_harden_schema.sql` instead of `schema.sql`, then run `seed.sql`. The migration runs in a single transaction and never deletes rows. If it finds duplicate progress rows or orphaned records, it stops and tells you what to fix.

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then fill in the values
python app.py           # http://127.0.0.1:5000
```

On macOS, AirPlay Receiver also listens on port 5000. Use `127.0.0.1` rather than `localhost` in URLs, or set `PORT=5001`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # then fill in the values
npm run dev                   # http://localhost:3000
```

## Environment variables

Real values go in `backend/.env` and `frontend/.env.local`. Both files are gitignored. Never commit them.

### backend/.env

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | yes | Postgres connection string (Supabase → Project Settings → Database). |
| `SUPABASE_URL` | yes | `https://<project-ref>.supabase.co`. It is also used as the expected token issuer. |
| `SUPABASE_KEY` | yes | Supabase publishable (anon) key, used only by the `/login` endpoint. Do **not** use the service role key. |
| `SUPABASE_JWT_SECRET` | no | Legacy HS256 JWT secret. Leave empty if the project uses asymmetric signing keys; tokens are then verified against the project's JWKS endpoint. |
| `CORS_ORIGINS` | no | Comma-separated allowed frontend origins. Default: `http://localhost:3000,http://127.0.0.1:3000`. |
| `PORT` | no | API port. Default: `5000`. |
| `FLASK_DEBUG` | no | `1` enables debug mode. Local development only. |

### frontend/.env.local

| Variable | Required | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | yes | Same project URL as the backend. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | yes | Supabase publishable (anon) key. |
| `NEXT_PUBLIC_API_URL` | no | Flask API URL. Default: `http://127.0.0.1:5000`. |

## Running the tests

The backend tests run against a real, **disposable local** PostgreSQL database. They load the schema and seed data, create test users, and delete those users (and, through the cascades, their data) after each test. The test harness refuses to run if `TEST_DATABASE_URL` points anywhere other than localhost.

```bash
createdb placementos_test
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/placementos_test python -m pytest
```

The tests use locally signed JWTs, so they need neither Supabase nor a network connection. They cover:

- token verification (missing, malformed, expired, wrongly signed, unsigned, wrong audience, issuer or role)
- two-user data isolation on every resource
- input validation on every write endpoint
- application status transitions
- progress upserts
- cascade deletes with no orphaned rows
- dashboard numbers compared against direct SQL queries
- query counts that stay constant as data grows (no N+1)

For the frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Security notes

- Flask verifies the token signature, expiry, audience (`authenticated`), issuer and role locally. It does not trust anything the client sends about who the user is.
- Row level security is enabled on every table, so the public anon key cannot be used to read other users' data through Supabase's REST API.
- Error responses never include database or internal error details.
- Job and resource links are only rendered when they use `http` or `https`.
