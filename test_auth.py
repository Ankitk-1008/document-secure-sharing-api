def register(client, email="user@example.com"):
    return client.post("/api/v1/auth/register", json={"full_name":"Test User","email":email,"password":"StrongPass123!"})

def test_register_and_login(client):
    r = register(client)
    assert r.status_code == 201, r.text
    login = client.post("/api/v1/auth/login", data={"username":"user@example.com","password":"StrongPass123!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization":f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

def test_duplicate_registration(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409

def test_protected_route_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
