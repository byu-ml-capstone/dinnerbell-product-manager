# Sprint Planner Specification

> **Template for an AI assistant to fill in.** This spec covers how we turn the base app (commit `fc1a359`) into the shared sprint planner we'll use for our main project. The team makes the key decisions in `SPRINT_PLANNER_DECISIONS.md`. An AI assistant fills in this spec from those decisions, `ARCH_SYNTH.md` and the code, and the team reviews the result before building.

## How this document gets filled in

### Workflow

1. The team answers `SPRINT_PLANNER_DECISIONS.md` together.
2. Each area's owner has an AI assistant fill in their sections of this spec on their own branch, then opens a PR.
3. The team reviews the PR. Each **Proposed** answer is either accepted (and its box checked) or changed.
4. A section is **ready to build** when it has no unreviewed proposals, its data model and API tables are filled in, and it has acceptance criteria.

Section status values: `Not started` · `AI draft` · `In review` · `Decided` · `In progress` · `Done`

### Instructions for the AI assistant

- **Sources, from most to least authoritative:**
  1. `SPRINT_PLANNER_DECISIONS.md`: the team's decisions. Never contradict them.
  2. `ARCH_SYNTH.md`: the reasons behind the main features.
  3. The current code: how things work today.
- **Answer every question** in the sections you've been asked to fill in:
  - If a team decision settles it, write the answer, cite the decision ID, and check the box.
  - If no decision covers it, propose an answer with a one-sentence reason, marked **Proposed**. Leave the box unchecked.
  - If it needs information you don't have (budget, class rules, team preferences), or every reasonable answer conflicts with a team decision, mark it **Needs team input**, say what's needed, and add it to §18.
- **Keep IDs stable.** Don't renumber, reword or delete questions, and keep the listed options. If a question doesn't apply, write `N/A` and why. Add new questions at the end of their section with the next free ID.
- **Fill in the tables and lists** under each section (requirements, data model, API, UI, acceptance criteria, risks) so they match the answers. Acceptance criteria must be testable. API paths follow the existing `/api/...` style.
- **Check the "Starting point" notes** against the current code and correct anything that has changed. Don't edit them otherwise.
- **Keep sections consistent.** When an answer depends on another section, cite that question's ID. Questions that span features are in §14.
- **Log team decisions** that change direction or affect several sections in §17.
- **Only edit the sections you were asked to fill in**, plus §17 and §18.

Question format, before and after filling in:

```markdown
- [ ] **ID** The question
  - Options: choices we already know about (not exhaustive)
  - Decision:

- [x] **ID** A question settled by a team decision
  - Options: ...
  - Decision: <answer> (D-21)

- [ ] **ID** A question with no team decision yet
  - Options: ...
  - Decision: **Proposed:** <answer>. Reason: <one sentence>

- [ ] **ID** A question the AI can't answer
  - Options: ...
  - Decision: **Needs team input:** <what's needed> (see §18)
```

---

## 1. Document info

| Field | Value |
|---|---|
| Spec owner | |
| Repo | |
| Staging URL | |
| Production URL | |
| Base commit | `fc1a359` |
| Last updated | |

| Team member | Role | Areas owned |
|---|---|---|
| | | |
| | | |
| | | |
| | | |

---

## 2. Product overview

### 2.1 Purpose

_In two or three sentences: what problem does the planner solve for us?_

### 2.2 Users

- [ ] **PROD-1** Who will use the app?
  - Options: only our team · other capstone teams · instructors/TAs (read-only?)
  - Decision:
- [ ] **PROD-2** How many projects will we track in it?
  - Options: only our main project · several projects
  - Decision:
- [ ] **PROD-3** Does anyone outside the team need to see our progress? If so, how (shared login, read-only link, exported reports)?
  - Decision:

### 2.3 Goals

- Semester 1:
- Semester 2:

### 2.4 Non-goals

_What are we deliberately not building?_

-

### 2.5 Success measures

- [ ] **PROD-4** How will we know the planner is working for us by the end of semester 1?
  - Decision:

---

## 3. Scope and priorities

