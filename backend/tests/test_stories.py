from .helpers import (
    active_sprint,
    close_sprint,
    create_project,
    create_story,
    create_subtask,
    get_story,
    me,
    ok,
    story_titles,
    update_story,
)


def test_create_story_defaults_to_backlog(client):
    project = create_project(client)
    story = create_story(client, project["id"], "  Recipe search  ", acceptance_criteria="By ingredient", due_date="2026-12-01")
    assert story["title"] == "Recipe search"
    assert story["status"] == "backlog"
    assert story["sprint_id"] is None
    detail = get_story(client, story["id"])
    assert detail["acceptance_criteria"] == "By ingredient"
    assert detail["due_date"] == "2026-12-01"


def test_create_story_in_sprint_starts_selected(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "In sprint", sprint_id=sprint["id"])
    assert story["sprint_id"] == sprint["id"]
    assert story["status"] == "selected"
    close_sprint(client, sprint["id"])
    response = client.post(f"/api/projects/{project['id']}/stories", json={"title": "Late", "sprint_id": sprint["id"]})
    assert response.status_code == 400


def test_fibonacci_points(client):
    project = create_project(client)
    assert client.post(f"/api/projects/{project['id']}/stories", json={"title": "Four", "story_points": 4}).status_code == 422
    assert create_story(client, project["id"], "Five", story_points=5)["story_points"] == 5
    assert create_story(client, project["id"], "None", story_points=None)["story_points"] is None
    story = create_story(client, project["id"], "Later")
    assert client.put(f"/api/stories/{story['id']}", json={"story_points": 7}).status_code == 422


def test_titles_are_unique_per_project_ignoring_case_and_spaces(client):
    project = create_project(client)
    create_story(client, project["id"], "Login page")
    response = client.post(f"/api/projects/{project['id']}/stories", json={"title": "  LOGIN page "})
    assert response.status_code == 409
    assert response.json()["detail"] == "A story with this title already exists in this project"
    other = create_story(client, project["id"], "Signup page")
    assert client.put(f"/api/stories/{other['id']}", json={"title": "login PAGE"}).status_code == 409
    # Subtasks share the same namespace (CORE-6).
    assert client.post(f"/api/stories/{other['id']}/subtasks", json={"title": "Login Page"}).status_code == 409
    # Another project can reuse the title.
    second = create_project(client, "Other")
    create_story(client, second["id"], "Login page")


