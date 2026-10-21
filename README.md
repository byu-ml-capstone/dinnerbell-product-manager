# DinnerBell Product Manager

The shared sprint planner the DinnerBell team uses to run its main project. It keeps stories, subtasks,
sprints, dependencies and each story's GitHub branch in one place, tracks velocity in points, and uses AI to
analyse sprint progress and to check whether the code on a sprint's branches backs up what the board says is done.

`SPRINT_PLANNER_SPEC.md` is the source of truth for how the app should behave. `SPRINT_PLANNER_DECISIONS.md`
records the team decisions behind it.

## What's in it

- **Login.** Username and password with open sign-up. A new user sees nothing until a member adds them to a project.
- **Board.** Five status columns with drag and drop. The dashboard shows status counts, the selected sprint, burndown, velocity and the team.
- **Sprints.** Status comes from the dates: a future start date means *planned*. Several sprints can be active at once, and closing is manual.
- **Planning.** The backlog and every open sprint side by side. You can drag stories between them, bulk-move them, and carry over unfinished work from closed sprints.
- **Stories.** Titles are unique within a project, points use the Fibonacci scale, and subtasks are full stories. Every field can be edited from the story drawer, which also shows sprint history and carry-over count.
- **Dependencies.** Blockers are managed from the story drawer. The read-only graph uses React Flow and dagre. Duplicate and circular blocker links are rejected, and the app warns when a story is planned before its blocker.
- **Soft delete.** Nothing is ever deleted for good. Children are deleted and restored with their parent, through a Trash tab and a 10-second Undo.
- **GitHub links.** Each project records its repo URL, and each story records a branch. The story drawer shows the suggested branch name and the live PR status.
- **AI.** Sprint analysis goes through the class LiteLLM proxy. The sprint review uses a Codex model that reads each story's code with read-only GitHub tools and gives an advice-only verdict.
- **Discussion.** Each sprint has its own board, with one level of replies.

## Layout

```
backend/                FastAPI + SQLAlchemy 2 + Alembic
  alembic/versions/     migrations (run on container start)
  app/main.py           app, lifespan, router registration, /health
  app/models.py         every table
  app/deps.py           login + "must be a member" helpers used by every route
  app/routers/          one module per area (auth, projects, stories, sprints, planning, metrics, …)
  app/services/         the rules: moves, soft delete, story events, metrics, AI, GitHub
  app/schemas/          request/response models per area
  scripts/ai_eval.py    manual prompt check against real AI settings (never in CI)
  tests/                pytest against Postgres, with fake AI and GitHub clients
frontend/               React (Vite), plain JSX, hand-written CSS
  src/App.jsx           login gate, sidebar, tab bar
  src/api/              fetch wrapper + one module per area
  src/components/       shared UI (modal, toast, error banner, …)
  src/features/<area>/  board, stories, sprints, planning, metrics, ai, graph, discussion, trash, settings
  src/styles/           stylesheets, imported in order from main.jsx
terraform/              optional: provisions the Coolify apps and GitHub secrets (see terraform/README.md)
```

## Run it locally

With Docker (closest to production):

```bash
SEED_DEMO_DATA=true docker compose up --build     # http://localhost:8080
./smoke-test.sh                                   # or: build, start and smoke-test in one go
```

`SEED_DEMO_DATA=true` seeds a demo project and four users, `taylor`, `jordan`, `casey` and `morgan`, all with
the password `devpassword`. Seeding only happens when the database has no projects. Never set it on staging or
production. To start from a clean database, run `docker compose down -v`.

Without Docker, for hot reload:

```bash
docker compose up -d db                           # Postgres on localhost:5432
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
SEED_DEMO_DATA=true .venv/bin/uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

## Configuration

These backend environment variables are set in Coolify for staging and production. See `backend/.env.example`.

| Variable | Secret? | Purpose |
|---|---|---|
| `DATABASE_URL` | no | Set by `docker-compose.yaml` |
| `APP_TIMEZONE` | no | Decides "today" for sprint status and burndown (default `America/Denver`) |
| `SESSION_COOKIE_SECURE` | no | `false` on the class deploy, which is HTTP only |
| `SEED_DEMO_DATA` | no | Local development only |
| `ANALYSIS_LLM_BASE_URL`, `ANALYSIS_LLM_MODEL` | no | Class LiteLLM proxy and model for sprint analysis |
| `ANALYSIS_LLM_API_KEY` | yes | LiteLLM key |
| `REVIEW_LLM_BASE_URL`, `REVIEW_LLM_MODEL` | no | Codex model for the sprint review. Leave the URL empty to call OpenAI directly |
| `REVIEW_LLM_API_KEY` | yes | OpenAI token or LiteLLM key |
| `GITHUB_TOKEN` | yes | Fine-grained, read-only token for the project repo (Contents, Pull requests, Metadata: read) |

When the AI or GitHub variables are empty, those features return a clear 503 and the rest of the app works.

## Tests

The tests run against Postgres, because partial unique indexes and JSON columns behave differently on SQLite.
**Every run drops and rebuilds the schema in the database you point it at.**

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql+psycopg://appuser:apppass@localhost:5432/appdb .venv/bin/pytest -q
.venv/bin/alembic check        # fails if models.py and the migrations disagree
cd ../frontend && npm run build
```

CI (`.github/workflows/ci.yml`) runs the same steps against a Postgres service container on every PR into
`staging` or `main`. CI never calls a real AI or GitHub API.

## Migrations

The schema is managed by Alembic. The backend container runs `alembic upgrade head` before starting, and a
failed migration stops the container.

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add something"   # then read the generated file
.venv/bin/alembic upgrade head
```

Use one migration per PR. If two PRs create two Alembic heads, whoever merges second points their
`down_revision` at the other migration. Back up production with `pg_dump` before merging a migration to `main`.

## Deploy

1. Branch off `staging` as `<name>/<task>` and open a PR into `staging`. It needs one approval and a green CI run.
2. Merging to `staging` deploys staging at `http://dinnerbell-product-manager-staging.ml-capstone.cs.byu.edu` (VPN).
3. When the team agrees staging is stable, merge `staging` into `main` with a merge commit. That deploys
   production at `http://dinnerbell-product-manager.ml-capstone.cs.byu.edu`.
4. Check it with `./smoke-test.sh <url>`. Set `SMOKE_USERNAME` and `SMOKE_PASSWORD` to also check login. The
   remote mode never writes data.

The deployed apps are HTTP only, because the class wildcard certificate doesn't cover these hostnames. Traffic is
encrypted by the VPN, so the session cookie isn't marked `Secure`. The hostname comes from the repository name.
`terraform/README.md` explains how the Coolify side was provisioned.
