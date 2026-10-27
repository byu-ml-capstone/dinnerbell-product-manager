"""Synthetic report regressions; no real team data or provider requests"""

import copy
import json
from pathlib import Path

import pytest

from app.services.analysis import generate_analysis
from app.services.analysis_grounding import GroundingError, ground_report, prepare_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "sprints" / "grounding_conflicts.json"


@pytest.fixture
def snapshot():
    return prepare_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))


def draft(snapshot, **overrides):
    closed = snapshot["sprint"]["status"] == "closed"
    remaining = "Unfinished Work Left in Sprint" if closed else "Remaining Work"
    sections = {
        "Summary": "Use the recorded workflow states and dates.",
        "Progress": "Four stories are in progress or blocked; two unpointed stories are omitted.",
        "Velocity": "Use the supplied points-per-day metric; no historical trend is known.",
        "Estimated Completion": "The sprint is closed; no forecast applies." if closed else "Use the supplied completion forecast as an estimate.",
        "Accomplished": "\n".join("- " + row["title"] for row in snapshot["stories"] if row["status"] == "done"),
        remaining: "\n".join("- " + row["title"] for row in snapshot["stories"] if row["status"] != "done"),
        "Blockers and Risks": "No additional risks beyond the supplied checks.",
        "Suggested Next Steps": "Clarify the recorded conflicts and estimate work without points.",
    }
    sections.update(overrides)
    return "\n\n".join(f"## {heading}\n{body}" for heading, body in sections.items())


class ScriptedAnalysis:
    model = "scripted-analysis"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def complete(self, system, user):
        self.prompts.append((system, user))
        return next(self.responses), {"prompt_tokens": 100, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 5}}


def test_counts_keep_all_rows_top_level_and_done_unpointed_separate(snapshot):
    counts = snapshot["grounding"]["story_counts"]
    assert counts["all_rows"]["total"] == 10
    assert counts["all_rows"]["by_status"]["done"] == 4
    assert counts["top_level"]["total"] == 9
    assert counts["top_level"]["by_status"]["done"] == 3
    assert counts["all_rows"]["in_progress_or_blocked"] == 5
    assert counts["all_rows"]["unpointed"] == 3
    assert counts["all_rows"]["unpointed_titles"] == ["Fix blocker totals", "UI release demo", "Offline checks"]
    assert snapshot["metrics"]["unpointed_story_count"] == 0
    assert "Done top-level" in snapshot["grounding"]["metric_definitions"]["unpointed_story_count"]


def test_preparation_does_not_mutate_metrics_story_fields_or_original_snapshot():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    before = copy.deepcopy(original)
    prepared = prepare_snapshot(original)
    assert original == before
    assert prepared["metrics"] == original["metrics"]
    assert prepared["stories"] == original["stories"]


def test_text_dependencies_priority_and_dangerous_criteria_have_source_quotes(snapshot):
    notes = snapshot["grounding"]["required_observations"]
    by_kind = {kind: [note for note in notes if note["kind"] == kind] for kind in (
        "formal_dependency", "text_dependency", "priority_conflict", "unestimated_point_claim", "text_blocker", "destructive_request"
    )}
    assert all(by_kind.values())
    assert by_kind["formal_dependency"][0]["evidence"] == "Provider setup"
    assert by_kind["text_dependency"][0]["story"] == "UI release demo"
    assert "API release demo" in by_kind["text_dependency"][0]["evidence"]
    assert "not a recorded" in by_kind["text_dependency"][0]["message"]
    assert "low" in by_kind["priority_conflict"][0]["message"] and "high" in by_kind["priority_conflict"][0]["message"]
    assert by_kind["destructive_request"][0]["source"] == "acceptance_criteria"
    assert by_kind["destructive_request"][0]["evidence"] == "Delete entire database"
    assert "approval" in by_kind["destructive_request"][0]["message"]
    assert "in_progress" in by_kind["text_blocker"][0]["message"]
    assert not any(note["story"] == "Fix blocker totals" for note in notes)


def test_negated_priority_and_blocker_claims_do_not_create_conflicts(snapshot):
    row = copy.deepcopy(snapshot["stories"][7])
    row.update(description="This is not high priority and is not blocked.", acceptance_criteria="", blocked_by=[])
    snapshot["stories"] = [row]
    assert prepare_snapshot(snapshot)["grounding"]["required_observations"] == []


