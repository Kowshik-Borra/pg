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

def test_reject_missing_coordinates(client, seeded_users):
    token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "No Coordinates PG",
        "property_type": "BOYS",
        "address_line1": "100 Test Ave",
        "locality": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560066",
        "description": "Property with missing coordinates"
    }
    res = client.post("/api/properties", json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert "coordinates" in data["error"]["message"].lower()

def test_reject_out_of_range_coordinates(client, seeded_users):
    token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Invalid Coordinates PG",
        "property_type": "BOYS",
        "address_line1": "100 Test Ave",
        "locality": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560066",
        "latitude": 150.0,
        "longitude": 200.0,
        "description": "Property with out of range coordinates"
    }
    res = client.post("/api/properties", json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False

def test_reject_zero_placeholder_coordinates(client, seeded_users):
    token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Zero Placeholder PG",
        "property_type": "BOYS",
        "address_line1": "100 Test Ave",
        "locality": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560066",
        "latitude": 0.0,
        "longitude": 0.0,
        "description": "Property with (0,0) coordinates"
    }
    res = client.post("/api/properties", json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False

def test_food_filter_search(client, seeded_users):
    # Alpha PG currently has no food menus added, so has_food=true returns 0 results
    res_true = client.get("/api/properties/search?has_food=true")
    assert res_true.status_code == 200
    data_true = res_true.get_json()["data"]
    assert data_true["total"] == 0

    # has_food=false returns Alpha PG
    res_false = client.get("/api/properties/search?has_food=false")
    assert res_false.status_code == 200
    data_false = res_false.get_json()["data"]
    assert data_false["total"] >= 1

def test_public_and_owner_map_visibility(client, seeded_users):
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")

    # 1. Public markers: Alpha PG is verified, so it appears
    pub_res = client.get("/api/maps/markers")
    assert pub_res.status_code == 200
    pub_markers = pub_res.get_json()["data"]
    assert any(m["id"] == seeded_users["property_id"] for m in pub_markers)

    # 2. Owner markers: includes owner's properties
    owner_res = client.get("/api/maps/owner-properties", headers={"Authorization": f"Bearer {owner_token}"})
    assert owner_res.status_code == 200
    owner_markers = owner_res.get_json()["data"]
    assert any(m["id"] == seeded_users["property_id"] for m in owner_markers)

