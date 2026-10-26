# Open items for the Initial-App build

Everything on this list is something the AI build of `Initial-App` couldn't finish alone. Each item says what's
needed from the team to close it. This is the single list of open items: §18 of `SPRINT_PLANNER_SPEC.md` points
here, so add new items to this file. Spec IDs are in brackets.

Last updated: 2026-10-24 (Eason local verification; online items not revalidated)

**Eason branch update, 2026-10-23:** the user selected direct OpenAI `gpt-6-luna` for both AI features. The branch now accepts one backend-only `OPENAI_API_KEY`, plus optional separate provider keys. This is an implementation override for `eason`; the historical team decisions below still need team review. Do not remove `OPENAI_API_KEY` when deploying this branch. See `AI_SETUP_TESTING.md` for current configuration and verification. The class proxy settings below are only needed if the team switches back to that route.

## 1. Before the first deploy to staging

- [ ] **Approve committing the build and opening the PR**
  - **State:** Eason's local changes are committed on `eason`; push and PR are pending. See `LOCAL_VERIFICATION.md`.
  - **Needed:** a go-ahead to commit and open a PR into `staging`, then one teammate's approval on it (D-4).

- [ ] **Wipe the staging database** (MIG-3) · Johnny
  - **Historical scope:** original Initial-App migration task, not a requirement of these Eason changes. This branch has no schema changes; verify the current deployed state before acting on this old item.
  - **Why:** the new schema is created from scratch by Alembic and can't migrate over the base app's tables, so the first deploy fails until the old tables are gone.
  - **Needed:** in the Coolify terminal on the staging `db` container, run
    `psql -U appuser -d appdb -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`
    right before `Initial-App` is merged to `staging`.

- [ ] **Update the environment variables in Coolify** (OPS-3) · Johnny
  - **Needed:** in both the staging and production apps:
    - **Add** `APP_TIMEZONE=America/Denver` and `SESSION_COOKIE_SECURE=false`.
    - **Remove** the old `OPENAI_MODEL` and `DEFAULT_USER_ID`. On `eason`, **keep/set** `OPENAI_API_KEY` for the direct OpenAI route.
    - **Don't set** `SEED_DEMO_DATA`.

- [ ] **Set up branch protection** on `staging` and `main` (TEST-5)
  - **Needed:** someone with admin rights requires one approving review and a passing `test` check on both branches. Alternatively, tell me it's OK to do this with the `gh` CLI.

## 2. AI and GitHub integration

- [x] **Local OpenAI configuration** (AI-7) · Eason
  - Direct OpenAI `gpt-6-luna` is verified for both features: Analysis `medium`, Review `high`, using the backend-only shared key. The class proxy remains an optional alternative.
- [x] **Local GitHub access and repository URL** (REPO-4, GH-4, GH-8) · Eason
  - The supplied local token queried `byu-ml-capstone/dinnerbell-product-manager`. The repository and real branches are saved in the local verification project. No token is stored in Git.
- [x] **Real-service verification**
  - Three analysis samples, merged/deleted-branch PR lookup, branch without PR, missing branch, code-backed and missing-feature verdicts, no-link handling, unchanged-result reuse and close-trigger analysis are verified. See `LOCAL_VERIFICATION.md` for results, boundaries and frontend steps.
- [ ] **Online configuration and verification** · deployment owner
  - Set the API keys, model/effort settings and GitHub token in Coolify; configure the online project's repository and branches, then repeat frontend checks after staging deploy. Local `.env` is not uploaded by Git. Online work is outside the completed local scope.

## 3. Decisions to confirm

- [ ] **Review the build's changes to the spec**
  - **Needed:** accept or reject each of these. They're already written into the spec (§17.1, plus §10.3, VEL-12 and MOVE-9) and marked as waiting for team review:
    1. A `usage` column on `sprint_analyses` to record token use (NFR-4). The §10 data model table didn't include it.
    2. A closed sprint's burndown and numbers show the moment it closed, so carrying stories out afterwards doesn't look like removed scope. Closed sprints get no completion estimate.
    3. Every sprint carries `capacity_warning`, so the warning shows in the sprint header as well as on Planning (MOVE-9).

- [ ] **GitHub usernames for CODEOWNERS** (TEST-8, D-8) · Johnny
  - **Needed:** the GitHub usernames for Johnny, Bella, Eason and Taft. I'll fill them in and turn on `.github/CODEOWNERS`.

- [ ] **Confirm the "Already agreed" items**
  - **Needed:** check off A-1 to A-14 in `SPRINT_PLANNER_DECISIONS.md`. The spec and the build treat them as decided, but none are checked.

- [ ] **Confirm Johnny's answers from drafting** (§17.2)
  - **Needed:** the team agrees with Q&A-1 to Q&A-7, or says what to change:
    - the app name;
    - open sign-up;
    - wiping the databases;
    - keeping story comments;
    - LiteLLM and Codex;
    - closing sprints by hand.

- [ ] **Unique titles include subtasks** (CORE-6) · Bella
  - **Needed:** confirm that two stories can't both have a subtask called "Write tests", or ask for titles to be unique only among top-level stories.

- [ ] **Deleting a sprint deletes its stories** (DEL-2) · Johnny
  - **Needed:** confirm this rule, which follows D-26 as written, or switch it so the sprint's stories move to the backlog instead.

- [ ] **Review the remaining "Proposed" answers in the spec**
  - **Needed:** accept or change each answer marked **Proposed** during the PR review. The build follows all of them.

## 4. Planning and process

- [ ] **Sprint dates for the roadmap** (§16)
  - **Needed:** the real start and end dates for Sprints 1 to 3. The spec's dates are a guess based on "about 10 days" (A-2).

- [ ] **"Staging is stable" checklist** (D-9, TEST-10)
  - **Needed:** the team agrees on what to check before the first `staging` → `main` merge. The spec proposes: CI is green, someone has clicked through login, board, planning and a sprint close on staging, and a backup is taken if there's a migration.

- [ ] **Production wipe and backups** (MIG-3, MIG-6, NFR-2) · Johnny
  - **Needed:**
    - Wipe the production database the same way as staging before the first merge to `main`.
    - After that, take a `pg_dump` before every production migration, plus weekly.

- [ ] **Smoke-test account** (TEST-7, optional)
  - **Needed:** a dedicated account on staging and production. Its credentials go in `SMOKE_USERNAME` and `SMOKE_PASSWORD` so `./smoke-test.sh <url>` can also check that login works.

- [ ] **After the two semesters** (NFR-5)
  - **Needed:** a decision on whether the app keeps running, and whether the class Coolify will still host it.