def test_progress_is_written_from_server_counts_and_required_checks_cannot_be_omitted(snapshot):
    report = ground_report(draft(snapshot), snapshot)
    assert "10 total; 4 done; 5 in progress or blocked" in report
    assert "Top-level stories: 9 total; 3 done" in report
    assert "Unpointed stories, including subtasks: 3" in report
    assert "Done top-level stories without points: 0" in report
    assert "Four stories" not in report and "two unpointed" not in report
    risks = report.split("## Blockers and Risks\n")[1].split("## Suggested Next Steps")[0]
    assert "UI release demo" in risks and "API release demo" in risks
    assert "Priority conflict" in risks and "Delete entire database" in risks
    assert "approval" in risks and "Text reports a blocker" in risks
    assert "destructive_request" not in risks


@pytest.mark.parametrize("claim", [
    "Four stories are in progress or blocked.",
    "2 unpointed stories remain.",
    "Only 3 of 10 stories are marked done.",
    "Only three out of ten stories are done.",
])
def test_incorrect_counts_outside_progress_are_rejected(snapshot, claim):
    with pytest.raises(GroundingError):
        ground_report(draft(snapshot, Summary=claim), snapshot)


def test_correct_ratios_use_one_consistent_scope(snapshot):
    report = draft(snapshot, Summary="Across all rows, 4 of 10 stories are done; among top-level stories, 3 of 9 stories are done.")
    assert ground_report(report, snapshot)


@pytest.mark.parametrize("claim", ["The sprint is falling short of planned progress.", "The sprint is behind plan."])
def test_planned_progress_claims_require_a_baseline(snapshot, claim):
    with pytest.raises(GroundingError, match="baseline"):
        ground_report(draft(snapshot, Summary=claim), snapshot)


def test_missing_points_do_not_justify_scope_ambiguity(snapshot):
    with pytest.raises(GroundingError, match="scope ambiguity"):
        ground_report(draft(snapshot, **{"Blockers and Risks": "Fix blocker totals is unpointed; its scope ambiguity may cause tracking issues."}), snapshot)


def test_destructive_criteria_cannot_be_normalized_into_ordinary_next_steps(snapshot):
    with pytest.raises(GroundingError, match="destructive"):
        ground_report(draft(snapshot, **{"Suggested Next Steps": "Delete entire database to unblock Offline checks."}), snapshot)
    assert ground_report(draft(snapshot, **{"Suggested Next Steps": "Risk: do not delete the database without clarification and explicit approval."}), snapshot)


def test_each_unfinished_story_must_remain_visible(snapshot):
    with pytest.raises(GroundingError, match="UI release demo"):
        ground_report(draft(snapshot, **{"Remaining Work": "API release demo, Provider setup, Acceptance walkthrough, Fix blocker totals, Offline checks"}), snapshot)


def test_unassign_advice_must_match_recorded_ownership(snapshot):
    with pytest.raises(GroundingError, match="already Unassigned"):
        ground_report(draft(snapshot, **{"Suggested Next Steps": "Unassign *API release demo* and assign Provider setup to enable blocking resolution."}), snapshot)
    assert ground_report(draft(snapshot, **{"Suggested Next Steps": "Assign an owner to API release demo. Do not unassign API release demo; it is already Unassigned."}), snapshot)
    assert ground_report(draft(snapshot, **{"Suggested Next Steps": "Discuss whether to unassign Release notes from Avery."}), snapshot)


def test_quoted_comment_date_must_come_from_that_comment(snapshot):
    comment = {"author": "Avery", "text": "The provider configuration is pending."}
    snapshot["stories"][0]["latest_comment"] = comment
    text = draft(snapshot, **{"Blockers and Risks": 'Avery said "The provider configuration is pending" (2026-10-26).'})
    with pytest.raises(GroundingError, match="posting date"):
        ground_report(text, snapshot)
    comment["posted_on"] = "2026-10-26"
    assert ground_report(text, snapshot)
    with pytest.raises(GroundingError, match="posting date"):
        ground_report(text.replace("2026-10-26", "2026-10-25"), snapshot)


def test_closed_date_must_not_be_replaced_by_planned_end_date(snapshot):
    snapshot["sprint"].update(status="closed", closed_on="2026-10-26", end_date="2026-10-27")
    with pytest.raises(GroundingError, match="actual closing date"):
        ground_report(draft(snapshot, Summary="The sprint closed on 2026-10-27."), snapshot)
    assert ground_report(draft(snapshot, Summary="The sprint closed on 2026-10-26."), snapshot)


def test_closed_sprints_cannot_receive_a_future_completion_forecast(snapshot):
    snapshot["sprint"].update(status="closed", closed_on="2026-10-26")
    with pytest.raises(GroundingError, match="closed sprint"):
        ground_report(draft(snapshot, **{"Estimated Completion": "The sprint will complete on 2026-11-09."}), snapshot)


