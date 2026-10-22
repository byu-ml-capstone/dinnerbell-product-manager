from .helpers import active_sprint, add_member, create_project, create_story, me, ok, update_story


def test_create_list_and_get_project(client, other_client):
    bob = me(other_client)
    project = create_project(client, "DinnerBell", (bob["id"],), description="Meal planner")
    assert {member["username"] for member in project["members"]} == {"alice", "bob"}
    assert project["github_repo_url"] is None
    assert [item["id"] for item in ok(client.get("/api/projects"))] == [project["id"]]
    assert ok(other_client.get(f"/api/projects/{project['id']}"))["name"] == "DinnerBell"


def test_non_member_gets_403(client, other_client):
    project = create_project(client)
    for path in ("", "/summary", "/stories", "/sprints", "/velocity", "/planning", "/trash", "/dependency-graph"):
        assert other_client.get(f"/api/projects/{project['id']}{path}").status_code == 403, path
    assert ok(other_client.get("/api/projects")) == []
    assert other_client.put(f"/api/projects/{project['id']}", json={"name": "x"}).status_code == 403
    assert other_client.delete(f"/api/projects/{project['id']}").status_code == 403


def test_unknown_project_is_404(client):
    assert client.get("/api/projects/proj-missing").status_code == 404


def test_update_project_and_repo_url(client):
    project = create_project(client)
    updated = ok(
        client.put(
            f"/api/projects/{project['id']}",
            json={"name": "Renamed", "github_repo_url": "https://github.com/byu-ml-capstone/dinnerbell.git/"},
        )
    )
    assert updated["name"] == "Renamed"
    assert updated["github_repo_url"] == "https://github.com/byu-ml-capstone/dinnerbell"
    assert client.put(f"/api/projects/{project['id']}", json={"github_repo_url": "https://gitlab.com/x/y"}).status_code == 422
    cleared = ok(client.put(f"/api/projects/{project['id']}", json={"github_repo_url": None}))
    assert cleared["github_repo_url"] is None


def test_add_and_remove_members(client, other_client):
    project = create_project(client)
    bob = me(other_client)
    project = add_member(client, project["id"], bob["id"])
    assert len(project["members"]) == 2
    story = create_story(client, project["id"], "Assigned to Bob", assignee_id=bob["id"])

    removed = ok(client.delete(f"/api/projects/{project['id']}/team/{bob['id']}"))
    assert {member["username"] for member in removed["members"]} == {"alice"}
    assert ok(client.get(f"/api/stories/{story['id']}"))["assignee_id"] is None
    assert other_client.get(f"/api/projects/{project['id']}").status_code == 403

    alice = me(client)
    assert client.delete(f"/api/projects/{project['id']}/team/{alice['id']}").status_code == 400


def test_assignee_must_be_member(client, other_client):
    project = create_project(client)
    bob = me(other_client)
    response = client.post(f"/api/projects/{project['id']}/stories", json={"title": "x", "assignee_id": bob["id"]})
    assert response.status_code == 400


def test_summary_lists_every_active_sprint(client):
    project = create_project(client)
    first = active_sprint(client, project["id"], "Sprint A")
    second = active_sprint(client, project["id"], "Sprint B")
    story = create_story(client, project["id"], "Done thing", sprint_id=first["id"])
    update_story(client, story["id"], status="done")
    summary = ok(client.get(f"/api/projects/{project['id']}/summary"))
    assert {sprint["id"] for sprint in summary["active_sprints"]} == {first["id"], second["id"]}
    assert summary["counts"]["done"] == 1
    assert summary["total_stories"] == 1
