from .helpers import create_project, create_sprint, create_story, get_story, ok, today, update_story, days


def link(client, blocker_id, blocked_id, reason="", expect=200):
    return ok(client.post(f"/api/stories/{blocker_id}/blocks/{blocked_id}", json={"reason": reason}), expect)


def graph(client, project_id, **params):
    return ok(client.get(f"/api/projects/{project_id}/dependency-graph", params=params))


def test_adding_a_blocker_never_changes_status(client):
    project = create_project(client)
    blocker = create_story(client, project["id"], "Blocker")
    blocked = create_story(client, project["id"], "Blocked")
    update_story(client, blocker["id"], status="done")
    update_story(client, blocked["id"], status="in_progress")
    result = link(client, blocker["id"], blocked["id"], reason="Needs the API")
    assert result["reason"] == "Needs the API"
    assert result["blocker_title"] == "Blocker"
    assert get_story(client, blocked["id"])["status"] == "in_progress"


def test_blocked_story_can_change_status_with_blockers(client):
    project = create_project(client)
    blocker = create_story(client, project["id"], "Blocker")
    blocked = create_story(client, project["id"], "Blocked")
    link(client, blocker["id"], blocked["id"])
    update_story(client, blocked["id"], status="blocked")
    assert update_story(client, blocked["id"], status="in_progress")["status"] == "in_progress"


def test_duplicate_and_self_links(client):
    project = create_project(client)
    a = create_story(client, project["id"], "A")
    b = create_story(client, project["id"], "B")
    link(client, a["id"], b["id"])
    assert client.post(f"/api/stories/{a['id']}/blocks/{b['id']}", json={}).status_code == 409
    assert client.post(f"/api/stories/{a['id']}/blocks/{a['id']}", json={}).status_code == 400


def test_cycles_are_rejected(client):
    project = create_project(client)
    a = create_story(client, project["id"], "A")
    b = create_story(client, project["id"], "B")
    c = create_story(client, project["id"], "C")
    link(client, a["id"], b["id"])
    link(client, b["id"], c["id"])
    response = client.post(f"/api/stories/{c['id']}/blocks/{a['id']}", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "This would create a cycle: C → A → B → C"
    assert get_story(client, a["id"])["blocked_by"] == []


def test_links_cannot_cross_projects(client):
    first = create_project(client, "One")
    second = create_project(client, "Two")
    a = create_story(client, first["id"], "A")
    b = create_story(client, second["id"], "B")
    assert client.post(f"/api/stories/{a['id']}/blocks/{b['id']}", json={}).status_code == 400


def test_removed_link_can_be_added_again(client):
    project = create_project(client)
    a = create_story(client, project["id"], "A")
    b = create_story(client, project["id"], "B")
    link(client, a["id"], b["id"])
    removed = ok(client.delete(f"/api/stories/{a['id']}/blocks/{b['id']}"))
    assert removed["batch_id"]
    assert get_story(client, b["id"])["blocked_by"] == []
    link(client, a["id"], b["id"])
    assert get_story(client, b["id"])["blocked_by"] == [a["id"]]
    trash = ok(client.get(f"/api/projects/{project['id']}/trash"))
    assert [item["root_label"] for item in trash] == ["Link: A blocks B"]


def test_graph_starts_empty_and_shows_only_linked_stories(client):
    project = create_project(client)
    assert graph(client, project["id"]) == {"nodes": [], "edges": []}
    a = create_story(client, project["id"], "A")
    b = create_story(client, project["id"], "B")
    create_story(client, project["id"], "Unlinked")
    link(client, a["id"], b["id"], reason="why")
    data = graph(client, project["id"])
    assert {node["title"] for node in data["nodes"]} == {"A", "B"}
    assert [(edge["source"], edge["target"], edge["reason"]) for edge in data["edges"]] == [(a["id"], b["id"], "why")]


def test_graph_filters(client):
    project = create_project(client)
    sprint = create_sprint(client, project["id"], today(), today() + days(9))
    a = create_story(client, project["id"], "A", sprint_id=sprint["id"])
    b = create_story(client, project["id"], "B")
    c = create_story(client, project["id"], "C")
    d = create_story(client, project["id"], "D")
    link(client, b["id"], a["id"])
    link(client, c["id"], d["id"])
    in_sprint = graph(client, project["id"], sprint_id=sprint["id"])
    assert {node["title"] for node in in_sprint["nodes"]} == {"A", "B"}
    update_story(client, c["id"], status="done")
    without_done = graph(client, project["id"], include_done="false")
    assert {node["title"] for node in without_done["nodes"]} == {"A", "B"}


def test_order_warning_when_blocker_is_planned_later(client):
    project = create_project(client)
    first = create_sprint(client, project["id"], today() + days(10), today() + days(20), "Sprint 1")
    second = create_sprint(client, project["id"], today() + days(25), today() + days(35), "Sprint 2")
    blocker = create_story(client, project["id"], "API", sprint_id=second["id"])
    blocked = create_story(client, project["id"], "UI", sprint_id=first["id"])
    result = link(client, blocker["id"], blocked["id"])
    assert result["warnings"] == ["'UI' is blocked by 'API', which is planned for a later sprint (Sprint 2)"]
    assert graph(client, project["id"])["edges"][0]["order_warning"] is True
    assert get_story(client, blocked["id"])["warnings"]


def test_all_blockers_done_hint(client):
    project = create_project(client)
    blocker = create_story(client, project["id"], "Blocker")
    blocked = create_story(client, project["id"], "Blocked")
    link(client, blocker["id"], blocked["id"])
    update_story(client, blocked["id"], status="blocked")
    assert get_story(client, blocked["id"])["all_blockers_done"] is False
    update_story(client, blocker["id"], status="done")
    detail = get_story(client, blocked["id"])
    assert detail["all_blockers_done"] is True
    assert detail["status"] == "blocked"


def test_deleting_a_story_removes_it_from_the_graph_until_restored(client):
    project = create_project(client)
    a = create_story(client, project["id"], "A")
    b = create_story(client, project["id"], "B")
    link(client, a["id"], b["id"])
    deleted = ok(client.delete(f"/api/stories/{a['id']}"))
    assert graph(client, project["id"]) == {"nodes": [], "edges": []}
    assert get_story(client, b["id"])["blocked_by"] == []
    ok(client.post(f"/api/trash/{deleted['batch_id']}/restore"))
    data = graph(client, project["id"])
    assert {node["title"] for node in data["nodes"]} == {"A", "B"}
    assert len(data["edges"]) == 1
