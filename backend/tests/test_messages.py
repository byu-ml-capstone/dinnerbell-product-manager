from .helpers import active_sprint, add_member, close_sprint, create_project, create_story, get_story, me, ok


def post(client, sprint_id, text, parent=None, expect=201):
    return ok(client.post(f"/api/sprints/{sprint_id}/messages", json={"text": text, "parent_message_id": parent}), expect)


def board(client, sprint_id, **params):
    return ok(client.get(f"/api/sprints/{sprint_id}/messages", params=params))


def test_posts_and_replies(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    first = post(client, sprint["id"], "First topic")
    second = post(client, sprint["id"], "Second topic")
    reply = post(client, sprint["id"], "A reply", parent=first["id"])
    messages = board(client, sprint["id"])
    assert [message["text"] for message in messages] == ["Second topic", "First topic"]
    assert [item["text"] for item in messages[1]["replies"]] == ["A reply"]
    assert messages[1]["author_name"] == "Alice Anders"
    assert client.post(
        f"/api/sprints/{sprint['id']}/messages", json={"text": "nested", "parent_message_id": reply["id"]}
    ).status_code == 400
    assert second["parent_message_id"] is None


def test_reply_must_be_in_the_same_sprint(client):
    project = create_project(client)
    first = active_sprint(client, project["id"], "One")
    second = active_sprint(client, project["id"], "Two")
    topic = post(client, first["id"], "Topic")
    response = client.post(f"/api/sprints/{second['id']}/messages", json={"text": "x", "parent_message_id": topic["id"]})
    assert response.status_code == 400


def test_only_the_author_can_edit_or_delete(client, other_client):
    project = create_project(client)
    add_member(client, project["id"], me(other_client)["id"])
    sprint = active_sprint(client, project["id"])
    message = post(client, sprint["id"], "Mine")
    assert other_client.put(f"/api/sprint-messages/{message['id']}", json={"text": "hijack"}).status_code == 403
    assert other_client.delete(f"/api/sprint-messages/{message['id']}").status_code == 403
    edited = ok(client.put(f"/api/sprint-messages/{message['id']}", json={"text": "Mine, edited"}))
    assert edited["text"] == "Mine, edited"
    assert edited["edited_at"] is not None


def test_deleting_a_post_takes_replies_and_can_be_restored(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    topic = post(client, sprint["id"], "Topic")
    post(client, sprint["id"], "Reply", parent=topic["id"])
    deleted = ok(client.delete(f"/api/sprint-messages/{topic['id']}"))
    assert deleted["counts"] == {"messages": 1}
    assert board(client, sprint["id"]) == []
    trash = ok(client.get(f"/api/projects/{project['id']}/trash"))
    assert trash[0]["root_type"] == "message" and trash[0]["root_label"] == "Message: Topic"
    ok(client.post(f"/api/trash/{deleted['batch_id']}/restore"))
    messages = board(client, sprint["id"])
    assert [message["text"] for message in messages] == ["Topic"]
    assert [reply["text"] for reply in messages[0]["replies"]] == ["Reply"]


def test_polling_with_since(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    first = post(client, sprint["id"], "Before")
    second = post(client, sprint["id"], "After")
    changed = board(client, sprint["id"], since=first["created_at"])
    assert [message["text"] for message in changed] == ["After"]
    ok(client.put(f"/api/sprint-messages/{first['id']}", json={"text": "Before, edited"}))
    changed = board(client, sprint["id"], since=second["created_at"])
    assert [message["text"] for message in changed] == ["Before, edited"]


def test_closed_sprints_still_take_messages(client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    close_sprint(client, sprint["id"])
    post(client, sprint["id"], "Retro notes")


def test_story_comments_are_unchanged(client):
    project = create_project(client)
    story = create_story(client, project["id"], "Story")
    ok(client.post(f"/api/stories/{story['id']}/comments", json={"text": "A comment"}))
    assert [comment["text"] for comment in get_story(client, story["id"])["comments"]] == ["A comment"]


def test_messages_check_membership(client, other_client):
    project = create_project(client)
    sprint = active_sprint(client, project["id"])
    post(client, sprint["id"], "Private")
    assert other_client.get(f"/api/sprints/{sprint['id']}/messages").status_code == 403
    assert other_client.post(f"/api/sprints/{sprint['id']}/messages", json={"text": "x"}).status_code == 403
