# Eason §9/§10 local verification — 2026-10-24

## Result and scope

Local implementation and real-service verification are complete. Both features use direct OpenAI `gpt-6-luna`: Analysis `medium`, Sprint review `high`. The locally supplied GitHub token successfully queried `byu-ml-capstone/dinnerbell-product-manager`. The repository was public at verification time; private-repository access has not been independently tested.

No GitHub branch, PR, setting, online database or Coolify service was changed. Latest `origin/main` is `37a26b5` and is already included in local `eason`. The remote has no `eason` branch yet. Push and PR remain the next handoff step. Local environment secrets and detailed evaluation outputs are ignored by Git.

## Frontend walkthrough

Open **http://localhost:8082/** and sign in as **taylor / devpassword**. Select **Live GitHub + AI verification**, then **Board** and **Live verification sprint**. Scroll down to **AI for Live verification sprint**.

| Check | Where to look | Verified result |
|---|---|---|
| Medium analysis | Analysis → existing history | Eight required sections, computed metrics, review caveats and deliberate negative test stories described without treating them as real product requirements |
| High code review | Sprint review → newest completed review | Five stories with the results below |
| Code evidence | Click a review story row | Criteria and commit-pinned GitHub file/line links; all six file/range references in this live result were checked against actual source contents |
| Review history/cache | Past reviews → compare latest two runs | Fresh run used tools; same-profile repeat reused the three linked verdicts and used zero tool calls (summary remains a new AI call) |
| Real PR status | Open the architecture story from the board → Branch | PR #4 is merged even though `synthesis-update` was deleted |
| Branch without PR | Open backend health story → Branch | `taft` exists with no PR |
| Missing branch | Open missing-branch story → Branch | Branch not found |
| Closed automatic report | Selected sprint → Close-trigger verification → Analysis | Saved On close analysis, Unfinished Work Left in Sprint, no completion date estimate |

Real review cases:

- **Architecture lessons documented [real PR #4] → Matches**: `ARCH_SYNTH.md` lines 6 and 50 support the criteria.
- **CSV export endpoint [deliberate missing feature] → No evidence**: a deliberate false “done” claim, not a requested DinnerBell feature. The PR only changes documentation, and the sprint router lacks the claimed endpoint.
- **Backend health route [real branch without PR] → Matches**: `backend/app/main.py` at the actual `taft` head has the health route.
- **No linked branch [negative case] → No link**.
- **Missing branch [negative case] → No evidence**.

The local project also contains backlog status-only examples for `Initial-App` and `main`. These links mean its unlinked-work section is correctly empty. A separate read-only check with an empty story set found merged PRs **#2 and #1** within the sprint window.

Existing save-Final, regenerate/history, Retry, sprint-switch and mock state checks are documented in `AI_SETUP_TESTING.md` and `GITHUB_LINKS_TESTING.md`. The free mock remains at **http://127.0.0.1:8083/**. There are currently no real open or closed-unmerged PRs in the selected repository, so those statuses are covered by mock/tests rather than creating artificial remote PRs.

## Analysis quality checks

All three supplied samples completed at medium effort: on-track, behind, and closed-with-carryover. Reports retained the supplied metrics, names, status distinctions and eight required headings. The closed sample was corrected to match server behavior: no completion estimate after close. The real close-trigger report also completed and preserved the unfinished work.

Review results remain advice. These are representative functional checks, not a claim that all future model conclusions will be correct.

## Fixes found during verification

1. **Review configuration cache** — `backend/app/services/sprint_review.py`: old behavior reused verdicts across model/effort changes. Two regression cases failed before the fix. Reuse now additionally requires the same repository and hashed profile of endpoint, model, effort, output limit, prompt, tools and verdict schema. The hash is stored in the existing usage JSON; old reports without it are evaluated again. No schema migration.
2. **Evidence links** — `services/sprint_review.py` and `routers/reviews.py`: real output contained comma-separated ranges, which make invalid GitHub anchors. Ranges are split into individual links on new results and historical reads. Zero, reversed and nonnumeric ranges cannot substantiate a Matches verdict without other valid evidence.
3. **Closed sprint estimates** — `services/analysis.py` and `tests/fixtures/sprints/closed_with_carryover.json`: the prompt explicitly excludes completion estimates after close, and the old sample's inconsistent date was removed.

## Validation and API use

- **164 backend tests passed** on a newly created disposable PostgreSQL container. Existing local databases were not used by pytest. Test container/network were removed afterwards.
- **Alembic check passed**: no model/schema differences.
- Frontend production build and interaction baseline passed for the prior implementation commit; this verification changes backend behavior and documentation, not frontend source.
- Real medium/high tests returned **31 successful API responses**. Reported aggregate usage conservatively estimated at **US$0.0128889**, below the US$1 verification cap. Input was priced at the full uncached rate; actual provider billing may differ. Retries without reported usage cannot be independently priced from response usage alone.
- Detailed snapshots, raw reports, request usage and the budget-guarded local harness are retained under ignored `backend/ai_eval_out/`, rather than committed with project data. API keys and tokens were not printed or stored in this report.

## Next step

Review the clean local commit, push **eason**, and open a PR into the team's **staging** branch. Keep merge and Coolify deployment separate. Coolify still needs its own environment settings; local `.env` does not travel with Git. Historical deployment and team-approval items in `OPEN_ITEMS.md` are not asserted complete by this local verification.
