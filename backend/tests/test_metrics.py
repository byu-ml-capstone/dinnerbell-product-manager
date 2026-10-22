from datetime import date, timedelta

from sqlalchemy import text

from app.database import engine

from .helpers import (
    active_sprint,
    at,
    close_sprint,
    create_project,
    create_sprint,
    create_story,
    create_subtask,
    ok,
    update_story,
)

MONDAY = date(2026, 11, 2)


def events(story_id: str) -> list[tuple[str, str | None, str | None]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT event_type, from_value, to_value FROM story_events WHERE story_id = :id ORDER BY created_at"),
            {"id": story_id},
        )
        return [tuple(row) for row in rows]


def metrics(client, sprint_id: str) -> dict:
    return ok(client.get(f"/api/sprints/{sprint_id}/metrics"))


def test_velocity_is_points_and_unpointed_count_as_zero(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    for title, points in (("Three", 3), ("Five", 5), ("Unpointed", None)):
        story = create_story(client, project["id"], title, sprint_id=sprint["id"], story_points=points)
        update_story(client, story["id"], status="done")
    create_story(client, project["id"], "Not done", sprint_id=sprint["id"], story_points=8)
    result = close_sprint(client, sprint["id"])
    assert result["velocity"] == 8
    assert result["unpointed_done_stories"] == 1
    assert result["completed_stories"] == 3
    assert result["incomplete_stories"] == 1


def test_velocity_is_zero_when_nothing_has_points(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    for title in ("One", "Two"):
        story = create_story(client, project["id"], title, sprint_id=sprint["id"])
        update_story(client, story["id"], status="done")
    assert close_sprint(client, sprint["id"])["velocity"] == 0


def test_subtask_points_do_not_count(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    parent = create_story(client, project["id"], "Parent", sprint_id=sprint["id"], story_points=5)
    child = create_subtask(client, parent["id"], "Child", story_points=3)
    update_story(client, parent["id"], status="done")
    update_story(client, child["id"], status="done")
    assert close_sprint(client, sprint["id"])["velocity"] == 5


def test_burndown_and_scope_change(client, travel):
    travel(at(MONDAY, 9))
    project = create_project(client)
    sprint = create_sprint(client, project["id"], MONDAY, MONDAY + timedelta(days=4))
    create_story(client, project["id"], "Five", sprint_id=sprint["id"], story_points=5)
    three = create_story(client, project["id"], "Three", sprint_id=sprint["id"], story_points=3)
    create_story(client, project["id"], "Two", sprint_id=sprint["id"], story_points=2)

    travel(at(MONDAY + timedelta(days=2), 15))  # Wednesday
    update_story(client, three["id"], status="done")
    create_story(client, project["id"], "Added Wednesday", sprint_id=sprint["id"], story_points=2)

    travel(at(MONDAY + timedelta(days=4), 12))  # Friday
    data = metrics(client, sprint["id"])
    assert data["committed_points"] == 10
    assert data["scope_added_points"] == 2
    assert data["scope_removed_points"] == 0
    assert data["completed_points"] == 3
    assert data["remaining_points"] == 9
    burndown = {point["date"]: point for point in data["burndown"]}
    assert burndown["2026-11-03"]["remaining_points"] == 10
    assert burndown["2026-11-04"]["remaining_points"] == 9
    assert burndown["2026-11-04"]["scope_change_points"] == 2
    assert burndown["2026-11-02"]["ideal_points"] == 10
    assert burndown["2026-11-06"]["ideal_points"] == 0
    assert data["days_elapsed"] == 5
    assert data["days_remaining"] == 0


def test_burndown_tuesday_and_wednesday(client, travel):
    travel(at(MONDAY, 9))
    project = create_project(client)
    sprint = create_sprint(client, project["id"], MONDAY, MONDAY + timedelta(days=4))
    create_story(client, project["id"], "Seven", sprint_id=sprint["id"], story_points=5)
    create_story(client, project["id"], "Two", sprint_id=sprint["id"], story_points=2)
    three = create_story(client, project["id"], "Three", sprint_id=sprint["id"], story_points=3)
    travel(at(MONDAY + timedelta(days=2), 15))
    update_story(client, three["id"], status="done")
    travel(at(MONDAY + timedelta(days=4), 12))
    burndown = {point["date"]: point["remaining_points"] for point in metrics(client, sprint["id"])["burndown"]}
    assert burndown["2026-11-03"] == 10
    assert burndown["2026-11-04"] == 7


def test_committed_points_saved_at_close(client, travel):
    travel(at(MONDAY, 9))
    project = create_project(client)
    sprint = create_sprint(client, project["id"], MONDAY, MONDAY + timedelta(days=4))
    create_story(client, project["id"], "A", sprint_id=sprint["id"], story_points=8)
    travel(at(MONDAY + timedelta(days=1), 9))
    create_story(client, project["id"], "Late", sprint_id=sprint["id"], story_points=5)
    travel(at(MONDAY + timedelta(days=4), 17))
    result = close_sprint(client, sprint["id"])
    assert result["committed_points"] == 8
    history = ok(client.get(f"/api/projects/{project['id']}/velocity"))
    assert history["sprints"][0]["committed_points"] == 8
    assert history["sprints"][0]["velocity"] == 0


def _closed_sprint_with_velocity(client, project_id, start: date, name: str, points: list[int]):
    sprint = create_sprint(client, project_id, start, start + timedelta(days=9), name)
    for index, value in enumerate(points):
        story = create_story(client, project_id, f"{name} story {index}", sprint_id=sprint["id"], story_points=value)
        update_story(client, story["id"], status="done")
    return sprint


def test_estimated_completion_date(client, travel):
    travel(at(date(2026, 9, 1), 9))
    project = create_project(client)
    velocities = {"Sprint 1": [5, 5], "Sprint 2": [8, 3, 1], "Sprint 3": [13, 1]}
    start = date(2026, 9, 1)
    for name, points in velocities.items():
        travel(at(start, 9))
        sprint = _closed_sprint_with_velocity(client, project["id"], start, name, points)
        travel(at(start + timedelta(days=9), 17))
        close_sprint(client, sprint["id"])
        start += timedelta(days=10)

    travel(at(date(2026, 11, 2), 9))
    current = create_sprint(client, project["id"], date(2026, 11, 2), date(2026, 11, 13))
    create_story(client, project["id"], "Remaining five", sprint_id=current["id"], story_points=5)
    create_story(client, project["id"], "Remaining one", sprint_id=current["id"], story_points=1)
    data = metrics(client, current["id"])
    assert data["points_per_day"] == 1.2
    assert data["remaining_points"] == 6
    assert data["estimated_completion_date"] == "2026-11-07"
    history = ok(client.get(f"/api/projects/{project['id']}/velocity"))
    assert [item["velocity"] for item in history["sprints"]] == [10, 12, 14]
    assert history["average_velocity_3"] == 12


def test_no_estimate_without_data(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    create_story(client, project["id"], "Open", sprint_id=sprint["id"], story_points=5)
    data = metrics(client, sprint["id"])
    assert data["estimated_completion_date"] is None
    assert data["points_per_day"] is None
    assert data["percent_complete"] == 0


def test_every_change_writes_exactly_one_event(client):
    project = create_project(client)
    first = active_sprint(client, project["id"], "First")
    second = active_sprint(client, project["id"], "Second")
    story = create_story(client, project["id"], "Tracked", story_points=3)
    assert events(story["id"]) == [("created", None, None), ("status_changed", None, "backlog"), ("points_changed", None, "3")]

    def new_events(before):
        return events(story["id"])[len(before):]

    before = events(story["id"])
    update_story(client, story["id"], status="in_progress")
    assert new_events(before) == [("status_changed", "backlog", "in_progress")]

    before = events(story["id"])
    update_story(client, story["id"], story_points=5)
    assert new_events(before) == [("points_changed", "3", "5")]

    before = events(story["id"])
    update_story(client, story["id"], sprint_id=first["id"])
    assert new_events(before) == [("sprint_changed", None, first["id"])]

    before = events(story["id"])
    ok(client.post(f"/api/projects/{project['id']}/stories/move", json={"story_ids": [story["id"]], "sprint_id": second["id"]}))
    assert new_events(before) == [("sprint_changed", first["id"], second["id"])]

    before = events(story["id"])
    close_sprint(client, second["id"])
    ok(client.post(f"/api/sprints/{second['id']}/move-unfinished", json={"target_sprint_id": first["id"]}))
    assert new_events(before) == [("sprint_changed", second["id"], first["id"])]

    before = events(story["id"])
    deleted = ok(client.delete(f"/api/stories/{story['id']}"))
    assert new_events(before) == [("deleted", None, None)]

    before = events(story["id"])
    ok(client.post(f"/api/trash/{deleted['batch_id']}/restore"))
    assert new_events(before) == [("restored", None, None)]

    before = events(story["id"])
    update_story(client, story["id"], title="Renamed", priority="low")
    assert new_events(before) == []


def test_closed_sprint_metrics_freeze_at_close(client, travel):
    travel(at(MONDAY, 9))
    project = create_project(client)
    sprint = create_sprint(client, project["id"], MONDAY, MONDAY + timedelta(days=4))
    later = create_sprint(client, project["id"], MONDAY + timedelta(days=7), MONDAY + timedelta(days=11), "Later")
    done = create_story(client, project["id"], "Done", sprint_id=sprint["id"], story_points=5)
    create_story(client, project["id"], "Unfinished", sprint_id=sprint["id"], story_points=3)
    travel(at(MONDAY + timedelta(days=3), 10))
    update_story(client, done["id"], status="done")
    travel(at(MONDAY + timedelta(days=4), 16))
    close_sprint(client, sprint["id"])
    travel(at(MONDAY + timedelta(days=4), 17))
    ok(client.post(f"/api/sprints/{sprint['id']}/move-unfinished", json={"target_sprint_id": later["id"]}))

    data = metrics(client, sprint["id"])
    assert data["completed_points"] == 5
    assert data["remaining_points"] == 3
    assert data["scope_removed_points"] == 0
    assert data["burndown"][-1]["remaining_points"] == 3
    assert data["percent_complete"] == 62.5
    assert data["estimated_completion_date"] is None