def test_deleted_story_title_can_be_reused(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Reusable")
    ok(client.delete(f"/api/stories/{story['id']}"))
    assert create_story(client, project["id"], "reusable")["title"] == "reusable"


def test_every_field_can_be_edited(client, other_client):
    project = create_project(client, member_ids=(me(other_client)["id"],))
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Original")
    bob = me(other_client)
    update_story(
        client,
        story["id"],
        title="Edited",
        description="New description",
        acceptance_criteria="New criteria",
        status="in_progress",
        priority="urgent",
        story_points=8,
        assignee_id=bob["id"],
        due_date="2026-12-24",
        sprint_id=sprint["id"],
        github_branch="bob/edited",
    )
    detail = get_story(client, story["id"])
    assert detail["title"] == "Edited"
    assert detail["description"] == "New description"
    assert detail["acceptance_criteria"] == "New criteria"
    assert detail["status"] == "in_progress"
    assert detail["priority"] == "urgent"
    assert detail["story_points"] == 8
    assert detail["assignee_id"] == bob["id"]
    assert detail["due_date"] == "2026-12-24"
    assert detail["sprint_id"] == sprint["id"]
    assert detail["github_branch"] == "bob/edited"
    # Clearing nullable fields.
    update_story(client, story["id"], story_points=None, assignee_id=None, due_date=None, github_branch="")
    detail = get_story(client, story["id"])
    assert detail["story_points"] is None and detail["assignee_id"] is None and detail["due_date"] is None
    assert detail["github_branch"] is None


def test_closed_sprint_stories_are_read_only(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    done = create_story(client, project["id"], "Done", sprint_id=sprint["id"])
    unfinished = create_story(client, project["id"], "Unfinished", sprint_id=sprint["id"])
    update_story(client, done["id"], status="done")
    close_sprint(client, sprint["id"])

    for field, value in (("title", "x"), ("status", "in_progress"), ("story_points", 3), ("sprint_id", None)):
        assert client.put(f"/api/stories/{done['id']}", json={field: value}).status_code == 400, field
    for field, value in (("title", "x"), ("status", "in_progress"), ("priority", "low")):
        response = client.put(f"/api/stories/{unfinished['id']}", json={field: value})
        assert response.status_code == 400, field
        assert response.json()["detail"] == "Story is in a closed sprint; move it out first"
    # Sending the current values is not a change.
    update_story(client, unfinished["id"], title="Unfinished", status="selected")
    # Comments are still allowed.
    ok(client.post(f"/api/stories/{done['id']}/comments", json={"text": "Retro note"}))
    # Moving the unfinished story out is allowed.
    assert update_story(client, unfinished["id"], sprint_id=None)["sprint_id"] is None


def test_subtasks(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    parent = create_story(client, project["id"], "Parent", sprint_id=sprint["id"])
    subtask = create_subtask(client, parent["id"], "Child", story_points=2)
    assert subtask["sprint_id"] == sprint["id"]
    assert subtask["parent_story_id"] == parent["id"]
    assert subtask["status"] == "selected"
    assert client.post(f"/api/stories/{subtask['id']}/subtasks", json={"title": "Grandchild"}).status_code == 400
    detail = get_story(client, parent["id"])
    assert [item["title"] for item in detail["subtasks"]] == ["Child"]
    assert detail["subtask_count"] == 1
    assert get_story(client, subtask["id"])["parent_title"] == "Parent"


def test_board_only_shows_this_project(client):
    first = create_project(client, "A")
    second = create_project(client, "B")
    sprint = active_sprint(client, first["id"])
    create_story(client, first["id"], "A backlog")
    create_story(client, first["id"], "A sprint", sprint_id=sprint["id"])
    create_story(client, second["id"], "B backlog")
    board = ok(client.get(f"/api/sprints/{sprint['id']}/board"))
    titles = {story["title"] for column in board["columns"].values() for story in column}
    assert titles == {"A backlog", "A sprint"}
    assert story_titles(board["columns"]["backlog"]) == {"A backlog"}
    assert story_titles(board["columns"]["selected"]) == {"A sprint"}
    assert board["read_only"] is False


def test_story_endpoints_check_membership(client, other_client):
    project = create_project(client)
    story = create_story(client, project["id"], "Private")
    assert other_client.get(f"/api/stories/{story['id']}").status_code == 403
    assert other_client.put(f"/api/stories/{story['id']}", json={"title": "x"}).status_code == 403
    assert other_client.delete(f"/api/stories/{story['id']}").status_code == 403
    assert other_client.post(f"/api/stories/{story['id']}/comments", json={"text": "x"}).status_code == 403
    assert other_client.post(f"/api/stories/{story['id']}/subtasks", json={"title": "x"}).status_code == 403
    assert other_client.post(f"/api/projects/{project['id']}/stories", json={"title": "x"}).status_code == 403
    assert client.get("/api/stories/story-missing").status_code == 404


def test_comments(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Commented")
    comment = ok(client.post(f"/api/stories/{story['id']}/comments", json={"text": "Looks good"}))
    assert comment["author_name"] == "Alice Anders"
    assert [item["text"] for item in get_story(client, story["id"])["comments"]] == ["Looks good"]
    assert client.post(f"/api/stories/{story['id']}/comments", json={"text": ""}).status_code == 422


def test_list_stories_sorted_by_priority_then_age(client):
    project = create_project(client)
    create_story(client, project["id"], "Low", priority="low")
    create_story(client, project["id"], "Urgent", priority="urgent")
    create_story(client, project["id"], "Medium old")
    create_story(client, project["id"], "Medium new")
    titles = [story["title"] for story in ok(client.get(f"/api/projects/{project['id']}/stories"))]
    assert titles == ["Urgent", "Medium old", "Medium new", "Low"]
