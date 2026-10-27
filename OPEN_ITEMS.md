# Open items for the Initial-App build

Everything on this list is something the AI build of `Initial-App` couldn't finish alone. Each item says what's
needed from the team to close it. This is the single list of open items: §18 of `SPRINT_PLANNER_SPEC.md` points
here, so add new items to this file. Spec IDs are in brackets.

Last updated: 2026-10-26 (live staging and production acceptance; PR #5 cleanup deployment remains open)

## 1. Before the first deploy to staging

- [x] **Merge the GitHub and AI implementation PR**
  - **State:** PR #5 was merged into `staging` on 2026-10-26. Its requested cleanup is a follow-up change; merge does not establish staging acceptance.

- [ ] **Wipe the staging database** (MIG-3) · Johnny
  - **Historical scope:** original Initial-App migration task, not a requirement of these Eason changes. This branch has no schema changes; verify the current deployed state before acting on this old item.
  - **Why:** the new schema is created from scratch by Alembic and can't migrate over the base app's tables, so the first deploy fails until the old tables are gone.
  - **Needed:** in the Coolify terminal on the staging `db` container, run
    `psql -U appuser -d appdb -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`
    right before `Initial-App` is merged to `staging`.

- [ ] **Update the environment variables in Coolify** (OPS-3) · Johnny
  - **Needed:** in both the staging and production apps:
    - **Add** `APP_TIMEZONE=America/Denver` and `SESSION_COOKIE_SECURE=false`.
    - **Remove** the old `OPENAI_MODEL`, `OPENAI_API_KEY` and `DEFAULT_USER_ID`.
    - **Set** separate `ANALYSIS_LLM_API_KEY` and `REVIEW_LLM_API_KEY` values and the explicit AI-7 provider/model settings from the README. Class analysis also needs `ANALYSIS_LLM_REASONING_EFFORT=none`.
    - **Don't set** `SEED_DEMO_DATA`.
  - **Verified 2026-10-26:** both environments use `America/Denver`, `SESSION_COOKIE_SECURE=false` and `SEED_DEMO_DATA=false`. Analysis uses the class proxy with reasoning `none`; review uses explicit OpenAI `gpt-6-luna`, reasoning `high`. All three integration secrets are runtime-only. `OPENAI_MODEL` and its Preview copies were removed; `DEFAULT_USER_ID` is absent.
  - **Remaining dependency:** `OPENAI_API_KEY` values are empty in both environments and their Preview copies. Coolify refuses to delete these rows while the deployed Compose file references the name. Deploy the review-cleanup PR first, then remove the obsolete empty rows. No existing key is revoked.

- [ ] **Set up branch protection** on `staging` and `main` (TEST-5)
  - **Needed:** someone with admin rights requires one approving review and a passing `test` check on both branches. Alternatively, tell me it's OK to do this with the `gh` CLI.

## 2. AI and GitHub integration

- [x] **Staging AI configuration** (AI-7) · Eason
  - Fresh analysis and review completed after the configuration redeploy at `0cee914`. They used `classroom-chat` and `gpt-6-luna` respectively, with independent keys and an empty legacy shared key.
- [x] **Staging GitHub access and repository URL** (REPO-4, GH-4, GH-8) · Eason
  - The live review reads the linked `eason` branch and PR #8. An unchanged repeat reuses its Matches verdict. No token is stored in Git.
- [x] **Production AI and GitHub configuration** (AI-7, GH-8) · Eason
  - Explicit review model/key and a read-only GitHub token are configured. The `a18abcc` configuration redeploy succeeded; both services return healthy responses. Production's dedicated acceptance project shows PR #8 as merged and completes class-proxy analysis plus an OpenAI review with commit-pinned evidence.
- [x] **Targeted real-service acceptance**
  - Both environments generated fresh analyses and reviews after deployment. Production also verified URL and branch normalization, three code-backed criteria, unchanged-result reuse, a Final report surviving reload, a new draft preserving that Final, and automatic On close analysis with the unfinished story retained. Only dedicated acceptance data was changed; no existing team story was edited.
  - Invalid-input, no-link, missing-branch, authorization and provider-error cases remain covered by the automated regression suite; this is not a claim that every such case was repeated live.
- [ ] **Deploy the PR #5 review-cleanup code and finish obsolete-variable removal** · deployment owner
  - The accepted runtime configuration is live, but this follow-up's code and documentation still require PR approval and deployment to `staging`, then normal promotion to `main`. After each deployment, remove the now-unused empty `OPENAI_API_KEY` rows and repeat health/AI smoke checks. Do not wipe either database; this follow-up has no schema change.

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
