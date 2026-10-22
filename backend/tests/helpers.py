from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

TZ = ZoneInfo("America/Denver")
PASSWORD = "password123"


def at(day: date, hour: int = 12) -> datetime:
    """A moment on `day` in the app's timezone."""
    return datetime.combine(day, time(hour), tzinfo=TZ)


def today() -> date:
    from app.services import clock

    return clock.today()


def days(n: int) -> timedelta:
    return timedelta(days=n)


def ok(response, status: int = 200):
    assert response.status_code == status, f"{response.status_code}: {response.text}"
    return response.json() if response.content else None


def register(client: TestClient, username: str, name: str | None = None, password: str = PASSWORD) -> dict:
    return ok(client.post("/api/auth/register", json={"username": username, "name": name or username.title(), "password": password}), 201)


def me(client: TestClient) -> dict:
    return ok(client.get("/api/auth/me"))


def create_project(client: TestClient, name: str = "DinnerBell", member_ids: tuple[str, ...] = (), **fields) -> dict:
    return ok(client.post("/api/projects", json={"name": name, "team_member_ids": list(member_ids), **fields}))


def add_member(client: TestClient, project_id: str, user_id: str) -> dict:
    return ok(client.post(f"/api/projects/{project_id}/team", json={"user_id": user_id}))


def create_sprint(client: TestClient, project_id: str, start: date, end: date, name: str | None = None, goal: str = "") -> dict:
    payload = {"start_date": start.isoformat(), "end_date": end.isoformat(), "goal": goal}
    if name:
        payload["name"] = name
    return ok(client.post(f"/api/projects/{project_id}/sprints", json=payload))


def active_sprint(client: TestClient, project_id: str, name: str = "Sprint A", start_offset: int = -2, length: int = 10) -> dict:
    start = today() + days(start_offset)
    return create_sprint(client, project_id, start, start + days(length - 1), name)


def create_story(client: TestClient, project_id: str, title: str, **fields) -> dict:
    return ok(client.post(f"/api/projects/{project_id}/stories", json={"title": title, **fields}))


def create_subtask(client: TestClient, parent_id: str, title: str, **fields) -> dict:
    return ok(client.post(f"/api/stories/{parent_id}/subtasks", json={"title": title, **fields}))


def update_story(client: TestClient, story_id: str, expect: int = 200, **fields):
    return ok(client.put(f"/api/stories/{story_id}", json=fields), expect)


def get_story(client: TestClient, story_id: str) -> dict:
    return ok(client.get(f"/api/stories/{story_id}"))


def close_sprint(client: TestClient, sprint_id: str, notes: str = "") -> dict:
    return ok(client.post(f"/api/sprints/{sprint_id}/close", json={"notes": notes}))


def story_titles(stories: list[dict]) -> set[str]:
    return {story["title"] for story in stories}
