from app.main import app
from app.services.github_client import get_github_client
from app.services.github_links import slugify

from .fakes import FakeGitHub
from .helpers import create_project, create_story, get_story, me, ok, update_story

REPO_URL = "https://github.com/byu-ml-capstone/dinnerbell"


def project_with_repo(client) -> dict:
    project = create_project(client)
    return ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": REPO_URL}))


def test_branch_url_is_stored_as_a_branch_name(client):
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Login", github_branch=f"{REPO_URL}/tree/johnny/login-page")
    assert story["github_branch"] == "johnny/login-page"
    detail = get_story(client, story["id"])
    assert detail["branch_url"] == f"{REPO_URL}/tree/johnny/login-page"


def test_branch_url_for_another_repo_is_rejected(client):
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Login")
    response = client.put(f"/api/stories/{story['id']}", json={"github_branch": "https://github.com/someone/else/tree/main"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Branch URL is for a different repository"
    assert client.put(f"/api/stories/{story['id']}", json={"github_branch": "bad..name"}).status_code == 400
    assert client.put(f"/api/stories/{story['id']}", json={"github_branch": "has space"}).status_code == 400


def test_branch_without_repo_has_no_link(client):
    project = create_project(client)
    story = create_story(client, project["id"], "No repo yet", github_branch="alice/no-repo")
    assert story["github_branch"] == "alice/no-repo"
    assert get_story(client, story["id"])["branch_url"] is None


def test_suggested_branch(client, other_client):
    johnny = me(other_client)
    project = create_project(client, member_ids=(johnny["id"],))
    story = create_story(client, project["id"], "Add Login Page", assignee_id=johnny["id"])
    assert get_story(client, story["id"])["suggested_branch"] == "bob/add-login-page"
    unassigned = create_story(client, project["id"], "Fix the --weird-- title!!")
    assert get_story(client, unassigned["id"])["suggested_branch"] == "alice/fix-the-weird-title"
    assert len(slugify("x" * 100)) == 40


def test_live_status_finds_pr_after_branch_is_deleted(client):
    github = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Recipe search", github_branch="alice/recipe-search")
    status = ok(client.get(f"/api/stories/{story['id']}/github"))
    assert status["branch_exists"] is False
    assert status["pull_request"] == {
        "number": 12,
        "title": "Recipe search by ingredient",
        "state": "closed",
        "merged": True,
        "url": "https://github.com/byu-ml-capstone/dinnerbell/pull/12",
    }
    assert {(call[1], call[2], call[3]) for call in github.calls} == {
        ("byu-ml-capstone", "dinnerbell", "alice/recipe-search")
    }
    # Cached for five minutes.
    calls = len(github.calls)
    ok(client.get(f"/api/stories/{story['id']}/github"))
    assert len(github.calls) == calls


def test_live_status_errors(client):
    project = project_with_repo(client)
    with_branch = create_story(client, project["id"], "Branch", github_branch="alice/branch")
    without_branch = create_story(client, project["id"], "No branch")
    assert client.get(f"/api/stories/{with_branch['id']}/github").status_code == 503
    app.dependency_overrides[get_github_client] = lambda: FakeGitHub()
    assert client.get(f"/api/stories/{without_branch['id']}/github").status_code == 400
    failing = FakeGitHub()
    failing.fail = True
    app.dependency_overrides[get_github_client] = lambda: failing
    assert client.get(f"/api/stories/{with_branch['id']}/github").status_code == 502


def test_branch_is_cleared_with_empty_string(client):
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Branch", github_branch="alice/branch")
    assert update_story(client, story["id"], github_branch="")["github_branch"] is None
