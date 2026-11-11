from tests.conftest import get_auth_token
from app.models.room_bed import Bed

def test_booking_workflow_and_reservation(client, seeded_users):
    tenant_token = get_auth_token(client, "tenant@test.com", "Tenant@123")
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")

    prop_id = seeded_users["property_id"]
    room_id = seeded_users["room_id"]
    bed_id = seeded_users["bed1_id"]

    # 1. Customer submits booking request
    res = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-01",
        "sharing_type": "DOUBLE"
    }, headers={"Authorization": f"Bearer {tenant_token}"})

    assert res.status_code == 201
    booking_data = res.get_json()["data"]
    booking_id = booking_data["id"]
    assert booking_data["status"] == "PENDING"

    # 2. Owner approves request -> Bed becomes RESERVED
    res_approve = client.post(f"/api/bookings/{booking_id}/approve", json={
        "remarks": "Approved. Bed reserved."
    }, headers={"Authorization": f"Bearer {owner_token}"})

    assert res_approve.status_code == 200
    assert res_approve.get_json()["data"]["status"] == "APPROVED"

    # Check bed status
    bed = Bed.query.get(bed_id)
    assert bed.status == "RESERVED"

    # 3. Prevent duplicate booking of same reserved bed
    res_duplicate = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-01"
    }, headers={"Authorization": f"Bearer {tenant_token}"})

    assert res_duplicate.status_code == 409
