from .helpers import (
    active_sprint,
    close_sprint,
    create_project,
    create_sprint,
    create_story,
    create_subtask,
    days,
    get_story,
    ok,
    today,
    update_story,
)


def test_cannot_move_into_closed_or_foreign_sprint(client):
    project = create_project(client)
    other = create_project(client, "Other")
    closed = active_sprint(client, project["id"])
    close_sprint(client, closed["id"])
    foreign = active_sprint(client, other["id"])
    story = create_story(client, project["id"], "Story")
    assert client.put(f"/api/stories/{story['id']}", json={"sprint_id": closed["id"]}).status_code == 400
    assert client.put(f"/api/stories/{story['id']}", json={"sprint_id": foreign["id"]}).status_code == 404
    assert get_story(client, story["id"])["sprint_id"] is None


def test_unfinished_story_can_leave_closed_sprint_and_keeps_status(client):
    project = create_project(client)
    old = active_sprint(client, project["id"], "Old")
    upcoming = create_sprint(client, project["id"], today() + days(10), today() + days(20), "Next")
    story = create_story(client, project["id"], "Carry me", sprint_id=old["id"])
    update_story(client, story["id"], status="in_progress")
    close_sprint(client, old["id"])
    moved = update_story(client, story["id"], sprint_id=upcoming["id"])
    assert moved["sprint_id"] == upcoming["id"]
    assert moved["status"] == "in_progress"
    board = ok(client.get(f"/api/sprints/{upcoming['id']}/board"))
    assert [item["title"] for item in board["columns"]["in_progress"]] == ["Carry me"]


