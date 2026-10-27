# DinnerBell Product Manager

The shared sprint planner the DinnerBell team uses to run its main project. It keeps stories, subtasks,
sprints, dependencies and each story's GitHub branch in one place, tracks velocity in points, and uses AI to
analyse sprint progress and to check whether the code on a sprint's branches backs up what the board says is done.

`SPRINT_PLANNER_SPEC.md` is the source of truth for how the app should behave. `SPRINT_PLANNER_DECISIONS.md`
records the team decisions behind it.

## Try it out

You need **git** and **Docker Desktop**, and Docker Desktop has to be running. You don't need Python or Node.

1. **Get the branch:**

   ```bash
   git fetch
   git checkout staging
   git pull
   ```

2. **Start the app with demo data:**

   ```bash
   cp .env.example .env          # Windows Command Prompt: copy .env.example .env
   docker compose down -v        # first time only: clears any database left over from the old app
   docker compose up --build
   ```

   The first build takes a few minutes. The app is ready once the log shows `dinnerbell-product-manager-frontend-1`
   started. You'll keep seeing log lines after that, which is normal.

3. **Open http://localhost:8080** and log in as `taylor`, password `devpassword`. `jordan`, `casey` and `morgan`
   use the same password. You can also create your own account, but you won't see any projects until someone adds
   you to one in Settings.

4. **Things to try:**
   - **Board:** drag a story to another column, or click a story to edit it in the drawer.
   - **Planning:** drag stories between the backlog and the sprints.
   - **Graph:** add a blocker from a story's drawer, then look at the Graph tab.
   - **Closing a sprint:** close one from the Sprint panel, then use "Move unfinished stories…".
   - **Deleting:** delete something, then click Undo or restore it from Trash.
   - **Discussion:** post in a sprint's Discussion tab.

5. **To stop it**, press `Ctrl+C`, then run `docker compose down`. Your local data is kept until you run
   `docker compose down -v`.

The demo data, a "DinnerBell Demo" project with three sprints, is only created when the database has no projects.
The AI features say "not configured" until the AI keys are set. That's expected; everything else works without them.

### If something goes wrong

Start with `docker compose ps`. All three services, `db`, `backend` and `frontend`, should show as running.
`docker compose logs backend` usually explains the rest. These are the problems you're most likely to hit:

| What you see | Why | How to fix it |
|---|---|---|
| `Cannot connect to the Docker daemon … Is the docker daemon running?` | Docker Desktop isn't running. | Start Docker Desktop, wait until it says it's running, and run the command again. |
| `dependency failed to start: container dinnerbell-product-manager-backend-1 is unhealthy`, and the backend keeps restarting. `docker compose logs backend` shows `relation "users" already exists`. | Your local database still has tables from the old app, so the new schema can't be created. | `docker compose down -v`, then `docker compose up --build`. This only deletes your local data. |
| `dependency failed to start: … backend-1 is unhealthy`, with some other error in `docker compose logs backend` | The backend failed for another reason, shown in the log. | Read the last error in `docker compose logs backend`. If you can't tell what's wrong, do a full reset (last row of this table). |
| `Bind for 0.0.0.0:5432 failed: port is already allocated`, or the same for `:8080`, or `address already in use` | Something else is already using that port, for example a local Postgres or another project's containers. | Stop the other program (`docker ps` lists other containers), or change the port in `.env`, for example `DB_PORT=5433` or `APP_PORT=8081`. If you change `APP_PORT`, open the app on that port instead. |
| Logging in as `taylor` says "Invalid username or password". | The demo data wasn't created. Either `SEED_DEMO_DATA=true` wasn't set the first time the database started, or the database already had a project. | Check that `.env` contains `SEED_DEMO_DATA=true`, then `docker compose down -v` and `docker compose up --build`. You can also just create your own account. |
| `The "SERVICE_FQDN_FRONTEND" variable is not set. Defaulting to a blank string.` | Coolify sets this variable when it deploys the app. It isn't needed locally. | Nothing to fix; it's only a warning. |
| "Sprint analysis isn't configured", "GitHub token not configured", or "Set the GitHub repository in Settings first" | The AI keys and the GitHub token aren't set yet (see `OPEN_ITEMS.md`). | Nothing to fix. If you have keys, add them to `.env` (see the Configuration section) and run `docker compose up -d` again. |
| The page still says "Engineering Workflow Manager" or looks like the old app. | You're on the wrong branch, or Docker is running an old image. | Check that `git branch --show-current` prints `staging`, run `docker compose up --build`, and hard-refresh the browser (`Cmd+Shift+R` on Mac, `Ctrl+Shift+R` on Windows). |
| An error mentioning `start_interval` | Your Docker is too old for the health-check settings in `docker-compose.yaml`. | Update Docker Desktop. |
| You're suddenly logged out, or your account is gone. | `docker compose down -v` deletes every local account and session along with the data. | Log in again, or register again. The demo users come back if `SEED_DEMO_DATA=true` is set. |
| `./smoke-test.sh: Permission denied`, or it won't run on Windows | The script isn't marked executable, or Windows has no bash. | Run `chmod +x smoke-test.sh`. On Windows, use Git Bash or WSL. The smoke test is optional. |
| Anything else | | Do a full reset: `docker compose down -v`, then `docker compose up --build`. If it still fails, share the output of `docker compose logs backend` with the team. |

