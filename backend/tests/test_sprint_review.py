from datetime import date

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.main import app
from app.models import SprintReview, SprintReviewItem
from app.services.github_client import get_github_client
from app.services.llm import get_review_llm

from .fakes import FakeGitHub, FakeReviewLLM, tool_turn, verdict_turn
from .helpers import PASSWORD, at, create_project, create_sprint, create_story, create_subtask, ok, update_story

REPO_URL = "https://github.com/byu-ml-capstone/dinnerbell"
EVIDENCE = [{"path": "backend/app/recipes.py", "lines": "1-4", "commit": None, "note": "search_recipes"}]


def install(llm: FakeReviewLLM | None = None, github: FakeGitHub | None = None):
    llm = llm or FakeReviewLLM()
    github = github or FakeGitHub()
    app.dependency_overrides[get_review_llm] = lambda: llm
    app.dependency_overrides[get_github_client] = lambda: github
    return llm, github


@pytest.fixture
def sprint_setup(client, travel):
    travel(at(date(2026, 11, 10), 10))
    project = create_project(client)
    ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": REPO_URL}))
    sprint = create_sprint(client, project["id"], date(2026, 11, 2), date(2026, 11, 13), "Sprint 4")
    stories = {}
    stories["complete"] = create_story(
        client, project["id"], "Recipe search", sprint_id=sprint["id"], github_branch="alice/recipe-search",
        acceptance_criteria="Search by ingredient",
    )
    update_story(client, stories["complete"]["id"], status="done")
    stories["partial"] = create_story(
        client, project["id"], "Grocery list", sprint_id=sprint["id"], github_branch="alice/grocery-list",
        acceptance_criteria="Combines ingredients\nGroups by aisle",
    )
    stories["empty"] = create_story(
        client, project["id"], "Pantry tracking", sprint_id=sprint["id"], github_branch="alice/pantry-tracking",
    )
    update_story(client, stories["empty"]["id"], status="done")
    stories["unlinked"] = create_story(client, project["id"], "Family login", sprint_id=sprint["id"])
    stories["subtask"] = create_subtask(client, stories["complete"]["id"], "Recipe search: tests")
    return project, sprint, stories


def standard_scripts() -> dict:
    return {
        "Recipe search": [
            tool_turn("get_pull_request_files", "c1", pr_number=12),
            tool_turn("read_file", "c2", path=".env"),
            tool_turn("read_file", "c3", path="frontend/package-lock.json"),
            tool_turn("read_file", "c4", path="../../etc/passwd"),
            tool_turn("read_file", "c5", path="backend/app/recipes.py"),
            verdict_turn(
                "matches",
                evidence=EVIDENCE,
                criteria=[{"criterion": "Search by ingredient", "status": "met", "evidence": "search_recipes(ingredient)"}],
            ),
        ],
        "Grocery list": [
            tool_turn("get_pull_request_files", "c1", pr_number=13),
            verdict_turn(
                "partial",
                evidence=[{"path": "backend/app/grocery.py", "lines": "1-2", "commit": None, "note": "combine"}],
                has_tests=False,
            ),
        ],
        "Pantry tracking": [tool_turn("get_pull_request_files", "c1", pr_number=14), verdict_turn("no_evidence", has_tests=False)],
        "Recipe search: tests": [verdict_turn("matches", evidence=[{"path": "backend/tests/test_recipes.py", "lines": "1-2", "commit": None, "note": "test"}])],
    }


def start(client, sprint_id: str) -> dict:
    created = ok(client.post(f"/api/sprints/{sprint_id}/reviews"), 202)
    return ok(client.get(f"/api/reviews/{created['id']}"))


def by_title(review: dict) -> dict:
    return {item["story_title"]: item for item in review["items"]}


