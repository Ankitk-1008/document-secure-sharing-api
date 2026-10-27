def get_token(client, email):
    client.post("/api/v1/auth/register", json={"full_name":"Test User","email":email,"password":"StrongPass123!"})
    r = client.post("/api/v1/auth/login", data={"username":email,"password":"StrongPass123!"})
    return r.json()["access_token"]

def test_upload_and_list_document(client):
    token = get_token(client, "uploader@example.com")
    r = client.post("/api/v1/documents/upload", headers={"Authorization":f"Bearer {token}"}, files={"file":("hello.txt", b"hello world", "text/plain")})
    assert r.status_code == 201, r.text
    assert r.json()["original_filename"] == "hello.txt"
    listed = client.get("/api/v1/documents", headers={"Authorization":f"Bearer {token}"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
