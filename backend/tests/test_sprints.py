from .helpers import active_sprint, close_sprint, create_project, create_sprint, days, ok, today


def test_several_sprints_can_be_active(client):
    project = create_project(client)
    active_sprint(client, project["id"], "One")
    active_sprint(client, project["id"], "Two")
    sprints = ok(client.get(f"/api/projects/{project['id']}/sprints"))
    assert [sprint["status"] for sprint in sprints] == ["active", "active"]


def test_status_comes_from_dates(client):
    project = create_project(client)
    planned = create_sprint(client, project["id"], today() + days(1), today() + days(10))
    assert planned["status"] == "planned"
    moved = ok(client.put(f"/api/sprints/{planned['id']}", json={"start_date": today().isoformat()}))
    assert moved["status"] == "active"


def test_overdue_until_closed(client):
    project = create_project(client)
    sprint = create_sprint(client, project["id"], today() - days(10), today() - days(1))
    assert sprint["status"] == "active"
    assert sprint["is_overdue"] is True
    close_sprint(client, sprint["id"])
    closed = ok(client.get(f"/api/sprints/{sprint['id']}"))
    assert closed["status"] == "closed"
    assert closed["is_overdue"] is False
    assert closed["closed_by_id"] is not None


def test_dates_are_required_and_ordered(client):
    project = create_project(client)
    path = f"/api/projects/{project['id']}/sprints"
    assert client.post(path, json={"end_date": today().isoformat()}).status_code == 422
    assert client.post(path, json={"start_date": today().isoformat()}).status_code == 422
    backwards = {"start_date": today().isoformat(), "end_date": (today() - days(1)).isoformat()}
    assert client.post(path, json=backwards).status_code == 422
    sprint = active_sprint(client, project["id"])
    assert client.put(f"/api/sprints/{sprint['id']}", json={"end_date": "2000-01-01"}).status_code == 422


def test_default_names_count_every_sprint(client):
    project = create_project(client)
    first = create_sprint(client, project["id"], today(), today() + days(5))
    assert first["name"] == "Sprint 1"
    ok(client.delete(f"/api/sprints/{first['id']}"))
    second = create_sprint(client, project["id"], today(), today() + days(5))
    assert second["name"] == "Sprint 2"


def test_closed_sprint_cannot_be_edited_or_closed_again(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    close_sprint(client, sprint["id"], notes="Done")
    assert client.put(f"/api/sprints/{sprint['id']}", json={"name": "x"}).status_code == 400
    assert client.post(f"/api/sprints/{sprint['id']}/close", json={}).status_code == 400
    assert ok(client.get(f"/api/sprints/{sprint['id']}/board"))["read_only"] is True
    assert ok(client.get(f"/api/sprints/{sprint['id']}"))["notes"] == "Done"


def test_sprint_endpoints_check_membership(client, other_client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    for method, path in (
        ("get", f"/api/sprints/{sprint['id']}"),
        ("get", f"/api/sprints/{sprint['id']}/board"),
        ("get", f"/api/sprints/{sprint['id']}/metrics"),
        ("put", f"/api/sprints/{sprint['id']}"),
        ("post", f"/api/sprints/{sprint['id']}/close"),
        ("delete", f"/api/sprints/{sprint['id']}"),
        ("post", f"/api/projects/{project['id']}/sprints"),
    ):
        body = {"start_date": today().isoformat(), "end_date": today().isoformat()}
        kwargs = {"json": body} if method in ("put", "post") else {}
        assert getattr(other_client, method)(path, **kwargs).status_code == 403, path
