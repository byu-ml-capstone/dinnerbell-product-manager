# CLAUDE.md

Shared instructions for the LLMs that write code in this repo (D-10).

## What this is

DinnerBell Product Manager is the team's sprint planner. `SPRINT_PLANNER_SPEC.md` is the source of truth for
behaviour. When you implement something, cite the spec IDs in the PR description (for example, "Implements
MOVE-6"). If the spec and the code disagree, say so rather than guessing.

## Layout

- Backend: `backend/app/`.
  - Routers in `routers/` stay thin. Rules live in `services/`.
  - Request and response models live in `schemas/<area>.py`.
  - All tables live in `models.py`.
- Frontend: `frontend/src/`.
  - API calls go in `api/<area>.js`.
  - Shared UI goes in `components/`.
  - Each area has its own `features/<area>/` folder.
  - Styles live in `styles/`.
- Area owners (D-2):
  - Johnny: platform, login, soft delete.
  - Bella: workflow, moves, metrics.
  - Eason: GitHub, AI.
  - Taft: graph, discussion.

## Commands

```bash
docker compose up --build                       # full stack on :8080 (SEED_DEMO_DATA=true for demo data)
docker compose up -d db                         # just Postgres on :5432
cd backend && DATABASE_URL=postgresql+psycopg://appuser:apppass@localhost:5432/appdb .venv/bin/pytest -q
cd backend && .venv/bin/alembic revision --autogenerate -m "what changed"
cd backend && .venv/bin/alembic check
cd frontend && npm run dev                      # :5173, proxies /api to :8000
cd frontend && npm run build
./smoke-test.sh
```

The test suite drops and rebuilds the schema of whatever `DATABASE_URL` points at. Never point it at a real database.

## Rules

- **Membership checks.** Every endpoint reaches its project through the helpers in `app/deps.py`
  (`get_project_for_member`, `get_story_for_member`, …), so login and membership are always checked (X-9). There
  is one role; every member can do everything (D-14).
- **Migrations.** Every change to `models.py` comes with an Alembic migration (MIG-4). `alembic check` must pass.
- **Story events.** Status, sprint and points changes go through `services/moves.py` and `services/events.py`.
  Never set `story.sprint_id` or `story.status` without recording the event. Burndown and history depend on it (VEL-6, MOVE-11).
- **No hard deletes.** Use `services/soft_delete.py` (D-26). Normal queries hide soft-deleted rows automatically.
  Only Trash and restore code passes `execution_options(include_deleted=True)`.
- **AI and GitHub calls.** Never call an AI provider or GitHub from a router. Use `services/llm.py` and
  `services/github_client.py`, which are FastAPI dependencies so tests can swap in fakes. AI output is advice
  only; it never changes data (D-36).
- **Status.** `blocked` is set by people. Dependencies never change a story's status (D-20).
- **Time.** Use `services/clock.py` (`clock.now()`, `clock.today()`) so tests can freeze time.
- **Tests.** Every new or changed endpoint gets tests for the success case, a 403 for non-members, and one
  failure case (TEST-2). Tests live in `backend/tests/test_<router>.py` and use the fakes in `tests/fakes.py`.
- **Formatting and scope.** Don't reformat code you didn't change (TEST-6). Stay inside your area's folders
  unless the PR explains why (A-5).
- **Secrets.** No secrets in code, logs or prompts (NFR-3).

## Git

Branch off `staging` as `<name>/<task>`, for example `johnny/login-page` (D-6, A-4). Open PRs into `staging`.
Each PR needs one approval and a green CI run (D-4), and is merged with a merge commit (D-5).