## What's in it

- **Login.** Username and password with open sign-up. A new user sees nothing until a member adds them to a project.
- **Board.** Five status columns with drag and drop. The dashboard shows status counts, the selected sprint, burndown, velocity and the team.
- **Sprints.** Status comes from the dates: a future start date means *planned*. Several sprints can be active at once, and closing is manual.
- **Planning.** The backlog and every open sprint side by side. You can drag stories between them, bulk-move them, and carry over unfinished work from closed sprints.
- **Stories.** Titles are unique within a project, points use the Fibonacci scale, and subtasks are full stories. Every field can be edited from the story drawer, which also shows sprint history and carry-over count.
- **Dependencies.** Blockers are managed from the story drawer. The read-only graph uses React Flow and dagre. Duplicate and circular blocker links are rejected, and the app warns when a story is planned before its blocker.
- **Soft delete.** Nothing is ever deleted for good. Children are deleted and restored with their parent, through a Trash tab and a 10-second Undo.
- **GitHub links.** Each project records its repo URL, and each story records a branch. The story drawer shows the suggested branch name and the live PR status.
- **AI.** Sprint analysis uses the class LiteLLM proxy (`classroom-chat`); sprint review uses OpenAI `gpt-6-luna` through Responses with read-only GitHub tools (AI-7). Each feature requires its own backend key and an explicit model. Reports and review verdicts are advice and never change stories.
- **Discussion.** Each sprint has its own board, with one level of replies.

## High-level architecture

The application runs as three separate services. The frontend serves the React UI, the FastAPI backend owns
application logic and API access, and PostgreSQL persists application data.

```mermaid
flowchart LR
    user([Browser]) -->|HTTP| frontend[Frontend service<br/>React + Vite<br/>port 80]
    frontend -->|/api requests| backend[Backend service<br/>FastAPI + SQLAlchemy<br/>port 8000]
    backend -->|SQL| database[(Database service<br/>PostgreSQL 16<br/>port 5432)]

    classDef service fill:#eef6ff,stroke:#2563eb,stroke-width:1.5px,color:#111827
    classDef data fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#111827
    class frontend,backend service
    class database data
```

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

With Docker (closest to production), as in "Try it out" above:

```bash
cp .env.example .env                              # SEED_DEMO_DATA, APP_PORT, DB_PORT and optional AI keys
docker compose up --build                         # http://localhost:8080
./smoke-test.sh                                   # or: build, start and smoke-test in one go
```

`SEED_DEMO_DATA=true` seeds a demo project and four users, `taylor`, `jordan`, `casey` and `morgan`, all with
the password `devpassword`. Seeding only happens when the database has no projects. Never set it on staging or
production. To start from a clean database, run `docker compose down -v`.

Without Docker, for hot reload:

```bash
docker compose up -d db                           # Postgres on localhost:5432 (or DB_PORT from .env)
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
SEED_DEMO_DATA=true .venv/bin/uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

## Configuration

For Docker Compose, put these in the root `.env` (copy `.env.example`). For a directly launched backend, use `backend/.env.example`. Set production values separately in Coolify; your local `.env` is ignored by Git.

| Variable | Secret? | Purpose |
|---|---|---|
| `DATABASE_URL` | no | Set by `docker-compose.yaml` |
| `APP_TIMEZONE` | no | Decides "today" for sprint status and burndown (default `America/Denver`) |
| `SESSION_COOKIE_SECURE` | no | `false` on the class deploy, which is HTTP only |
| `SEED_DEMO_DATA` | no | Local development only |
| `ANALYSIS_LLM_BASE_URL`, `ANALYSIS_LLM_MODEL` | no | Empty by default; set the class LiteLLM URL and `classroom-chat` |
| `ANALYSIS_LLM_API_KEY` | yes | Required analysis-specific class proxy key |
| `REVIEW_LLM_BASE_URL`, `REVIEW_LLM_MODEL` | no | Empty by default; set model `gpt-6-luna`; an empty URL uses OpenAI directly |
| `REVIEW_LLM_API_KEY` | yes | Required review-specific OpenAI key |
| `ANALYSIS_LLM_REASONING_EFFORT`, `REVIEW_LLM_REASONING_EFFORT` | no | Backend defaults to `medium` / `high`; set analysis to `none` for `classroom-chat` |
| `ANALYSIS_LLM_MAX_OUTPUT_TOKENS`, `REVIEW_LLM_MAX_OUTPUT_TOKENS` | no | Per-request limits, default `4096` and `6000`, including reasoning tokens |
| `GITHUB_TOKEN` | yes | Fine-grained, read-only token for the project repo (Contents, Pull requests, Metadata: read) |

Provider URLs, model names and keys have no application or Compose defaults. Missing required settings return
a clear 503 and the rest of the app works. Remove the retired `OPENAI_API_KEY` from local and Coolify settings;
it cannot enable either feature. Reasoning and output-limit defaults live in `backend/app/config.py`, so blank
Compose or example-file values behave the same as a directly launched backend.

For the classroom `classroom-chat` proxy, set `ANALYSIS_LLM_REASONING_EFFORT=none` to omit the unsupported
reasoning parameter. Keep `ANALYSIS_LLM_API_KEY` set to the classroom key. This does not change the separate
`REVIEW_LLM_*` settings.

Set these non-secret values in your ignored `.env` or in Coolify, and obtain the two keys separately:

```dotenv
ANALYSIS_LLM_BASE_URL=http://ml-capstone.cs.byu.edu:4000/v1
ANALYSIS_LLM_MODEL=classroom-chat
ANALYSIS_LLM_REASONING_EFFORT=none
REVIEW_LLM_BASE_URL=
REVIEW_LLM_MODEL=gpt-6-luna
```

Set `ANALYSIS_LLM_API_KEY` to the classroom key and `REVIEW_LLM_API_KEY` to the team's OpenAI key. The proxy
is reachable only on campus or through the BYU VPN. Keys stay in the backend runtime, never in the browser or Git.
After changing local settings, run `docker compose up -d backend` to recreate the backend with those settings.
Staging and production have separate Coolify settings and must be verified after deployment.

### GitHub and AI acceptance checks

Use a disposable local project or an agreed staging test project. Local results do not close the staging
verification items in `OPEN_ITEMS.md`.

| Feature | Steps | Expected result |
|---|---|---|
| Repository and branches (GH-4, GH-6) | Save the project's GitHub URL in Settings; edit a story's branch or paste a same-repository `/tree/` URL | Repository and branch values are normalized; invalid and cross-repository URLs are rejected |
| Suggestions and PR status (GH-5 to GH-8) | Copy or use the suggested branch; reopen stories with known PRs | Suggestion uses the assignee's username; status shows open, merged, closed, branch without PR or missing branch; cache lasts five minutes |
| Analysis (AI-1 to AI-5) | Board → select a sprint → AI → Analysis → Run analysis | Completed report has eight sections and the supplied metrics; new runs preserve history |
| Final report and history | Edit and save as final; refresh; generate another report | Final report persists and the new draft is selected; the saved final stays in history |
| Sprint review (REPO-9) | Link real branches, then Sprint review → Run sprint review; expand story rows | Criteria, verdicts and commit-pinned evidence links appear; unlinked stories show No link; stories remain unchanged |
| Failure and sprint switching | Check missing configuration, Retry after a failed request, and switch sprints | Clear errors; retry preserves the failed record; reports and errors belong to the selected sprint |
| Automatic analysis (AI-2) | Close a disposable sprint while analysis is configured | History includes an On close report, unfinished work and no completion-date estimate |

Real AI runs can incur provider usage. Backend tests use fake services or the real SDK with mocked HTTP responses,
so they do not validate staging credentials, network access or real model output.

### Deployment acceptance recorded on 2026-10-26

Both existing branches were redeployed after configuring independent runtime keys. Coolify reported success and
both `/health` endpoints returned 200. Analysis uses the class proxy with `classroom-chat`, reasoning `none` and
4096 output tokens; review uses direct OpenAI `gpt-6-luna`, reasoning `high` and 6000 output tokens.

| Environment | Deployed commit | Live checks |
|---|---|---|
| Staging | `0cee914` | Fresh analysis and review complete; linked PR #8 and unchanged-result reuse verified |
| Production | `a18abcc` | Repository/branch normalization, merged PR #8, fresh analysis, code-backed Matches verdict with pinned evidence, reuse, Final/history persistence and automatic on-close analysis verified in a dedicated acceptance project |

The production project is **Deployment acceptance 2026-10-26**; its closed **Production integration acceptance**
sprint retains the test story and reports for inspection. Existing DinnerBell and ProjectManager stories were
not changed. These are functional checks, not a guarantee that every generated conclusion is correct.

`OPENAI_MODEL` was removed from both Coolify applications, including Preview copies. The legacy
`OPENAI_API_KEY` values are empty and cannot supply a fallback key. Coolify currently refuses to delete those
rows because the deployed Compose file still references the name. This review-cleanup PR removes the reference;
after its approved deployments to staging and production, delete the obsolete empty rows and repeat smoke checks.
The live commits above do not yet contain this PR's code changes.

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
