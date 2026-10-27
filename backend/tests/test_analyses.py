import re
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.main import app
from app.models import SprintAnalysis
from app.services import clock
from app.services.jobs import mark_stale_jobs
from app.services.llm import get_analysis_llm

from .fakes import FakeAnalysisLLM, timeout_error
from .helpers import (
    active_sprint,
    close_sprint,
    create_project,
    create_story,
    me,
    ok,
    update_story,
)


def use_llm(fake: FakeAnalysisLLM) -> FakeAnalysisLLM:
    app.dependency_overrides[get_analysis_llm] = lambda: fake
    return fake


def run_analysis(client, sprint_id: str, context: str = "") -> dict:
    created = ok(client.post(f"/api/sprints/{sprint_id}/analyses", json={"additional_context": context}), 202)
    assert created["status"] == "pending"
    return ok(client.get(f"/api/analyses/{created['id']}"))


def test_analysis_runs_for_an_active_sprint(client):
    fake = use_llm(FakeAnalysisLLM(text="## Summary\nGood progress."))
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    create_story(client, project["id"], "Story", sprint_id=sprint["id"], story_points=3)
    analysis = run_analysis(client, sprint["id"], context="Demo on Friday")
    assert analysis["status"] == "complete"
    assert analysis["ai_content"].startswith("## Summary\nGood progress.")
    assert "All story rows, including subtasks: 1 total" in analysis["ai_content"]
    assert analysis["trigger"] == "manual"
    assert analysis["created_by_name"] == "Alice Anders"
    assert analysis["model"] == fake.model
    assert analysis["input_snapshot"]["additional_context"] == "Demo on Friday"
    assert analysis["metrics"]["remaining_points"] == 3
    assert analysis["usage"]["prompt_tokens"] == 100


def test_regenerating_never_overwrites_a_saved_analysis(client):
    use_llm(FakeAnalysisLLM())
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    first = run_analysis(client, sprint["id"])
    saved = ok(client.put(f"/api/analyses/{first['id']}", json={"final_content": "Edited by Alice"}))
    assert saved["finalized_by_name"] == "Alice Anders"
    run_analysis(client, sprint["id"])
    analyses = ok(client.get(f"/api/sprints/{sprint['id']}/analyses"))
    assert len(analyses) == 2
    original = ok(client.get(f"/api/analyses/{first['id']}"))
    assert original["final_content"] == "Edited by Alice"


def test_prompt_uses_names_and_titles_not_ids(client, other_client):
    fake = use_llm(FakeAnalysisLLM())
    bob = me(other_client)
    project = create_project(client, member_ids=(bob["id"],))
    sprint = active_sprint(client, project["id"])
    blocker = create_story(client, project["id"], "Recipe API", sprint_id=sprint["id"], assignee_id=bob["id"])
    blocked = create_story(client, project["id"], "Recipe UI", sprint_id=sprint["id"], story_points=5)
    ok(client.post(f"/api/stories/{blocker['id']}/blocks/{blocked['id']}", json={}))
    comment = ok(client.post(f"/api/stories/{blocked['id']}/comments", json={"text": "Waiting on the API"}))
    ok(client.post(f"/api/sprints/{sprint['id']}/messages", json={"text": "Standup notes"}), 201)
    analysis = run_analysis(client, sprint["id"])
    system, user = fake.prompts[-1]
    latest = next(row["latest_comment"] for row in analysis["input_snapshot"]["stories"] if row["title"] == "Recipe UI")
    assert latest["posted_at"] == comment["created_at"]
    assert latest["posted_on"] == clock.local_date(datetime.fromisoformat(comment["created_at"])).isoformat()
    assert "Bob Brown" in user and "Recipe API" in user and "Recipe UI" in user
    assert "Waiting on the API" in user and "Standup notes" in user
    assert not re.search(r"\b(user|story|sprint|proj)-[0-9a-f]{10}\b", user)
    assert "Use only the supplied sprint data" in system
    assert "## Remaining Work" in system


def test_closing_starts_an_analysis_with_metrics_and_unfinished_work(client):
    fake = use_llm(FakeAnalysisLLM())
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    done = create_story(client, project["id"], "Shipped", sprint_id=sprint["id"], story_points=5)
    create_story(client, project["id"], "Left over", sprint_id=sprint["id"], story_points=3)
    update_story(client, done["id"], status="done")
    result = close_sprint(client, sprint["id"])
    assert result["analysis_id"]
    analysis = ok(client.get(f"/api/analyses/{result['analysis_id']}"))
    assert analysis["trigger"] == "sprint_closed"
    assert analysis["status"] == "complete"
    assert analysis["created_by_id"] is None
    snapshot = analysis["input_snapshot"]
    assert snapshot["unfinished_stories_left_in_sprint"] == ["Left over"]
    assert snapshot["metrics"]["estimated_completion_date"] == "not enough data"
    assert snapshot["sprint"]["closed_at"]
    assert snapshot["sprint"]["closed_on"] == clock.today().isoformat()
    for key in ("committed_points", "completed_points", "remaining_points", "estimated_completion_date"):
        assert key in snapshot["metrics"]
    system, user = fake.prompts[-1]
    assert "## Unfinished Work Left in Sprint" in system
    assert "For a closed sprint, do not give a completion date estimate" in system
    assert '"completed_points": 5' in user


