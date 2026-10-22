from sqlalchemy import text

from app.database import engine

from .helpers import PASSWORD, create_project, ok, register


def test_register_sets_httponly_cookie_and_me_returns_user(make_client):
    client = make_client()
    response = client.post("/api/auth/register", json={"username": "Johnny", "name": "Johnny G", "password": PASSWORD})
    assert response.status_code == 201
    cookie = response.headers["set-cookie"]
    assert "dbpm_session=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert response.json()["username"] == "johnny"
    assert ok(client.get("/api/auth/me"))["name"] == "Johnny G"


def test_username_is_case_insensitive(make_client):
    register(make_client(), "johnny")
    response = make_client().post("/api/auth/register", json={"username": "Johnny", "name": "Other", "password": PASSWORD})
    assert response.status_code == 409


def test_register_validation(make_client):
    client = make_client()
    assert client.post("/api/auth/register", json={"username": "ab", "name": "x", "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "has space", "name": "x", "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "valid", "name": "x", "password": "short"}).status_code == 422


def test_login_and_logout(make_client):
    register(make_client(), "carol")
    client = make_client()
    bad = client.post("/api/auth/login", json={"username": "carol", "password": "wrong-password"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Invalid username or password"
    assert client.post("/api/auth/login", json={"username": "nobody", "password": PASSWORD}).status_code == 401

    good = client.post("/api/auth/login", json={"username": "CAROL", "password": PASSWORD})
    assert good.status_code == 200 and "dbpm_session=" in good.headers["set-cookie"]
    old_cookie = client.cookies.get("dbpm_session")
    assert client.get("/api/auth/me").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204
    replay = make_client()
    replay.cookies.set("dbpm_session", old_cookie)
    assert replay.get("/api/auth/me").status_code == 401


def test_every_api_route_requires_login_except_health(make_client, client):
    project = create_project(client)
    anonymous = make_client()
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get("/api/health").status_code == 200
    for path in (
        "/api/auth/me",
        "/api/users",
        "/api/projects",
        f"/api/projects/{project['id']}",
        f"/api/projects/{project['id']}/stories",
        f"/api/projects/{project['id']}/sprints",
        f"/api/projects/{project['id']}/velocity",
        f"/api/projects/{project['id']}/planning",
        f"/api/projects/{project['id']}/trash",
        "/api/trash/projects",
    ):
        assert anonymous.get(path).status_code == 401, path
    assert anonymous.post("/api/projects", json={"name": "x"}).status_code == 401


def test_x_user_id_header_is_ignored(make_client, client):
    user_id = ok(client.get("/api/auth/me"))["id"]
    anonymous = make_client()
    assert anonymous.get("/api/projects", headers={"X-User-Id": user_id}).status_code == 401


def test_password_is_hashed_with_argon2(client):
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT password_hash FROM users WHERE username = 'alice'")).scalar_one()
    assert stored.startswith("$argon2")
    assert PASSWORD not in stored


def test_users_list_requires_login_and_hides_email(client, other_client):
    users = ok(client.get("/api/users"))
    assert {user["username"] for user in users} == {"alice", "bob"}
    assert all(set(user) == {"id", "username", "name"} for user in users)
