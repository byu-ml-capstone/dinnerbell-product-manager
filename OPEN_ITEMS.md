# Open items for the Initial-App build

Everything on this list is something the AI build of `Initial-App` couldn't finish alone. Each item says what's
needed from the team to close it. This is the single list of open items: §18 of `SPRINT_PLANNER_SPEC.md` points
here, so add new items to this file. Spec IDs are in brackets.

Last updated: 2026-10-26

## 1. Before the first deploy to staging

- [ ] **Approve committing the build and opening the PR**
  - **State:** all the work is uncommitted on `Initial-App`.
  - **Needed:** a go-ahead to commit and open a PR into `staging`, then one teammate's approval on it (D-4).

- [ ] **Wipe the staging database** (MIG-3) · Johnny
  - **Why:** the new schema is created from scratch by Alembic and can't migrate over the base app's tables, so the first deploy fails until the old tables are gone.
  - **Needed:** in the Coolify terminal on the staging `db` container, run
    `psql -U appuser -d appdb -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`
    right before `Initial-App` is merged to `staging`.

- [x] **Update the environment variables in Coolify** (OPS-3) · Johnny
  - **Done 2026-10-26** in both the staging and production apps:
    - **Added** `APP_TIMEZONE=America/Denver` and `SESSION_COOKIE_SECURE=false`.
    - **Removed** `OPENAI_MODEL` and `DEFAULT_USER_ID`, which are no longer used.
    - **Kept** `OPENAI_API_KEY` for now. Nothing reads it, but it holds our OpenAI token. When the sprint review is set up, move its value into `REVIEW_LLM_API_KEY` and then remove it.
    - `SEED_DEMO_DATA` isn't set.

- [ ] **Set up branch protection** on `staging` and `main` (TEST-5)
  - **Needed:** someone with admin rights requires one approving review and a passing `test` check on both branches. Alternatively, tell me it's OK to do this with the `gh` CLI.

## 2. To turn on the AI features

These features return a "not configured" message until the settings below are in Coolify. Everything else works without them.

- [x] **LiteLLM settings for sprint analysis** (AI-7) · Johnny
  - **Done 2026-10-26:** `ANALYSIS_LLM_BASE_URL=http://ml-capstone.cs.byu.edu:4000/v1` and `ANALYSIS_LLM_MODEL=classroom-chat`, with our LiteLLM key in `ANALYSIS_LLM_API_KEY`. They're set in Coolify for staging and production, and a sprint analysis ran on both.
  - The proxy has a private BYU address, so it's only reachable on the campus network or the BYU VPN. That includes running sprint analysis locally.

- [ ] **Codex model for the sprint review** (AI-7) · Eason
  - **Needed:**
    - The exact Codex model name, which goes into `REVIEW_LLM_MODEL`.
    - Whether we reach it through LiteLLM or directly at OpenAI:
      - **Through LiteLLM:** set `REVIEW_LLM_BASE_URL` to the proxy URL.
      - **Directly at OpenAI:** leave it empty and put our OpenAI token in `REVIEW_LLM_API_KEY`. The token is in Coolify as `OPENAI_API_KEY` for now.
    - Confirmation that the model supports tool calls through the Responses API. The proxy only offers `classroom-chat`, `classroom-autocomplete` and `classroom-transcribe`, and none of them has been checked for this yet.

- [ ] **Read-only GitHub token** (REPO-4, GH-8) · Eason
  - **Needed:** a fine-grained token for the DinnerBell repo with *Contents*, *Pull requests* and *Metadata* set to read-only. The `byu-ml-capstone` org may need to approve it. Store it as `GITHUB_TOKEN` in Coolify for staging and production.

- [ ] **Set the project's repo URL** (GH-4) · Eason
  - **Needed:** after the deploy, create the DinnerBell project and paste its GitHub repo URL into the Settings tab.

- [ ] **Check the AI against the real services**
  - **Why:** sprint analysis ran against the real LiteLLM proxy on 2026-10-26, but the sprint review and GitHub code have only been tested against fakes. They haven't run against the real Codex model or GitHub.
  - **Needed:** once the settings above are in place, run these from `backend/` with the real environment variables, and read the results in `backend/ai_eval_out/`:
    - `python -m scripts.ai_eval`, which runs the analysis prompt on three sample sprints.
    - `python -m scripts.ai_eval --review <sprint_id>` on a staging sprint that has linked branches.

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
