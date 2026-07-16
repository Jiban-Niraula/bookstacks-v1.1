def test_register_creates_member_role_user(client):
    resp = client.post("/api/auth/register", json={
        "username": "newuser", "email": "newuser@test.local", "password": "password123",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["role"] == "member"
    assert "token" in body
    assert "password" not in body["user"]


def test_register_rejects_missing_fields(client):
    resp = client.post("/api/auth/register", json={"username": "onlyusername"})
    assert resp.status_code == 400


def test_register_rejects_short_password(client):
    resp = client.post("/api/auth/register", json={
        "username": "shortpw", "email": "shortpw@test.local", "password": "123",
    })
    assert resp.status_code == 400


def test_register_rejects_duplicate_username(client):
    payload = {"username": "dupe", "email": "dupe1@test.local", "password": "password123"}
    client.post("/api/auth/register", json=payload)
    payload["email"] = "dupe2@test.local"
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_rejects_duplicate_email(client):
    client.post("/api/auth/register", json={
        "username": "userA", "email": "same@test.local", "password": "password123",
    })
    resp = client.post("/api/auth/register", json={
        "username": "userB", "email": "same@test.local", "password": "password123",
    })
    assert resp.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "loginuser", "email": "loginuser@test.local", "password": "password123",
    })
    resp = client.post("/api/auth/login", json={"username": "loginuser", "password": "password123"})
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "loginuser2", "email": "loginuser2@test.local", "password": "password123",
    })
    resp = client.post("/api/auth/login", json={"username": "loginuser2", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_username(client):
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


def test_login_error_message_does_not_leak_user_existence(client):
    """Unknown username and wrong password must return the identical error
    message -- otherwise an attacker can enumerate valid usernames."""
    client.post("/api/auth/register", json={
        "username": "realuser", "email": "realuser@test.local", "password": "password123",
    })
    wrong_pw = client.post("/api/auth/login", json={"username": "realuser", "password": "wrongpass"})
    unknown_user = client.post("/api/auth/login", json={"username": "ghost", "password": "whatever"})
    assert wrong_pw.get_json()["error"] == unknown_user.get_json()["error"]


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, make_headers, staff):
    resp = client.get("/api/auth/me", headers=make_headers(staff))
    assert resp.status_code == 200
    assert resp.get_json()["username"] == staff.username