| ID | Area | Section | Priority (Must / Should / Could / Won't) | Target sprint |
|---|---|---|---|---|
| FND | Foundations | §5 | | |
| F0 | Core workflow model | §6 | | |
| F1 | Soft delete and restore | §7 | | |
| F2 | Dependency graph | §8 | | |
| F3 | GitHub links | §9 | | |
| F4 | AI sprint analysis and code review | §10 | | |
| F5 | Moving stories and sprint planning | §11 | | |
| F6 | Velocity and metrics | §12 | | |
| F7 | Discussion | §13 | | |

- [ ] **SCOPE-1** What's the minimum we need working before we start using the planner for our main project?
  - Decision:
- [ ] **SCOPE-2** Do we track the work on the planner itself in the planner, or somewhere else until it's ready?
  - Decision:

---

## 4. Base app: keep, change, replace or remove

Fill in the decision column for each part of the base app. This table also feeds section 3 of `ARCH_SYNTH.md` (Preserve / Replace / Simplify).

| Component | Where | Today | Keep / Change / Replace / Remove | Notes |
|---|---|---|---|---|
| Backend framework | `backend/app/main.py` | FastAPI; every route in one file | | |
| Data model | `backend/app/models.py` | SQLAlchemy 2: users, projects, members, sprints, stories, dependencies, comments, sprint reports | | |
| Schema management | `on_startup` in `main.py` | `Base.metadata.create_all` on every start | | |
| Authentication | `backend/app/auth.py` | Trusts an `X-User-Id` header; falls back to `DEFAULT_USER_ID` | | |
| Seed data | `backend/app/seed.py` | Four fake users and a demo project | | |
| AI reports | `backend/app/ai.py` | OpenAI Responses API; closed sprints only | | |
| Frontend structure | `frontend/src/main.jsx` | One 675-line file, one page, no router | | |
| API client | `frontend/src/api.js` | Small `fetch` wrapper; user ID kept in `localStorage` | | |
| Board drag and drop | `main.jsx` | `@dnd-kit/core` | | |
| Styling | `frontend/src/styles.css` | Hand-written CSS | | |
| Icons | `main.jsx` | `lucide-react` | | |
| Frontend serving | `frontend/nginx.conf` | nginx serves the build and proxies `/api` and `/health` to the backend | | |
| CI | `.github/workflows/ci.yml` | Runs `backend/ci_check.py` and `npm run build` | | |
| Deploy | `docker-compose.yaml`, Coolify | Push to `staging` / `main` triggers Coolify webhooks | | |
| Infrastructure | `terraform/` | Creates the Coolify project, environments, apps and GitHub secrets | | |
| Smoke test | `smoke-test.sh` | Starts the stack (or targets a URL) and creates a test project | | |
| Docs | `README.md` | Still describes the class hello-world template | | |

---

## 5. Foundations

Cross-cutting work that most features depend on.

**Status:** Not started · **Owner:**

### 5.1 Database migrations

**Starting point**

- The schema is built by `create_all` at startup. It creates missing tables but never adds or changes columns on tables that already exist.
- Staging and production databases already exist on Coolify volumes.

**Questions**

- [ ] **MIG-1** Which migration tool do we use?
  - Options: Alembic · numbered SQL files applied at startup (like the class hello-world template)
  - Decision:
- [ ] **MIG-2** Do migrations run automatically when the container starts, or as a separate deploy step?
  - Decision:
- [ ] **MIG-3** What do we do with existing staging and production data?
  - Options: baseline it with an initial migration · wipe and start fresh
  - Decision:
- [ ] **MIG-4** What are the rules for migrations in PRs (who reviews them, is a downgrade required)?
  - Decision:
- [ ] **MIG-5** How do we test a migration before it reaches production?
  - Decision:
- [ ] **MIG-6** Do we back up the production database before migrating? How, and who does it?
  - Decision:

**Changes**

-

**Acceptance criteria**

- [ ]

### 5.2 Authentication and accounts

**Starting point**

- There's no login. The frontend sends `X-User-Id` from a dropdown and the backend trusts it.
- Users only come from `seed.py`.
- `GET /api/users` lists every user without authentication.

**Questions**

- [ ] **AUTH-1** How do people log in?
  - Options: GitHub OAuth · university SSO · email and password · keep the user picker for now
  - Decision:
- [ ] **AUTH-2** How are accounts created?
  - Options: self sign-up · invite from a project owner · allow-list of emails or GitHub usernames
  - Decision:
- [ ] **AUTH-3** Session cookies or tokens? How long does a session last?
  - Decision:
- [ ] **AUTH-4** How do we log in during local development and in automated tests?
  - Decision:
- [ ] **AUTH-5** What happens to the seeded fake users and the `DEFAULT_USER_ID` fallback?
  - Decision:
- [ ] **AUTH-6** If we use GitHub OAuth, could each user's GitHub token also be used for the AI code review, or does the server use its own read-only token? (see REPO-4)
  - Decision:

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**Acceptance criteria**

- [ ]

### 5.3 Roles and permissions

**Starting point**

- `ProjectMember.role` exists (`owner` or `member`), but no endpoint checks it. Any project member can do anything.

**Questions**

- [ ] **PERM-1** Which roles do we need?
  - Options: owner · member · viewer
  - Decision:
- [ ] **PERM-2** Fill in the permission matrix below.
  - Decision: see table
- [ ] **PERM-3** Can members be removed from a project? What happens to stories assigned to them?
  - Decision:

| Action | Owner | Member | Viewer |
|---|---|---|---|
| Create and edit stories | | | |
| Delete stories | | | |
| Restore deleted items | | | |
| Permanently delete items | | | |
| Create, start and close sprints | | | |
| Move stories between sprints | | | |
| Add and remove dependencies | | | |
| Generate AI analysis | | | |
| Edit and finalize reports | | | |
| Comment | | | |
| Manage members | | | |
| Set the project's GitHub repository | | | |
| Run AI code review | | | |
| Delete the project | | | |

### 5.4 Frontend architecture and UI design

**Starting point**

- All of the UI is in `frontend/src/main.jsx`: one page with a dashboard, the board, a story drawer and the report panel.
- There's no router, and every change reloads the whole project (`loadProject`).
- TypeScript is installed, but the code is plain JSX.
- There are no frontend tests.
- Stories have no edit form after creation, and acceptance criteria and due dates can't be entered from the UI.
- `ARCH_SYNTH.md` §1 names UI as our biggest gap.

**Questions**

- [ ] **UI-1** Which views do we need?
  - Options to confirm: Board · Backlog / Planning · Dependency graph · Insights (velocity, burndown) · Story detail · Reports / AI · Discussion · Trash · Project settings (members, GitHub)
  - Decision:
- [ ] **UI-2** Which routing library?
  - Options: React Router · TanStack Router
  - Decision:
- [ ] **UI-3** How do we fetch and cache data?
  - Options: TanStack Query · keep hand-written fetching
  - Decision:
- [ ] **UI-4** Do we adopt a component library or design system?
  - Options: shadcn/ui · Mantine · MUI · keep custom CSS
  - Decision:
- [ ] **UI-5** Do we move the frontend to TypeScript?
  - Decision:
- [ ] **UI-6** Do we design screens before building them (wireframes, Figma)? Who signs off?
  - Decision:
- [ ] **UI-7** Where does story detail live?
  - Options: side drawer · modal · its own page with a shareable URL
  - Decision:
- [ ] **UI-8** Does it need to work on phones? Dark mode? What accessibility level do we aim for (keyboard drag and drop, contrast)?
  - Decision:
- [ ] **UI-9** How do we show errors, loading states and empty states consistently?
  - Decision:
- [ ] **UI-10** What folder structure and naming conventions do we use for the frontend?
  - Decision:

**Views**

| View | Purpose | Main components | Feature(s) |
|---|---|---|---|
| | | | |

**Acceptance criteria**

- [ ]

### 5.5 Testing and CI

**Starting point**

- CI runs `backend/ci_check.py` (health check and creating a project) and `npm run build`.
- `backend/tests/test_api_smoke.py` exists, but CI never runs pytest.
- Tests use SQLite; production uses Postgres.
- There are no frontend tests.
- `smoke-test.sh` creates a new project on whatever URL it targets, including production, and assumes no login is needed.

**Questions**

- [ ] **TEST-1** Do we run pytest in CI against a Postgres service container instead of SQLite?
  - Decision:
- [ ] **TEST-2** What tests must every feature PR include?
  - Options: API tests for each new endpoint · migration test · UI tests
  - Decision:
- [ ] **TEST-3** How do we test the frontend?
  - Options: Vitest + Testing Library · Playwright end to end · none for now
  - Decision:
- [ ] **TEST-4** How do we test the AI and GitHub features in CI without real keys?
  - Options: mocks · recorded responses
  - Decision:
- [ ] **TEST-5** Branch protection: which reviews and CI checks are required before merging into `staging` and `main`?
  - Decision:
- [ ] **TEST-6** Do we add linting and formatting (ruff, ESLint, Prettier), and is it enforced in CI?
  - Decision:
- [ ] **TEST-7** How should `smoke-test.sh` work once login and soft delete exist? Should it still create data on production?
  - Decision:

**Acceptance criteria**

- [ ]

### 5.6 Deployment, environments and configuration

**Starting point**

- Pushing to `staging` deploys staging, and pushing to `main` deploys production, through Coolify webhooks.
- The deployed hostname comes from the repository name.
- The README describes deployed apps as HTTP only and reached over the VPN.
- The only secret today is `OPENAI_API_KEY`, passed through `docker-compose.yaml`.

**Questions**

- [ ] **OPS-1** Do we rename the app and/or the repo? Renaming the repo changes the deployed hostname.
  - Decision:
- [ ] **OPS-2** Can the deployed backend make outbound requests to `api.github.com` and the AI provider's API?
  - Decision:
- [ ] **OPS-3** Which new secrets will we need (read-only GitHub token, session secret, AI key), and who manages them in Coolify?
  - Decision:
- [ ] **OPS-4** Does staging get its own GitHub and AI credentials, or share production's?
  - Decision:
- [ ] **OPS-5** What data does staging have?
  - Options: seed data · copy of production · its own data
  - Decision:
- [ ] **OPS-6** Do we keep using `terraform/`, or manage Coolify by hand?
  - Decision:
- [ ] **OPS-7** How do we find out when something breaks in production (logs, alerts, health checks)?
  - Decision:

### 5.7 Known issues inherited from the base app

For each issue, decide whether to fix it now, fix it as part of a feature, or accept it.

| ID | Issue | Where | Related | Decision | Fix in |
|---|---|---|---|---|---|
| BUG-1 | The board query includes unassigned backlog stories from *other* projects | `get_board` in `main.py` | | | |
| BUG-2 | Stories in a closed sprint can't be edited or moved, so unfinished work is stuck there | `ensure_story_editable` in `main.py` | F5 | | |
| BUG-3 | Adding a blocker always sets the blocked story to `blocked`, even if the blocker is already done | `create_dependency` in `main.py` | F2 | | |
| BUG-4 | `blocked` is never cleared automatically. A blocked story can't change status until its blocker links are deleted, even when every blocker is done | `update_story`, `delete_dependency` in `main.py` | F2 | | |
| BUG-5 | Adding the same dependency twice returns a 500 error (unique constraint) | `create_dependency` in `main.py` | F2 | | |
| BUG-6 | Nothing prevents dependency cycles (A blocks B, B blocks A) | `create_dependency` in `main.py` | F2 | | |
| BUG-7 | `PUT /sprints/{id}/stories/{id}` doesn't check the `sprint_id` in the request body, so a story can be moved into a closed sprint or another project's sprint | `assign_story_to_sprint` in `main.py` | F5 | | |
| BUG-8 | Moving a parent story doesn't move its subtasks | `update_story` in `main.py` | F5 | | |
| BUG-9 | Sprints created from the UI are always `active`, which fails if one is already active. Planned sprints can't be created from the UI | `SprintForm` in `main.jsx` | F5 | | |
| BUG-10 | Velocity mixes units: total points, or the number of done stories when none have points | `close_sprint` in `main.py` | F6 | | |
| BUG-11 | Velocity bars are `velocity * 14px` wide and overflow for normal values | `Dashboard` in `main.jsx` | F6 | | |
| BUG-12 | Regenerating an AI draft erases the saved final report | `draft_report` in `main.py` | F4 | | |
| BUG-13 | The AI prompt identifies people and stories by ID (`user-002`) instead of name | `_story_line` in `ai.py` | F4 | | |
| BUG-14 | `GET /api/users` lists every user without authentication | `list_users` in `main.py` | 5.2 | | |
| BUG-15 | `@app.on_event("startup")` is deprecated in FastAPI | `main.py` | 5.1 | | |
| BUG-16 | The README describes the hello-world template, not this app | `README.md` | 5.6 | | |

---

## 6. F0: Core workflow model

The basic rules every other feature builds on.

**Status:** Not started · **Owner:**

**Starting point**

- Story statuses: `backlog`, `selected`, `in_progress`, `blocked`, `done`.
- Priorities: `low`, `medium`, `high`, `urgent`.
- Sprint statuses: `planned`, `active`, `closed`. Only one sprint per project can be active.
- Subtasks are stories with a `parent_story_id`.
- Story IDs are random (`story-3f9a1c2b7d`).
- Story points can be any whole number of 1 or more.
- The backlog has no ordering field; stories are listed newest first.

**Questions**

- [ ] **CORE-1** Which statuses (board columns) do we want? Do we need a `review` status, e.g. while a PR is open?
  - Decision:
- [ ] **CORE-2** Is `blocked` a status someone sets, or a flag worked out from unfinished blockers? (see DEP-1)
  - Decision:
- [ ] **CORE-3** Do we need story types?
  - Options: feature · bug · chore · spike
  - Decision:
- [ ] **CORE-4** Do subtasks stay as full stories with a parent, or become a lighter checklist? Do they have their own points, assignee and status?
  - Decision:
- [ ] **CORE-5** Which point scale do we use? Can unpointed stories go into a sprint?
  - Options: Fibonacci (1, 2, 3, 5, 8, 13) · any whole number · t-shirt sizes
  - Decision:
- [ ] **CORE-6** Do we want short, readable story keys (e.g. `SP-42`)? These matter for suggested branch names (GH-6).
  - Decision:
- [ ] **CORE-7** How long are sprints? Are start and end dates required?
  - Decision:
- [ ] **CORE-8** Do we keep the one-active-sprint-per-project rule?
  - Decision:
- [ ] **CORE-9** What's our definition of done for a story?
  - Decision:
- [ ] **CORE-10** Which story fields can be edited after creation, and by whom? Are stories in closed sprints still locked?
  - Decision:
- [ ] **CORE-11** Do we need a backlog order (rank) separate from priority?
  - Decision:
- [ ] **CORE-12** Do we want limits on how many stories can be in a column at once (WIP limits)?
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| CORE-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 7. F1: Soft delete and restore

**Goal** (`ARCH_SYNTH.md` decision 1): projects, sprints and stories can be deleted without losing them for good.

**Status:** Not started · **Owner:**

**Starting point**

- There are no delete endpoints for projects, sprints, stories or comments. Only dependency links can be deleted, and that's permanent.
- The relationships use `cascade="all, delete-orphan"` (`models.py`), so a real delete of a project would also remove all of its sprints and stories.

**Questions**

- [ ] **DEL-1** Which things can be deleted and restored?
  - Options: projects · sprints · stories · subtasks · comments · dependency links · reports
  - Decision:
- [ ] **DEL-2** When a sprint is deleted, what happens to its stories?
  - Options: move to the backlog · delete them with the sprint · refuse while the sprint has stories
  - Decision:
- [ ] **DEL-3** Can a closed sprint be deleted? If so, does its velocity disappear from history?
  - Decision:
- [ ] **DEL-4** When a story is deleted, do its subtasks, comments and dependency links go with it and come back together on restore?
  - Decision:
- [ ] **DEL-5** Does a deleted story still block other stories?
  - Decision:
- [ ] **DEL-6** If a story is restored after its sprint was deleted or closed, where does it go?
  - Decision:
- [ ] **DEL-7** Is there permanent deletion?
  - Options: automatic after N days · manual only · never
  - Decision:
- [ ] **DEL-8** Where do people find deleted items?
  - Options: a Trash view per project · a "show deleted" filter on each list
  - Decision:
- [ ] **DEL-9** Do we keep an audit log of deletes and restores, or just `deleted_at` / `deleted_by` on each row?
  - Decision:
- [ ] **DEL-10** How do we make sure every query leaves out deleted rows?
  - Options: one global SQLAlchemy filter (`with_loader_criteria`) · explicit filters in each query · database views
  - Decision:
- [ ] **DEL-11** Do we want an immediate "undo" after deleting, as well as Trash?
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| DEL-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 8. F2: Dependency graph

**Goal** (`ARCH_SYNTH.md` decision 2): see which stories have to be done before others, as a graph, so we don't get stuck.

**Status:** Not started · **Owner:**

**Starting point**

- The `dependencies` table links a blocker story to a blocked story, with an optional reason. Each pair can only be linked once.
- Blockers are added and removed from the story drawer. There's no graph view.
- `GET /api/projects/{id}/stories` returns each story's `blocked_by` IDs.
- Related known issues: BUG-3, BUG-4, BUG-5, BUG-6.

**Questions**

- [ ] **DEP-1** Is a story blocked whenever any of its blockers isn't done (worked out automatically), or only when someone marks it? What happens when the last blocker is done?
  - Decision:
- [ ] **DEP-2** Do we need link types other than "blocks"?
  - Options: relates to · duplicates · part of
  - Decision:
- [ ] **DEP-3** Can dependencies cross projects? (Today they can't.)
  - Decision:
- [ ] **DEP-4** What does the graph show by default?
  - Options: whole project · current sprint · one story's upstream and downstream
  - Decision:
- [ ] **DEP-5** Are subtasks their own nodes, or rolled into their parent?
  - Decision:
- [ ] **DEP-6** What do colors and shapes mean (status, sprint, assignee)? How are done stories shown (hidden, faded)?
  - Decision:
- [ ] **DEP-7** Can dependencies be added and removed by drawing on the graph, or only from story detail?
  - Decision:
- [ ] **DEP-8** Do we warn when a story is planned in an earlier sprint than one of its blockers? Warn, or prevent it?
  - Decision:
- [ ] **DEP-9** Do we highlight the critical path (the longest chain of unfinished work)?
  - Decision:
- [ ] **DEP-10** Which graph library and layout do we use?
  - Options: React Flow with dagre or ELK · Cytoscape.js · D3
  - Decision:
- [ ] **DEP-11** How many nodes before the graph needs filtering or grouping?
  - Decision:
- [ ] **DEP-12** Is a reason required when adding a dependency?
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| DEP-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 9. F3: GitHub links

**Goal** (`ARCH_SYNTH.md` decision 3): every sprint and story can point to the GitHub branch, pull request or issue it belongs to, so we always know what each branch is for. The links are also how the AI code review (§10.2) finds the code.

**Status:** Not started · **Owner:**

**Starting point**

- Nothing exists: sprints and stories have no link fields. The `GitPullRequest` icon in the UI is only used as a "blocked" badge.

**Questions**

- [ ] **GH-1** Which kinds of links can be added?
  - Options: branch · pull request · issue · commit · any URL
  - Decision:
- [ ] **GH-2** Can a story have more than one link (e.g. a branch and its PR, or several PRs)?
  - Decision:
- [ ] **GH-3** Do sprints get their own links (e.g. a milestone or tracking issue), or only stories?
  - Decision:
- [ ] **GH-4** Does each project record its GitHub repository? Are links checked to make sure they point at that repo?
  - Decision:
- [ ] **GH-5** Branches are usually deleted after their PR is merged, which breaks a branch link. Do we ask people to link the PR, or does the app look up the PR for a linked branch?
  - Decision:
- [ ] **GH-6** Do we suggest a branch name for each story (e.g. `story/SP-42-short-title`) with a copy button?
  - Decision:
- [ ] **GH-7** Where do links appear?
  - Options: story card · story detail · sprint header · planning view
  - Decision:
- [ ] **GH-8** Do we show live details for a link (PR open, merged or closed), or only the URL? Live details need the GitHub token from REPO-4.
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| GH-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 10. F4: AI sprint analysis and code review

**Goal** (`ARCH_SYNTH.md` decision 4): more than a completion percentage. Guidance during a sprint on what's needed next, and a check of what's actually in the code against what the sprint says has been done.

**Status:** Not started · **Owner:**

**Starting point**

- `POST /api/sprints/{id}/report/draft` sends sprint details and one line per story to OpenAI (default model `gpt-5-mini`) and returns Markdown with five fixed sections.
- It only works for closed sprints. Each sprint can have only one report (`sprint_reports.sprint_id` is unique).
- The flow is: generate a draft, edit it, save it as final.
- The AI call runs inside the HTTP request, with no timeout or retry handling.
- The AI never sees any code.
- Related known issues: BUG-12, BUG-13.

### 10.1 Sprint analysis

- [ ] **AI-1** Which kinds of analysis do we want?
  - Options: mid-sprint progress check · end-of-sprint retrospective · sprint planning suggestions · help with a single story
  - Decision:
- [ ] **AI-2** When does it run?
  - Options: on demand at any time · on a schedule (e.g. daily) · when something changes
  - Decision:
- [ ] **AI-3** Do we keep every analysis for a sprint? Should earlier ones be easy to compare?
  - Decision:
- [ ] **AI-4** What data goes into the prompt? Check each one we include:
  - [ ] Story titles, statuses, points and assignees (by name)
  - [ ] Descriptions and acceptance criteria
  - [ ] Dependency chains and what's currently blocked
  - [ ] Days elapsed and remaining, points remaining
  - [ ] Stories with no recent updates
  - [ ] Recent comments and discussion
  - [ ] Code review results (§10.2)
  - [ ] Velocity from past sprints
  - [ ] Earlier analyses for the same sprint
  - [ ] Extra context typed in by the team
  - Decision:
- [ ] **AI-5** Which sections and format should the output have? Is there a length limit?
  - Decision:
- [ ] **AI-6** Can it recommend actions (reassign, split a story, move to the next sprint)? Can it carry them out after someone confirms?
  - Decision:
- [ ] **AI-7** Which AI provider and model do we use? Who supplies the API key, and what's our budget?
  - Decision:
- [ ] **AI-8** Is it OK to send our project data, comments and source code to an outside AI provider? Are there class rules about this?
  - Decision:
- [ ] **AI-9** How do we keep it from making things up?
  - Options: keep the "use only the supplied data" instruction · show the data it was given · require a person to review before saving
  - Decision:
- [ ] **AI-10** Who can edit and finalize a report? Can a finalized report be regenerated?
  - Decision:
- [ ] **AI-11** What happens when the AI call fails or is slow?
  - Options: timeout and show an error · retry · run as a background job
  - Decision:
- [ ] **AI-12** How do we test changes to the prompt (e.g. fixed sample sprints, comparing outputs)?
  - Decision:

### 10.2 Code review against linked GitHub work

**How it could work** (background for the questions below, not decisions)

- The backend splits each link (§9) into owner, repo and branch, PR or issue number, then reads the code through the GitHub API. It never fetches the pasted URL itself.
- A PR's changed files and diffs stay available after its branch is deleted. A branch link only works until the branch is deleted.
- An issue gives the description and discussion of the work, but no code unless it has linked PRs.
- Commits to `staging` between the sprint's start and end dates show work that was merged without being linked to any story.
- The AI gets each story's title, acceptance criteria and claimed status next to its code, and reports whether the code supports the claim.

**Questions**

- [ ] **REPO-1** What should the review check? Check each one we want:
  - [ ] Stories marked done have code that matches them
  - [ ] Each acceptance criterion has evidence in the code or tests
  - [ ] Stories in progress have recent commits
  - [ ] Work merged during the sprint that isn't linked to any story
  - [ ] Changes come with tests
  - Decision:
- [ ] **REPO-2** How much of the code does the AI see?
  - Options: only the linked PR's diff · the diff plus the full changed files · the AI explores the repo itself with read-only tools (list, read and search files) · the server clones the repo
  - Decision:
- [ ] **REPO-3** What is each story's code compared against?
  - Options: the linked PR's diff · the linked branch compared with `staging` · commits to `staging` between the sprint's start and end dates
  - Decision:
- [ ] **REPO-4** How does the backend read the repo? Is the repo private?
  - Options: fine-grained read-only token stored on the server · GitHub App · each user's own token
  - Decision:
- [ ] **REPO-5** Which files are never sent to the AI?
  - Options: lockfiles · generated and build output · binaries and images · `.env` and other secret-looking files
  - Decision:
- [ ] **REPO-6** What's the size limit per story, and what happens to a diff that's too big (cut off, summarize file by file, skip)?
  - Decision:
- [ ] **REPO-7** Do we review one story at a time and then summarize the sprint, or send the whole sprint in one call?
  - Decision:
- [ ] **REPO-8** What verdicts can a story get, and how is each shown? Must every claim point to a file, line or commit? Fill in the table below.
  - Decision: see table
- [ ] **REPO-9** If a story's code hasn't changed since its last review (same commit), do we reuse the old result?
  - Decision:
- [ ] **REPO-10** A review could take a minute or more. Does it run in the background, with progress shown?
  - Decision:
- [ ] **REPO-11** Is the verdict only advice, or can it change anything (flag a story, suggest a status change, block closing a sprint)?
  - Decision:
- [ ] **REPO-12** Code comments and issue text could contain instructions aimed at the AI. How do we make sure repo content is treated as data only?
  - Decision:
- [ ] **REPO-13** Do stories need acceptance criteria before they can be reviewed? Vague criteria give vague verdicts.
  - Decision:
- [ ] **REPO-14** How do we test it (e.g. sample stories with known diffs: one complete, one partial, one with no matching code; recorded GitHub responses)?
  - Decision:
- [ ] **REPO-15** Cost limits: who can start a review, and how many stories or tokens can one review use?
  - Decision:

| Verdict | Meaning | How it's shown |
|---|---|---|
| Matches | | |
| Partial | | |
| No evidence found | | |
| No link | | |
| Can't tell | | |

### 10.3 Specification

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| AI-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 11. F5: Moving stories and sprint planning

**Goal** (`ARCH_SYNTH.md` decision 5): stories can move to later or earlier sprints as plans change.

**Status:** Not started · **Owner:**

**Starting point**

- A story's sprint can be changed through `PUT /api/stories/{id}` (`sprint_id`) or `PUT /api/sprints/{id}/stories/{id}`.
- Drag and drop on the board only moves stories between the selected sprint and the backlog. No view shows several sprints at once.
- Closing a sprint leaves unfinished stories in it, where they can't be edited (BUG-2).
- Related known issues: BUG-2, BUG-7, BUG-8, BUG-9.

**Questions**

- [ ] **MOVE-1** When a sprint closes, what happens to unfinished stories?
  - Options: ask for each story · all move to the next sprint · all move to the backlog · they stay in the closed sprint
  - Decision:
- [ ] **MOVE-2** Can a story be moved out of a closed sprint later?
  - Decision:
- [ ] **MOVE-3** Can a story be added to the active sprint partway through? Does that count as a scope change in metrics?
  - Decision:
- [ ] **MOVE-4** How many future sprints can be planned at once?
  - Decision:
- [ ] **MOVE-5** What does the planning view look like?
  - Options: backlog and sprints side by side with drag and drop · one list with a sprint dropdown per story
  - Decision:
- [ ] **MOVE-6** Do subtasks always move with their parent? Can a subtask be in a different sprint?
  - Decision:
- [ ] **MOVE-7** If a story moves earlier than one of its unfinished blockers, do we warn or prevent it? (see DEP-8)
  - Decision:
- [ ] **MOVE-8** Do we keep each story's sprint history (e.g. "carried over twice")? Where is it shown?
  - Decision:
- [ ] **MOVE-9** Do we warn when a sprint's planned points are higher than our recent velocity?
  - Decision:
- [ ] **MOVE-10** When a partly finished story moves to another sprint, does it keep its status or reset?
  - Decision:
- [ ] **MOVE-11** Do we keep both move endpoints, or merge them into one?
  - Decision:
- [ ] **MOVE-12** Can several stories be moved at once?
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| MOVE-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 12. F6: Velocity and metrics

**Goal** (`ARCH_SYNTH.md` §1): track velocity across sprints.

**Status:** Not started · **Owner:**

**Starting point**

- Velocity is calculated once, when a sprint closes, and stored on the sprint.
- The dashboard shows the last six closed sprints as simple bars.
- Nothing records what was committed at the start of a sprint or when statuses changed, so burndown, cycle time and scope changes can't be calculated.
- Related known issues: BUG-10, BUG-11.

**Questions**

- [ ] **VEL-1** What does velocity mean for us? What do unpointed stories count as?
  - Options: points completed · stories completed
  - Decision:
- [ ] **VEL-2** Do subtasks count on their own, or only through their parent?
  - Decision:
- [ ] **VEL-3** When a story is carried over, do its points count only in the sprint where it's finished?
  - Decision:
- [ ] **VEL-4** Do we track committed versus completed points? When is the commitment recorded (e.g. when the sprint starts)?
  - Decision:
- [ ] **VEL-5** Which charts do we want?
  - Options: velocity over time · burndown or burnup · cumulative flow · cycle time
  - Decision:
- [ ] **VEL-6** Do we record every status change in an event log? Burndown and cycle time need it.
  - Decision:
- [ ] **VEL-7** Do we show per-person metrics? If so, who can see them?
  - Decision:
- [ ] **VEL-8** How many past sprints go into averages and forecasts?
  - Decision:
- [ ] **VEL-9** If a story's points change during a sprint, which value counts?
  - Decision:
- [ ] **VEL-10** Can a closed sprint's velocity be recalculated (e.g. after a correction or a restore)?
  - Decision:
- [ ] **VEL-11** Which chart library do we use?
  - Options: Recharts · Chart.js · Nivo · hand-built SVG
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| VEL-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 13. F7: Discussion

**Goal** (`ARCH_SYNTH.md` §1): chat and discussion features.

**Status:** Not started · **Owner:**

**Starting point**

- Stories have flat comments. Comments can't be edited or deleted.
- There are no mentions, no notifications, and no discussion at the sprint or project level.

**Questions**

- [ ] **CHAT-1** Where can discussion happen?
  - Options: on a story · on a sprint · a project-wide channel
  - Decision:
- [ ] **CHAT-2** Threaded replies, or flat?
  - Decision:
- [ ] **CHAT-3** Can people edit and delete their own comments? Is edit history shown?
  - Decision:
- [ ] **CHAT-4** Do we support @mentions? How are people notified?
  - Options: in the app only · email · a chat tool we already use
  - Decision:
- [ ] **CHAT-5** Do new messages appear live, or on refresh / polling? How quickly do they need to show up?
  - Decision:
- [ ] **CHAT-6** Do we support Markdown, code blocks, and links to stories and PRs?
  - Decision:
- [ ] **CHAT-7** Do we support attachments or images?
  - Decision:
- [ ] **CHAT-8** Should system events (status changes, moves, GitHub activity) appear in the discussion feed?
  - Decision:
- [ ] **CHAT-9** Does this replace the chat tool we already use, or sit alongside it?
  - Decision:

**Requirements**

| ID | As a… | I want… | So that… |
|---|---|---|---|
| CHAT-R1 | | | |

**Data model changes**

| Table | Change | Migration / backfill notes |
|---|---|---|
| | | |

**API changes**

| Method | Path | New / Changed / Removed | Notes |
|---|---|---|---|
| | | | |

**UI changes**

-

**Acceptance criteria**

- [ ]

**Risks and open questions**

-

---

## 14. How the features affect each other

Questions that come up where two features meet.

- [ ] **X-1** Soft delete and metrics: does deleting a done story from a closed sprint change that sprint's velocity?
  - Decision:
- [ ] **X-2** Soft delete and dependencies: how does the graph show a deleted blocker? (see DEL-5)
  - Decision:
- [ ] **X-3** Soft delete and links: are a story's GitHub links and code reviews deleted and restored along with it?
  - Decision:
- [ ] **X-4** Soft delete and AI: are deleted items left out of analysis?
  - Decision:
- [ ] **X-5** Moving and metrics: how do stories added or removed mid-sprint show up in burndown and committed points?
  - Decision:
- [ ] **X-6** Moving and code review: when a story moves to another sprint, does its last code review go with it, or is it reviewed again?
  - Decision:
- [ ] **X-7** Status changes can come from people, dependency rules and possibly AI suggestions (REPO-11). Which takes priority, and are they all recorded in the same history?
  - Decision:
- [ ] **X-8** Discussion and AI: are comments sent to the AI? Can a comment be marked as not for the AI?
  - Decision:
- [ ] **X-9** Permissions: does every new endpoint check project membership and role? (see PERM-2)
  - Decision:

---

## 15. Non-functional requirements

- [ ] **NFR-1** How much data do we expect after two semesters (users, projects, stories per project)? Any speed targets (page load, drag and drop)?
  - Decision:
- [ ] **NFR-2** Backups and recovery: how often, stored where, and who checks that restoring works?
  - Decision:
- [ ] **NFR-3** Security: how do we handle secrets, token permissions and input validation? Who reviews security-sensitive changes?
  - Decision:
- [ ] **NFR-4** Cost limits: AI usage and any paid services.
  - Decision:
- [ ] **NFR-5** What happens to the app and its data after the two semesters end?
  - Decision:

---

## 16. Roadmap

- [ ] **PLAN-1** In what order do we build things? Which foundations must be in place before feature work starts?
  - Decision:
- [ ] **PLAN-2** How do we divide work so people aren't all editing the same files? (`main.py` and `main.jsx` are single files today.)
  - Decision:

| Sprint | Dates | Goal | Spec items (IDs) | Owner(s) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 17. Decision log

Record decisions that change direction, affect several features, or were hard to agree on.

| Date | Question ID | Decision | Decided by | Notes |
|---|---|---|---|---|
| | | | | |

---

## 18. Open items for the team

Questions marked **Needs team input**, and new questions that don't belong to a section yet.

| Question ID | What's needed | Who follows up |
|---|---|---|
| | | |

---

## 19. Glossary

Agree on these definitions so we all use the words the same way.

| Term | Definition |
|---|---|
| Story | |
| Subtask | |
| Blocker / dependency | |
| Backlog | |
| Sprint (planned, active, closed) | |
| Story points | |
| Velocity | |
| Committed points | |
| Carry-over | |
| Definition of done | |
| Soft delete, restore, purge | |