def test_close_without_ai_still_closes(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    result = close_sprint(client, sprint["id"])
    assert result["analysis_id"] is None
    assert result["status"] == "closed"


def test_deleted_stories_are_left_out(client):
    fake = use_llm(FakeAnalysisLLM())
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    create_story(client, project["id"], "Kept", sprint_id=sprint["id"])
    gone = create_story(client, project["id"], "Deleted secret story", sprint_id=sprint["id"])
    ok(client.delete(f"/api/stories/{gone['id']}"))
    run_analysis(client, sprint["id"])
    assert "Deleted secret story" not in fake.prompts[-1][1]


def test_failed_call_is_recorded(client):
    use_llm(FakeAnalysisLLM(error=timeout_error()))
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    analysis = run_analysis(client, sprint["id"])
    assert analysis["status"] == "failed"
    assert "timed out" in analysis["error"]
    assert client.put(f"/api/analyses/{analysis['id']}", json={"final_content": "x"}).status_code == 400


def test_grounding_failure_is_recorded_and_unsafe_draft_is_not_saved(client):
    fake = use_llm(FakeAnalysisLLM(text="## Summary\nThe sprint is falling short of planned progress."))
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    create_story(client, project["id"], "A clear task", sprint_id=sprint["id"], description="Implement the specified endpoint")
    analysis = run_analysis(client, sprint["id"])
    assert analysis["status"] == "failed"
    assert analysis["ai_content"] is None
    assert "grounding checks" in analysis["error"]
    assert analysis["usage"]["grounding"]["attempts"] == 2
    assert analysis["usage"]["prompt_tokens"] == 200
    assert len(fake.prompts) == 2
    assert client.put(f"/api/analyses/{analysis['id']}", json={"final_content": "x"}).status_code == 400


def test_corrected_analysis_keeps_story_fields_and_metric_semantics(client):
    class CorrectingLLM(FakeAnalysisLLM):
        def complete(self, system, user):
            self.text = "## Summary\nThe sprint is falling short of planned progress." if not self.prompts else "## Summary\nUse the recorded facts."
            return super().complete(system, user)

    fake = use_llm(CorrectingLLM())
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "A clear task", sprint_id=sprint["id"],
                         description="This is high priority but has no assigned estimate", priority="low")
    before = ok(client.get(f"/api/stories/{story['id']}"))
    analysis = run_analysis(client, sprint["id"])
    assert analysis["status"] == "complete"
    assert len(fake.prompts) == 2
    assert analysis["usage"]["grounding"]["attempts"] == 2
    assert analysis["input_snapshot"]["grounding"]["story_counts"]["all_rows"]["unpointed"] == 1
    assert analysis["metrics"]["unpointed_story_count"] == 0
    assert "Priority conflict" in analysis["ai_content"]
    after = ok(client.get(f"/api/stories/{story['id']}"))
    for field in ("status", "priority", "story_points", "updated_at"):
        assert after[field] == before[field]


def test_not_configured_returns_503(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    assert client.post(f"/api/sprints/{sprint['id']}/analyses", json={}).status_code == 503


def test_unconfigured_analysis_still_checks_membership(client, other_client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    assert other_client.post(f"/api/sprints/{sprint['id']}/analyses", json={}).status_code == 403


def test_stale_jobs_are_marked_failed_on_startup(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    with SessionLocal() as db:
        stale = SprintAnalysis(sprint_id=sprint["id"], status="running", started_at=clock.now() - timedelta(minutes=20))
        fresh = SprintAnalysis(sprint_id=sprint["id"], status="running", started_at=clock.now())
        db.add_all([stale, fresh])
        db.commit()
        assert mark_stale_jobs(db) == 1
        db.refresh(stale)
        db.refresh(fresh)
        assert stale.status == "failed" and stale.error == "Interrupted by restart"
        assert fresh.status == "running"


def test_analyses_check_membership(client, other_client):
    use_llm(FakeAnalysisLLM())
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    analysis = run_analysis(client, sprint["id"])
    assert other_client.post(f"/api/sprints/{sprint['id']}/analyses", json={}).status_code == 403
    assert other_client.get(f"/api/sprints/{sprint['id']}/analyses").status_code == 403
    assert other_client.get(f"/api/analyses/{analysis['id']}").status_code == 403
    assert other_client.put(f"/api/analyses/{analysis['id']}", json={"final_content": "x"}).status_code == 403