def test_review_gives_each_story_a_verdict(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    llm, _github = install(FakeReviewLLM(standard_scripts()))
    review = start(client, sprint["id"])
    assert review["status"] == "complete"
    assert review["items_total"] == 5 and review["items_done"] == 5
    items = by_title(review)
    assert items["Recipe search"]["verdict"] == "matches"
    assert items["Recipe search"]["evidence"][0]["path"] == "backend/app/recipes.py"
    assert items["Recipe search"]["pr_number"] == 12
    assert items["Recipe search"]["head_sha"] == "a" * 40
    assert items["Grocery list"]["verdict"] == "partial"
    assert items["Grocery list"]["has_tests"] is False
    assert items["Pantry tracking"]["verdict"] == "no_evidence"
    assert items["Pantry tracking"]["claimed_status"] == "done"
    assert items["Family login"]["verdict"] == "no_link"
    assert llm.story_calls("Family login") == 0
    # REPO-16: the subtask has no branch, so it's reviewed against its parent's branch and PR.
    assert items["Recipe search: tests"]["branch"] == "alice/recipe-search"
    assert items["Recipe search: tests"]["verdict"] == "matches"
    assert review["summary_markdown"] == llm.summary
    assert review["usage"]["tool_calls"] == 7
    assert [pull["pr_number"] for pull in review["unlinked_work"]] == [20]


@pytest.mark.parametrize("changed_setting", ["model", "reasoning_effort"])
def test_changed_model_or_effort_does_not_reuse_old_verdict(client, sprint_setup, changed_setting):
    _project, sprint, _stories = sprint_setup
    first_llm, github = install(FakeReviewLLM(standard_scripts()))
    first_llm.reasoning_effort = "low"
    start(client, sprint["id"])

    next_llm = FakeReviewLLM(standard_scripts())
    next_llm.reasoning_effort = "low"
    setattr(next_llm, changed_setting, "high" if changed_setting == "reasoning_effort" else "another-review-model")
    install(next_llm, github)
    review = start(client, sprint["id"])
    assert by_title(review)["Recipe search"]["reused_from_item_id"] is None
    assert next_llm.story_calls("Recipe search") > 0


def test_disjoint_evidence_ranges_and_old_history_get_separate_links(client, sprint_setup):
    _project, sprint, stories = sprint_setup
    scripts = standard_scripts()
    evidence = [{"path": "backend/app/grocery.py", "lines": "L1-L2, 4, 7 - 9", "commit": None, "note": "Separate source ranges"}]
    scripts["Grocery list"] = [verdict_turn("matches", evidence=evidence)]
    install(FakeReviewLLM(scripts))
    review = start(client, sprint["id"])
    assert [row["lines"] for row in by_title(review)["Grocery list"]["evidence"]] == ["1-2", "4", "7-9"]
    # Existing reports may already contain the model's comma-separated format
    with SessionLocal() as db:
        item = db.query(SprintReviewItem).filter_by(review_id=review["id"], story_id=stories["partial"]["id"]).one()
        item.evidence = evidence
        db.commit()
    historical = ok(client.get(f"/api/reviews/{review['id']}"))
    assert [row["lines"] for row in by_title(historical)["Grocery list"]["evidence"]] == ["1-2", "4", "7-9"]


@pytest.mark.parametrize("lines", ["0", "4-1", "not a line"])
def test_invalid_line_numbers_do_not_support_matches(client, sprint_setup, lines):
    _project, sprint, _stories = sprint_setup
    scripts = standard_scripts()
    scripts["Grocery list"] = [verdict_turn("matches", evidence=[{"path": "backend/app/grocery.py", "lines": lines}])]
    install(FakeReviewLLM(scripts))
    item = by_title(start(client, sprint["id"]))["Grocery list"]
    assert item["verdict"] == "cant_tell"
    assert item["evidence"][0]["lines"] is None


def test_tools_follow_the_file_policy(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    llm, github = install(FakeReviewLLM(standard_scripts()))
    start(client, sprint["id"])
    outputs = llm.tool_outputs["Recipe search"]
    pr_files, env_file, lockfile, escape, source = outputs
    assert all(output.startswith("<repo_content") for output in outputs)
    assert "search_recipes" in pr_files
    assert "lockfile contents that must never be sent" not in pr_files
    assert "[excluded by policy]" in pr_files
    assert "[excluded by policy]" in env_file and "sk-should-never-be-read" not in env_file
    assert "[excluded by policy]" in lockfile
    assert "Invalid path" in escape
    assert "1 def search_recipes" in source
    # The client was only ever asked about the configured repo, never a pasted URL.
    assert {(call[1], call[2]) for call in github.calls} == {("byu-ml-capstone", "dinnerbell")}
    assert not any(call[0] == "get_contents" and call[3] in (".env", "frontend/package-lock.json") for call in github.calls)


def test_prompt_treats_pr_text_as_data(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    llm, _github = install(FakeReviewLLM(standard_scripts()))
    start(client, sprint["id"])
    context = next(call["context"] for call in llm.calls if call.get("title") == "Recipe search")
    assert '<repo_content source="pull_request_body">' in context
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in context.split('<repo_content source="pull_request_body">')[1]


def test_review_never_changes_stories(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    install(FakeReviewLLM(standard_scripts()))
    query = text("SELECT id, title, status, sprint_id, story_points, updated_at FROM stories ORDER BY id")
    with engine.connect() as connection:
        before = connection.execute(query).all()
    start(client, sprint["id"])
    with engine.connect() as connection:
        assert connection.execute(query).all() == before


def test_matches_without_evidence_becomes_cant_tell(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    scripts = standard_scripts()
    scripts["Grocery list"] = [verdict_turn("matches", evidence=[{"path": "backend/app/grocery.py", "lines": None, "commit": None, "note": "vague"}])]
    install(FakeReviewLLM(scripts))
    item = by_title(start(client, sprint["id"]))["Grocery list"]
    assert item["verdict"] == "cant_tell"
    assert item["summary"].startswith("No evidence cited.")


def test_tool_call_limit(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    scripts = standard_scripts()
    scripts["Grocery list"] = [tool_turn("list_directory", f"c{index}", path="backend") for index in range(16)]
    install(FakeReviewLLM(scripts))
    item = by_title(start(client, sprint["id"]))["Grocery list"]
    assert item["verdict"] == "cant_tell"
    assert item["summary"] == "Review limit reached."


def test_invalid_output_is_cant_tell(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    scripts = standard_scripts()
    bad = verdict_turn("matches", evidence=EVIDENCE)
    bad.text = "Looks fine to me!"
    scripts["Grocery list"] = [bad]
    install(FakeReviewLLM(scripts))
    assert by_title(start(client, sprint["id"]))["Grocery list"]["verdict"] == "cant_tell"


def test_unchanged_stories_reuse_the_last_result(client, sprint_setup):
    _project, sprint, stories = sprint_setup
    scripts = standard_scripts()
    llm, _github = install(FakeReviewLLM(scripts))
    first = by_title(start(client, sprint["id"]))
    calls_after_first = llm.story_calls("Recipe search")
    # Change one story's criteria so only it is reviewed again.
    update_story(client, stories["partial"]["id"], acceptance_criteria="Combines ingredients")
    llm.scripts["Grocery list"] = [verdict_turn("matches", evidence=[{"path": "backend/app/grocery.py", "lines": "1-2", "commit": None, "note": "ok"}])]
    second = by_title(start(client, sprint["id"]))
    assert llm.story_calls("Recipe search") == calls_after_first
    assert second["Recipe search"]["reused_from_item_id"] == first["Recipe search"]["id"]
    assert second["Recipe search"]["verdict"] == "matches"
    assert second["Grocery list"]["reused_from_item_id"] is None
    assert second["Grocery list"]["verdict"] == "matches"


def test_branch_without_pr_and_missing_branch(client, travel):
    travel(at(date(2026, 11, 10), 10))
    project = create_project(client)
    ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": REPO_URL}))
    sprint = create_sprint(client, project["id"], date(2026, 11, 2), date(2026, 11, 13))
    create_story(client, project["id"], "Login page", sprint_id=sprint["id"], github_branch="alice/login-page")
    create_story(client, project["id"], "Gone branch", sprint_id=sprint["id"], github_branch="alice/deleted-without-pr")
    llm, _github = install(FakeReviewLLM({"Login page": [verdict_turn("cant_tell", summary="No diff yet.")]}))
    items = by_title(start(client, sprint["id"]))
    login_context = next(call["context"] for call in llm.calls if call.get("title") == "Login page")
    assert "No pull request" in login_context and "compare_refs" in login_context
    assert items["Login page"]["head_sha"] == "d" * 40
    assert items["Gone branch"]["verdict"] == "no_evidence"
    assert items["Gone branch"]["summary"] == "Branch and PR not found."
    assert llm.story_calls("Gone branch") == 0


def test_github_errors_become_cant_tell(client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    github = FakeGitHub()
    github.fail = True
    install(FakeReviewLLM({}), github)
    review = start(client, sprint["id"])
    assert review["status"] == "complete"
    verdicts = {item["story_title"]: item["verdict"] for item in review["items"]}
    assert verdicts["Recipe search"] == "cant_tell"
    assert verdicts["Family login"] == "no_link"
    assert review["unlinked_work"] == []


def test_deleted_stories_are_hidden_from_the_review(client, sprint_setup):
    _project, sprint, stories = sprint_setup
    install(FakeReviewLLM(standard_scripts()))
    created = ok(client.post(f"/api/sprints/{sprint['id']}/reviews"), 202)
    ok(client.delete(f"/api/stories/{stories['unlinked']['id']}"))
    review = ok(client.get(f"/api/reviews/{created['id']}"))
    assert "Family login" not in by_title(review)


def test_start_review_preconditions(client, sprint_setup):
    project, sprint, _stories = sprint_setup
    path = f"/api/sprints/{sprint['id']}/reviews"

    app.dependency_overrides[get_review_llm] = lambda: FakeReviewLLM()
    app.dependency_overrides[get_github_client] = lambda: None
    assert client.post(path).status_code == 503

    app.dependency_overrides[get_github_client] = lambda: FakeGitHub()
    app.dependency_overrides[get_review_llm] = lambda: None
    assert client.post(path).status_code == 503

    install(FakeReviewLLM(standard_scripts()))
    with SessionLocal() as db:
        db.add(SprintReview(sprint_id=sprint["id"], status="running", repo_url=REPO_URL))
        db.commit()
    assert client.post(path).status_code == 409

    ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": None}))
    assert client.post(path).status_code == 400


def test_reviews_check_membership(client, other_client, sprint_setup):
    _project, sprint, _stories = sprint_setup
    install(FakeReviewLLM(standard_scripts()))
    created = ok(client.post(f"/api/sprints/{sprint['id']}/reviews"), 202)
    ok(other_client.post("/api/auth/login", json={"username": "bob", "password": PASSWORD}))
    assert other_client.post(f"/api/sprints/{sprint['id']}/reviews").status_code == 403
    assert other_client.get(f"/api/sprints/{sprint['id']}/reviews").status_code == 403
    assert other_client.get(f"/api/reviews/{created['id']}").status_code == 403
    assert len(ok(client.get(f"/api/sprints/{sprint['id']}/reviews"))) == 1
