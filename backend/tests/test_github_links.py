from types import SimpleNamespace

import httpx
import pytest

from app.main import app
from app.services import github_status
from app.services.github_client import GitHubClient, get_github_client
from app.services.github_links import slugify

from .fakes import FakeGitHub
from .helpers import create_project, create_story, create_subtask, get_story, me, ok, update_story

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


def test_branch_url_without_repo_requires_settings_or_a_name(client):
    project = create_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/stories",
        json={"title": "URL without repo", "github_branch": f"{REPO_URL}/tree/alice/login-page"},
    )
    assert response.status_code == 400
    assert "or enter a branch name" in response.json()["detail"]


@pytest.mark.parametrize("title", ["!!!", "登录页面"])
def test_title_without_slug_has_no_suggestion(client, title):
    project = create_project(client)
    story = create_story(client, project["id"], title)
    assert get_story(client, story["id"])["suggested_branch"] == ""
    assert update_story(client, story["id"], github_branch="alice/manual")["github_branch"] == "alice/manual"


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


def test_branch_is_optional_and_subtasks_have_independent_branches(client):
    project = project_with_repo(client)
    parent = create_story(client, project["id"], "Parent")
    assert parent["github_branch"] is None
    child = create_subtask(client, parent["id"], "API", github_branch=f"{REPO_URL}/tree/alice/api")
    other = create_subtask(client, parent["id"], "Documentation")
    assert child["github_branch"] == "alice/api"
    assert other["github_branch"] is None
    assert update_story(client, child["id"], github_branch=None)["github_branch"] is None
    assert get_story(client, parent["id"])["github_branch"] is None


def test_branch_save_does_not_query_github_and_checks_length(client):
    github = FakeGitHub()
    github.fail = True
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Long branch", github_branch="x" * 255)
    assert story["github_branch"] == "x" * 255
    assert client.put(f"/api/stories/{story['id']}", json={"github_branch": "x" * 256}).status_code == 400
    assert github.calls == []


def test_live_status_requires_repository(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Missing repo", github_branch="alice/missing")
    assert client.get(f"/api/stories/{story['id']}/github").status_code == 400
    assert get_story(client, story["id"])["github_branch"] == "alice/missing"


def test_live_status_checks_membership_before_cache_or_configuration(client, other_client, make_client):
    github = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Private branch", github_branch="alice/login-page")
    path = f"/api/stories/{story['id']}/github"
    ok(client.get(path))
    calls = len(github.calls)
    assert other_client.get(path).status_code == 403
    assert make_client().get(path).status_code == 401
    assert len(github.calls) == calls
    app.dependency_overrides[get_github_client] = lambda: None
    assert client.get(path).status_code == 503
    assert other_client.get(path).status_code == 403


@pytest.mark.parametrize("exists", [True, False])
def test_live_status_without_pr(client, exists):
    github = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    branch = "alice/login-page" if exists else "alice/unknown"
    story = create_story(client, project["id"], "No PR", github_branch=branch)
    status = ok(client.get(f"/api/stories/{story['id']}/github"))
    assert status["branch_exists"] is exists
    assert status["pull_request"] is None


@pytest.mark.parametrize("state,merged", [("open", False), ("closed", False), ("closed", True)])
def test_live_status_uses_latest_created_pr(client, state, merged):
    github = FakeGitHub()
    github.pulls["alice/login-page"] = [
        {"number": 1, "created_at": "2026-10-01T00:00:00Z", "state": "closed"},
        {"number": 2, "created_at": "2026-10-02T00:00:00Z", "state": state,
         "merged_at": "2026-10-03T00:00:00Z" if merged else None},
    ]
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Latest PR", github_branch="alice/login-page")
    pull = ok(client.get(f"/api/stories/{story['id']}/github"))["pull_request"]
    assert (pull["number"], pull["state"], pull["merged"]) == (2, state, merged)


def test_cache_expires_after_five_minutes(client, monkeypatch):
    moment = [1000]
    monkeypatch.setattr(github_status, "time", SimpleNamespace(monotonic=lambda: moment[0]))
    github = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Cache expiry", github_branch="alice/login-page")
    path = f"/api/stories/{story['id']}/github"
    assert ok(client.get(path))["branch_exists"] is True
    github.branches.clear()
    moment[0] += 299
    assert ok(client.get(path))["branch_exists"] is True
    assert len(github.calls) == 2
    moment[0] += 1
    assert ok(client.get(path))["branch_exists"] is False
    assert len(github.calls) == 4


def test_cache_is_separate_for_branch_and_repository(client):
    github = FakeGitHub()
    app.dependency_overrides[get_github_client] = lambda: github
    project = project_with_repo(client)
    story = create_story(client, project["id"], "Cache keys", github_branch="alice/login-page")
    path = f"/api/stories/{story['id']}/github"
    ok(client.get(path))
    update_story(client, story["id"], github_branch="alice/unknown")
    assert ok(client.get(path))["branch_exists"] is False
    assert len(github.calls) == 4
    new_repo = "https://github.com/byu-ml-capstone/other"
    ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": new_repo}))
    github.repo = "other"
    status = ok(client.get(path))
    assert status["branch_url"] == f"{new_repo}/tree/alice/unknown"
    assert len(github.calls) == 6
    ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": None}))
    assert client.get(path).status_code == 400


def test_github_client_only_calls_api_host_with_parsed_values(client):
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    with httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_github_client] = lambda: GitHubClient("fake-token", http=http)
        project = project_with_repo(client)
        story = create_story(client, project["id"], "HTTP lookup", github_branch=f"{REPO_URL}/tree/alice/login-page")
        ok(client.get(f"/api/stories/{story['id']}/github"))
    assert len(requests) == 2
    assert all(request.url.scheme == "https" and request.url.host == "api.github.com" for request in requests)
    assert requests[0].url.path == "/repos/byu-ml-capstone/dinnerbell/pulls"
    assert requests[0].url.params["head"] == "byu-ml-capstone:alice/login-page"
    assert requests[0].url.params["state"] == "all"
    assert requests[0].url.params["sort"] == "created"
    assert requests[0].url.params["direction"] == "desc"
    assert requests[1].url.path == "/repos/byu-ml-capstone/dinnerbell/branches/alice/login-page"


@pytest.mark.parametrize("kind", ["http", "network", "json", "redirect"])
def test_github_http_failures_return_502_without_caching(client, kind):
    requests = []

    def respond(request):
        requests.append(request)
        if kind == "network":
            raise httpx.ConnectError("unreachable", request=request)
        if kind == "json":
            return httpx.Response(200, text="not json")
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "https://example.com/"})
        return httpx.Response(403)

    with httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_github_client] = lambda: GitHubClient("fake-token", http=http)
        project = project_with_repo(client)
        story = create_story(client, project["id"], "HTTP failure", github_branch="alice/failure")
        path = f"/api/stories/{story['id']}/github"
        assert client.get(path).status_code == 502
        assert client.get(path).status_code == 502
    assert len(requests) == 2
    assert all(request.url.host == "api.github.com" for request in requests)