def test_done_story_stays_in_closed_sprint(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Finished", sprint_id=sprint["id"])
    update_story(client, story["id"], status="done")
    close_sprint(client, sprint["id"])
    assert client.put(f"/api/stories/{story['id']}", json={"sprint_id": None}).status_code == 400


def test_parent_moves_with_unfinished_subtasks_only(client):
    project = create_project(client)
    first = active_sprint(client, project["id"], "Sprint 1")
    second = active_sprint(client, project["id"], "Sprint 2")
    parent = create_story(client, project["id"], "Parent", sprint_id=first["id"])
    done_child = create_subtask(client, parent["id"], "Done child")
    open_child = create_subtask(client, parent["id"], "Open child")
    update_story(client, done_child["id"], status="done")
    update_story(client, open_child["id"], status="in_progress")
    update_story(client, parent["id"], sprint_id=second["id"])
    assert get_story(client, parent["id"])["sprint_id"] == second["id"]
    assert get_story(client, open_child["id"])["sprint_id"] == second["id"]
    assert get_story(client, done_child["id"])["sprint_id"] == first["id"]


def test_subtask_cannot_move_on_its_own(client):
    project = create_project(client)
    first = active_sprint(client, project["id"], "Sprint 1")
    second = active_sprint(client, project["id"], "Sprint 2")
    parent = create_story(client, project["id"], "Parent", sprint_id=first["id"])
    child = create_subtask(client, parent["id"], "Child")
    response = client.put(f"/api/stories/{child['id']}", json={"sprint_id": second["id"]})
    assert response.status_code == 400
    assert response.json()["detail"] == "Subtasks move with their parent story"


def test_status_rules_when_moving(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Story")
    assert story["status"] == "backlog"
    assert update_story(client, story["id"], sprint_id=sprint["id"])["status"] == "selected"
    update_story(client, story["id"], status="in_progress")
    assert update_story(client, story["id"], sprint_id=None)["status"] == "backlog"
    # An explicit status in the same request wins (board drag into a column).
    assert update_story(client, story["id"], sprint_id=sprint["id"], status="in_progress")["status"] == "in_progress"


def test_move_unfinished_out_of_closed_sprint(client):
    project = create_project(client)
    old = active_sprint(client, project["id"], "Old")
    target = create_sprint(client, project["id"], today() + days(10), today() + days(20), "Next")
    finished = create_story(client, project["id"], "Finished", sprint_id=old["id"])
    update_story(client, finished["id"], status="done")
    first = create_story(client, project["id"], "Open 1", sprint_id=old["id"])
    second = create_story(client, project["id"], "Open 2", sprint_id=old["id"])
    child = create_subtask(client, first["id"], "Open child")
    close_sprint(client, old["id"])
    result = ok(client.post(f"/api/sprints/{old['id']}/move-unfinished", json={"target_sprint_id": target["id"]}))
    assert result["moved"] == 2
    for story in (first, second, child):
        assert get_story(client, story["id"])["sprint_id"] == target["id"]
    assert get_story(client, finished["id"])["sprint_id"] == old["id"]
    to_backlog = ok(client.post(f"/api/sprints/{target['id']}/move-unfinished", json={"target_sprint_id": None}))
    assert to_backlog["moved"] == 2
    assert get_story(client, first["id"])["sprint_id"] is None


def test_bulk_move_is_all_or_nothing(client):
    project = create_project(client)
    closed = active_sprint(client, project["id"], "Closed")
    target = active_sprint(client, project["id"], "Target")
    done = create_story(client, project["id"], "Done", sprint_id=closed["id"])
    update_story(client, done["id"], status="done")
    close_sprint(client, closed["id"])
    free = create_story(client, project["id"], "Free")
    response = client.post(
        f"/api/projects/{project['id']}/stories/move",
        json={"story_ids": [free["id"], done["id"]], "sprint_id": target["id"]},
    )
    assert response.status_code == 400
    assert get_story(client, free["id"])["sprint_id"] is None

    result = ok(
        client.post(f"/api/projects/{project['id']}/stories/move", json={"story_ids": [free["id"]], "sprint_id": target["id"]})
    )
    assert [story["sprint_id"] for story in result["stories"]] == [target["id"]]


def test_sprint_history_and_carryover(client):
    project = create_project(client)
    s1 = active_sprint(client, project["id"], "Sprint 1")
    s2 = active_sprint(client, project["id"], "Sprint 2")
    s3 = active_sprint(client, project["id"], "Sprint 3")
    story = create_story(client, project["id"], "Slipping", sprint_id=s1["id"])
    update_story(client, story["id"], sprint_id=s2["id"])
    update_story(client, story["id"], sprint_id=s3["id"])
    detail = get_story(client, story["id"])
    assert [entry["sprint_name"] for entry in detail["sprint_history"]] == ["Sprint 1", "Sprint 2", "Sprint 3"]
    assert detail["carryover_count"] == 2
    listed = {item["id"]: item for item in ok(client.get(f"/api/projects/{project['id']}/stories"))}
    assert listed[story["id"]]["carryover_count"] == 2


def test_moving_out_of_planned_sprint_is_not_carryover(client):
    project = create_project(client)
    planned = create_sprint(client, project["id"], today() + days(5), today() + days(10))
    other = create_sprint(client, project["id"], today() + days(11), today() + days(20))
    story = create_story(client, project["id"], "Replanned", sprint_id=planned["id"])
    update_story(client, story["id"], sprint_id=other["id"])
    assert get_story(client, story["id"])["carryover_count"] == 0


def test_capacity_warning(client):
    project = create_project(client)
    past = active_sprint(client, project["id"], "Past")
    done = create_story(client, project["id"], "Done", sprint_id=past["id"], story_points=5)
    update_story(client, done["id"], status="done")
    close_sprint(client, past["id"])
    upcoming = create_sprint(client, project["id"], today() + days(1), today() + days(10), "Upcoming")
    create_story(client, project["id"], "Big", sprint_id=upcoming["id"], story_points=8)
    planning = ok(client.get(f"/api/projects/{project['id']}/planning"))
    column = next(item for item in planning["sprints"] if item["sprint"]["id"] == upcoming["id"])
    assert column["capacity_warning"] == "⚠ 8 pts planned vs 5 avg velocity"
    assert ok(client.get(f"/api/sprints/{upcoming['id']}"))["capacity_warning"] == column["capacity_warning"]
    assert ok(client.get(f"/api/sprints/{past['id']}"))["capacity_warning"] is None


def test_planning_view(client):
    project = create_project(client)
    closed = active_sprint(client, project["id"], "Closed")
    open_story = create_story(client, project["id"], "Left behind", sprint_id=closed["id"])
    close_sprint(client, closed["id"])
    planned = create_sprint(client, project["id"], today() + days(3), today() + days(9), "Planned")
    create_story(client, project["id"], "Planned story", sprint_id=planned["id"])
    parent = create_story(client, project["id"], "Backlog parent")
    create_subtask(client, parent["id"], "Hidden subtask")
    planning = ok(client.get(f"/api/projects/{project['id']}/planning"))
    assert [story["title"] for story in planning["backlog"]] == ["Backlog parent"]
    assert planning["backlog"][0]["subtask_count"] == 1
    assert [item["sprint"]["name"] for item in planning["sprints"]] == ["Planned"]
    assert [(item["sprint"]["name"], item["unfinished_count"]) for item in planning["closed_with_unfinished"]] == [("Closed", 1)]
    assert open_story["id"]


def test_move_warns_when_blocker_is_later(client):
    project = create_project(client)
    early = create_sprint(client, project["id"], today() + days(1), today() + days(5), "Early")
    late = create_sprint(client, project["id"], today() + days(6), today() + days(10), "Late")
    blocker = create_story(client, project["id"], "Blocker", sprint_id=late["id"])
    blocked = create_story(client, project["id"], "Blocked")
    ok(client.post(f"/api/stories/{blocker['id']}/blocks/{blocked['id']}", json={}))
    result = update_story(client, blocked["id"], sprint_id=early["id"])
    assert result["sprint_id"] == early["id"]
    assert result["warnings"] == ["'Blocked' is blocked by 'Blocker', which is planned for a later sprint (Late)"]


def test_old_assign_endpoint_is_gone(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    story = create_story(client, project["id"], "Story")
    response = client.put(f"/api/sprints/{sprint['id']}/stories/{story['id']}", json={"sprint_id": sprint["id"]})
    assert response.status_code in (404, 405)
