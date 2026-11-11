from tests.conftest import get_auth_token

def test_search_properties(client, seeded_users):
    res = client.get("/api/properties/search?city=Bengaluru")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["name"] == "Alpha PG"

def test_owner_create_property(client, seeded_users):
    token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Beta Executive PG",
        "property_type": "GIRLS",
        "address_line1": "45 MG Road",
        "locality": "Central",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560002",
        "latitude": 12.9750,
        "longitude": 77.6000,
        "description": "Premium ladies PG with high security",
        "contact_phone": "9876543211",
        "contact_email": "owner@test.com"
    }
    res = client.post("/api/properties", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.get_json()["success"] is True

def test_compare_properties(client, seeded_users):
    pid = seeded_users["property_id"]
    res = client.get(f"/api/properties/compare?ids={pid}")
    assert res.status_code == 200
    assert len(res.get_json()["data"]) == 1
