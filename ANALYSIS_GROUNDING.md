# Sprint analysis grounding

This change addresses report accuracy in AI-4, AI-5 and AI-9. It does not change the shared metrics rules, story workflow, provider configuration or existing saved reports.

`backend/app/services/analysis_grounding.py` adds a `grounding` object to the saved AI input. It distinguishes all story rows from top-level stories, supplies their status and unpointed counts, and explains that `metrics.unpointed_story_count` counts **done top-level stories without points**. Point metrics continue to exclude duplicate subtask points. Closed-sprint point metrics remain frozen; the row counts describe the rows in the analysis snapshot.

The server renders Progress from those facts and Estimated Completion from the supplied forecast and calendar dates. This keeps days from the snapshot date separate from days beyond the planned end date. It also includes source quotations for recorded dependencies and explicitly detected text dependencies, priority conflicts, unestimated point claims, textual blockers and destructive database criteria. Text claims remain claims: the analysis never creates dependency links, changes status or priority, assigns estimates, or executes actions (D-20, D-36). Multiple observations about the same source sentence share one quotation.

The model must retain every unfinished story in the remaining-work section. Checks reject the covered incorrect count formulations, mixed done/total scopes, unsupported planned-progress or scope-ambiguity claims, ordinary recommendations to perform destructive database operations, and incorrect closing-date/forecast statements. Ownership advice must match the assignee; an already Unassigned story cannot be unassigned again. Quoted comments cannot acquire an invented posting date. New inputs include the latest comment's actual `posted_at` and local `posted_on`; legacy comments without dates must remain undated. Sprint inputs supply `closed_at` and `closed_on` so the planned `end_date` is not used as the actual closing date.

A rejected draft gets at most one correction request. Two invalid drafts produce a retryable failed analysis without saving the invalid text as a completed report. Token usage for both returned responses is aggregated. Finalization still requires a complete analysis and a human review; regenerating creates a separate analysis as before.

These checks cover explicit English patterns and the regression examples. They are not a general semantic verifier, and can miss paraphrases or nuanced conflicts. The approximate 600-word target yields to complete story coverage and source-backed checks in large sprints. Human review of the supplied data and draft remains necessary.

## Verification

- `backend/tests/fixtures/sprints/grounding_conflicts.json` is synthetic and contains no real team records. Its cases include text/field conflicts, two kinds of dependencies, a textual blocker, destructive criteria, a subtask and three unpointed stories.
- `backend/tests/test_analysis_grounding.py` covers deterministic facts, negation, report checks and bounded correction. `backend/tests/test_analyses.py` covers persisted success/failure, usage, actual closing dates and unchanged story fields.
- Run the backend suite against a disposable PostgreSQL database: the test setup drops and rebuilds its schema. CI uses fake providers. `alembic check` should find no schema changes.
- `backend/scripts/ai_eval.py` uses the same grounding and correction path for manual provider evaluation. Run it only with intentionally configured Analysis credentials. Keep private inputs, outputs and usage under ignored `backend/ai_eval_out/`.

This local change does not imply that staging or production runs the new behavior. Deployment requires the normal review and merge workflow.

Verification on 2026-10-26: **192 backend tests passed**, and `alembic check` found no new upgrade operations, using an isolated temporary PostgreSQL container. The earlier local `gpt-6-luna` replay remains recorded separately.

The actual LiteLLM `classroom-chat` provider was then tested using the staging backend's existing environment with reasoning effort `none`. The candidate source was loaded into an isolated Python process, with bytecode writes disabled, without changing the deployed service, configuration or database. Source hashes link the replay to code commit `c1d85af`.

- Original failing snapshot: the first draft's incorrect active/blocked count was rejected; one automatic correction produced a 488-word report with the correct scopes, dependencies, conflicts and destructive-operation warning.
- Synthetic closed sprint: a 206-word report retained unfinished work, used the actual closing date rather than the planned end date, omitted a future completion forecast, and did not invent a posting date for an undated comment.

Earlier classroom outputs exposed redundant unassignment advice, an invented comment date and a mistaken relative-day comparison. The added checks, source timestamps and deterministic forecast section cover those regressions. This remains provider integration verification, not post-merge HTTP/UI acceptance of a deployment. Private replay inputs, outputs and usage remain ignored.