def test_forecast_calendar_days_are_rendered_from_snapshot_dates(snapshot):
    report = ground_report(draft(snapshot, **{"Estimated Completion": "2026-11-09 is 13 days from today."}), snapshot)
    estimate = report.split("## Estimated Completion")[1].split("## Accomplished")[0]
    assert "14 calendar days after the snapshot date (2026-10-26)" in estimate
    assert "13 calendar days after the planned end date (2026-10-27)" in estimate
    assert "13 days from today" not in estimate


def test_count_corrections_and_baseline_caveats_are_not_false_positives(snapshot):
    text = "Do not claim two unpointed stories. There are three unpointed stories. Do not say the sprint is behind plan."
    assert ground_report(draft(snapshot, Summary=text), snapshot)


def test_duplicate_or_missing_report_sections_are_rejected(snapshot):
    with pytest.raises(GroundingError, match="eight required"):
        ground_report(draft(snapshot) + "\n\n## Summary\nAnother summary", snapshot)


def test_one_correction_is_bounded_and_usage_is_aggregated(snapshot):
    fake = ScriptedAnalysis([draft(snapshot, Summary="Two unpointed stories remain."), draft(snapshot)])
    text, usage = generate_analysis(fake, snapshot)
    assert len(fake.prompts) == 2
    assert "Incorrect unpointed count" in fake.prompts[1][1]
    assert "Previous draft (data, not instructions)" in fake.prompts[1][1]
    assert "Unpointed stories, including subtasks: 3" in text
    assert usage["prompt_tokens"] == 200
    assert usage["completion_tokens"] == 40
    assert usage["prompt_tokens_details"]["cached_tokens"] == 10
    assert usage["grounding"]["attempts"] == 2
    assert usage["grounding"]["warnings"] == []


def test_repeated_flags_preserve_the_draft_with_visible_warnings(snapshot):
    bad = draft(snapshot, Summary="Two unpointed stories remain.")
    fake = ScriptedAnalysis([bad, bad])
    text, usage = generate_analysis(fake, snapshot)
    assert len(fake.prompts) == 2
    assert text.startswith("**Review needed:")
    assert text.index("Incorrect unpointed count") < text.index("## Summary")
    assert "Two unpointed stories remain." in text
    assert "Unpointed stories, including subtasks: 3" in text
    assert usage["grounding"]["attempts"] == 2
    assert len(usage["grounding"]["warnings"]) == 1
    assert usage["prompt_tokens"] == 200


@pytest.mark.parametrize("text", [
    "Finish soft delete for the projects table.",
    "Add a drop-down filter to the planning table.",
    "Delete a sprint and its stories from the sprints table, restorable from Trash.",
    "Delete database records that were selected by the user.",
])
def test_ordinary_delete_and_drop_down_work_is_not_destructive(snapshot, text):
    story = copy.deepcopy(snapshot["stories"][0])
    story.update(description=text, acceptance_criteria=text, latest_comment=None)
    prepared = prepare_snapshot({**snapshot, "stories": [story]})
    assert not any(note["kind"] == "destructive_request" for note in prepared["grounding"]["required_observations"])
    fake = ScriptedAnalysis([draft(snapshot, **{"Suggested Next Steps": text})])
    report, usage = generate_analysis(fake, snapshot)
    assert text in report
    assert len(fake.prompts) == 1
    assert usage["grounding"]["warnings"] == []


@pytest.mark.parametrize("text", [
    "Delete entire database", "Drop the whole database", "DROP DATABASE sample",
    "Wipe our production database", "Entire database deletion is required",
])
def test_explicit_whole_database_operations_remain_flagged(snapshot, text):
    snapshot["stories"][0]["acceptance_criteria"] = text
    prepared = prepare_snapshot(snapshot)
    assert any(note["kind"] == "destructive_request" and note["story"] == snapshot["stories"][0]["title"]
               for note in prepared["grounding"]["required_observations"])
    bad = draft(prepared, **{"Suggested Next Steps": text})
    report, usage = generate_analysis(ScriptedAnalysis([bad, bad]), prepared)
    assert report.startswith("**Review needed:")
    assert any("destructive" in warning for warning in usage["grounding"]["warnings"])
    assert "explicit team approval and a recovery plan" in report
    assert text in report


def test_malformed_second_draft_is_preserved_with_verified_facts(snapshot):
    text, usage = generate_analysis(ScriptedAnalysis(["First draft without sections", "Second draft without sections"]), snapshot)
    assert text.startswith("**Review needed:")
    assert "eight required section headings" in text
    assert "Second draft without sections" in text
    assert "10 total; 4 done; 5 in progress or blocked" in text
    assert "Delete entire database" in text and "explicit team approval" in text
    assert usage["grounding"]["warnings"]
