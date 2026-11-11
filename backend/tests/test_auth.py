from tests.conftest import get_auth_token

def test_user_registration_success(client):
    payload = {
        "email": "newtenant@example.com",
        "password": "Password@123",
        "full_name": "New Tenant",
        "phone": "9812345678",
        "role": "TENANT",
        "emergency_contact_name": "Parent",
        "emergency_contact_phone": "9812345679"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "newtenant@example.com"

def test_duplicate_registration_fails(client, seeded_users):
    payload = {
        "email": "tenant@test.com",
        "password": "Password@123",
        "full_name": "Duplicate User",
        "phone": "9812345678",
        "role": "TENANT"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False

def test_login_invalid_password(client, seeded_users):
    res = client.post("/api/auth/login", json={"email": "tenant@test.com", "password": "WrongPassword"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_rbac_access_forbidden(client, seeded_users):
    token = get_auth_token(client, "tenant@test.com", "Tenant@123")
    headers = {"Authorization": f"Bearer {token}"}
    # Tenant cannot access admin analytics
    res = client.get("/api/admin/analytics", headers=headers)
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
