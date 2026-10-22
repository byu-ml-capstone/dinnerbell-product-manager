from sqlalchemy import text

from app.database import engine

from .helpers import (
    active_sprint,
    close_sprint,
    create_project,
    create_story,
    create_subtask,
    get_story,
    ok,
    story_titles,
    update_story,
)

TABLES = ("projects", "sprints", "stories", "dependencies", "comments", "sprint_messages")


def row_counts() -> dict[str, int]:
    with engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in TABLES}


def restore(client, batch_id, expect=200):
    return ok(client.post(f"/api/trash/{batch_id}/restore"), expect)


def test_deleted_story_is_hidden_everywhere_and_restores_with_children(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Parent", sprint_id=sprint["id"], story_points=5)
    subtask = create_subtask(client, story["id"], "Child")
    other = create_story(client, project["id"], "Other", sprint_id=sprint["id"])
    ok(client.post(f"/api/stories/{story['id']}/comments", json={"text": "note"}))
    ok(client.post(f"/api/stories/{story['id']}/blocks/{other['id']}", json={}))

    deleted = ok(client.delete(f"/api/stories/{story['id']}"))
    assert deleted["counts"] == {"stories": 1, "comments": 1, "dependencies": 1}
    assert story_titles(ok(client.get(f"/api/projects/{project['id']}/stories"))) == {"Other"}
    board = ok(client.get(f"/api/sprints/{sprint['id']}/board"))
    assert {item["title"] for column in board["columns"].values() for item in column} == {"Other"}
    assert get_story(client, other["id"])["blocked_by"] == []
    assert client.get(f"/api/stories/{story['id']}").status_code == 404
    assert client.get(f"/api/stories/{subtask['id']}").status_code == 404
    assert ok(client.get(f"/api/projects/{project['id']}/summary"))["total_stories"] == 1
    with engine.connect() as connection:
        assert connection.execute(text("SELECT deleted_at FROM stories WHERE id = :id"), {"id": story["id"]}).scalar_one()

    restored = restore(client, deleted["batch_id"])
    assert restored["restored"] == {"stories": 2, "comments": 1, "dependencies": 1}
    detail = get_story(client, story["id"])
    assert detail["story_points"] == 5 and detail["sprint_id"] == sprint["id"]
    assert [item["id"] for item in detail["subtasks"]] == [subtask["id"]]
    assert [item["text"] for item in detail["comments"]] == ["note"]
    assert get_story(client, other["id"])["blocked_by"] == [story["id"]]
    assert ok(client.get(f"/api/projects/{project['id']}/trash")) == []


def test_child_deleted_earlier_stays_deleted(client):
    project = create_project(client)
    parent = create_story(client, project["id"], "Parent")
    child = create_subtask(client, parent["id"], "Child")
    ok(client.delete(f"/api/stories/{child['id']}"))
    parent_batch = ok(client.delete(f"/api/stories/{parent['id']}"))
    restore(client, parent_batch["batch_id"])
    assert get_story(client, parent["id"])["subtasks"] == []
    assert client.get(f"/api/stories/{child['id']}").status_code == 404


def test_deleting_a_sprint_deletes_its_stories(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    for title in ("One", "Two", "Three"):
        create_story(client, project["id"], title, sprint_id=sprint["id"])
    create_story(client, project["id"], "Backlog")
    deleted = ok(client.delete(f"/api/sprints/{sprint['id']}"))
    assert deleted["counts"]["stories"] == 3
    assert story_titles(ok(client.get(f"/api/projects/{project['id']}/stories"))) == {"Backlog"}
    assert client.get(f"/api/sprints/{sprint['id']}").status_code == 404
    restore(client, deleted["batch_id"])
    board = ok(client.get(f"/api/sprints/{sprint['id']}/board"))
    assert story_titles(board["columns"]["selected"]) == {"One", "Two", "Three"}


def test_deleting_and_restoring_a_project(client, other_client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    create_story(client, project["id"], "Story", sprint_id=sprint["id"])
    deleted = ok(client.delete(f"/api/projects/{project['id']}"))
    assert ok(client.get("/api/projects")) == []
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    trash = ok(client.get("/api/trash/projects"))
    assert [item["root_label"] for item in trash] == ["DinnerBell"]
    assert ok(other_client.get("/api/trash/projects")) == []
    assert other_client.post(f"/api/trash/{deleted['batch_id']}/restore").status_code == 403
    restore(client, deleted["batch_id"])
    assert [item["id"] for item in ok(client.get("/api/projects"))] == [project["id"]]
    assert len(ok(client.get(f"/api/projects/{project['id']}/sprints"))) == 1
    assert story_titles(ok(client.get(f"/api/projects/{project['id']}/stories"))) == {"Story"}


def test_restore_refuses_title_clash(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Login")
    deleted = ok(client.delete(f"/api/stories/{story['id']}"))
    create_story(client, project["id"], "login")
    response = client.post(f"/api/trash/{deleted['batch_id']}/restore")
    assert response.status_code == 409
    assert "Rename it" in response.json()["detail"]
    assert client.get(f"/api/stories/{story['id']}").status_code == 404


def test_story_restored_alone_goes_to_backlog_when_sprint_is_still_deleted(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Orphan", sprint_id=sprint["id"])
    story_batch = ok(client.delete(f"/api/stories/{story['id']}"))
    ok(client.delete(f"/api/sprints/{sprint['id']}"))
    restore(client, story_batch["batch_id"])
    detail = get_story(client, story["id"])
    assert detail["sprint_id"] is None
    assert detail["status"] == "backlog"


def test_subtask_needs_parent_restored_first(client):
    project = create_project(client)
    parent = create_story(client, project["id"], "Parent")
    child = create_subtask(client, parent["id"], "Child")
    child_batch = ok(client.delete(f"/api/stories/{child['id']}"))
    ok(client.delete(f"/api/stories/{parent['id']}"))
    response = client.post(f"/api/trash/{child_batch['batch_id']}/restore")
    assert response.status_code == 409
    assert response.json()["detail"] == "Restore the parent story first"


def test_nothing_is_ever_hard_deleted(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    a = create_story(client, project["id"], "A", sprint_id=sprint["id"])
    b = create_story(client, project["id"], "B", sprint_id=sprint["id"])
    ok(client.post(f"/api/stories/{a['id']}/blocks/{b['id']}", json={}))
    ok(client.post(f"/api/stories/{a['id']}/comments", json={"text": "x"}))
    ok(client.post(f"/api/sprints/{sprint['id']}/messages", json={"text": "hello"}), 201)
    before = row_counts()
    batches = [
        ok(client.delete(f"/api/stories/{a['id']}/blocks/{b['id']}")),
        ok(client.delete(f"/api/stories/{a['id']}")),
        ok(client.delete(f"/api/sprints/{sprint['id']}")),
        ok(client.delete(f"/api/projects/{project['id']}")),
    ]
    assert row_counts() == before
    for batch in reversed(batches):
        restore(client, batch["batch_id"])
        assert row_counts() == before


def test_deleted_closed_sprint_leaves_velocity_until_restored(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Done", sprint_id=sprint["id"], story_points=5)
    update_story(client, story["id"], status="done")
    close_sprint(client, sprint["id"])
    assert [item["velocity"] for item in ok(client.get(f"/api/projects/{project['id']}/velocity"))["sprints"]] == [5]
    deleted = ok(client.delete(f"/api/sprints/{sprint['id']}"))
    assert ok(client.get(f"/api/projects/{project['id']}/velocity"))["sprints"] == []
    restore(client, deleted["batch_id"])
    assert [item["velocity"] for item in ok(client.get(f"/api/projects/{project['id']}/velocity"))["sprints"]] == [5]


def test_stories_in_closed_sprint_cannot_be_deleted_alone(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Locked", sprint_id=sprint["id"])
    close_sprint(client, sprint["id"])
    assert client.delete(f"/api/stories/{story['id']}").status_code == 400


def test_trash_lists_batches_and_restoring_twice_fails(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Gone")
    create_subtask(client, story["id"], "Gone child")
    deleted = ok(client.delete(f"/api/stories/{story['id']}"))
    trash = ok(client.get(f"/api/projects/{project['id']}/trash"))
    assert len(trash) == 1
    item = trash[0]
    assert item["root_type"] == "story" and item["root_label"] == "Gone"
    assert item["counts"] == {"stories": 1}
    assert item["deleted_by"] == "Alice Anders"
    restore(client, deleted["batch_id"])
    assert client.post(f"/api/trash/{deleted['batch_id']}/restore").status_code == 409
