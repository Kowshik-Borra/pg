from tests.conftest import get_auth_token
from app.extensions import db
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
    bed = db.session.get(Bed, bed_id)
    assert bed.status == "RESERVED"

    # 3. Prevent duplicate booking of same reserved bed
    res_duplicate = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-01"
    }, headers={"Authorization": f"Bearer {tenant_token}"})

    assert res_duplicate.status_code == 409

def test_cross_owner_booking_approval_forbidden(client, seeded_users):
    tenant_token = get_auth_token(client, "tenant@test.com", "Tenant@123")

    # 1. Register a distinct second owner
    res_reg = client.post("/api/auth/register", json={
        "email": "owner2@test.com",
        "password": "Password@123",
        "full_name": "Second Owner",
        "phone": "9811122233",
        "role": "OWNER",
        "business_name": "Second Enterprise Stays"
    })
    assert res_reg.status_code == 201
    owner2_token = res_reg.get_json()["data"]["access_token"]

    prop_id = seeded_users["property_id"]
    room_id = seeded_users["room_id"]
    bed_id = seeded_users["bed2_id"]

    # Customer books bed2 on Alpha PG (owned by Owner 1)
    res_bk = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-05",
        "sharing_type": "DOUBLE"
    }, headers={"Authorization": f"Bearer {tenant_token}"})
    assert res_bk.status_code == 201
    booking_id = res_bk.get_json()["data"]["id"]

    # Owner 2 attempts to approve Owner 1's booking -> Must be 403 FORBIDDEN
    res_cross = client.post(f"/api/bookings/{booking_id}/approve", json={
        "remarks": "Cross owner unauthorized attempt"
    }, headers={"Authorization": f"Bearer {owner2_token}"})

    assert res_cross.status_code == 403
    assert res_cross.get_json()["success"] is False

def test_tenant_check_in_validation_and_atomicity(client, seeded_users):
    tenant_token = get_auth_token(client, "tenant@test.com", "Tenant@123")
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")

    prop_id = seeded_users["property_id"]
    room_id = seeded_users["room_id"]
    bed_id = seeded_users["bed1_id"]
    tenant_id = seeded_users["tenant_id"]

    # 1. Customer books bed1
    res_bk = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-01",
        "sharing_type": "DOUBLE"
    }, headers={"Authorization": f"Bearer {tenant_token}"})
    assert res_bk.status_code == 201
    booking_id = res_bk.get_json()["data"]["id"]

    # 2. Owner approves
    client.post(f"/api/bookings/{booking_id}/approve", json={"remarks": "Approved"}, headers={"Authorization": f"Bearer {owner_token}"})

    # 3. Check-in with mismatched user fails
    res_fail = client.post("/api/tenants/check-in", json={
        "user_id": 9999,  # Mismatched user
        "bed_id": bed_id,
        "monthly_rent_agreed": 10000.0,
        "security_deposit_paid": 15000.0,
        "booking_id": booking_id
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res_fail.status_code in [400, 404]

    # 4. Valid check-in succeeds atomically
    res_ok = client.post("/api/tenants/check-in", json={
        "user_id": tenant_id,
        "bed_id": bed_id,
        "monthly_rent_agreed": 10000.0,
        "security_deposit_paid": 15000.0,
        "booking_id": booking_id
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res_ok.status_code == 201

    bed = db.session.get(Bed, bed_id)
    assert bed.status == "OCCUPIED"

    # 5. Duplicate check-in fails (already has active allocation)
    res_dup = client.post("/api/tenants/check-in", json={
        "user_id": tenant_id,
        "bed_id": seeded_users["bed2_id"],
        "monthly_rent_agreed": 10000.0,
        "security_deposit_paid": 15000.0
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res_dup.status_code == 409

def test_reservation_expiry_releases_bed(client, seeded_users):
    from datetime import datetime, timezone, timedelta
    from app.extensions import db
    from app.models.booking import Booking

    tenant_token = get_auth_token(client, "tenant@test.com", "Tenant@123")
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")

    prop_id = seeded_users["property_id"]
    room_id = seeded_users["room_id"]
    bed_id = seeded_users["bed2_id"]

    # Book and approve bed2
    res_bk = client.post("/api/bookings", json={
        "property_id": prop_id,
        "room_id": room_id,
        "bed_id": bed_id,
        "preferred_move_in_date": "2026-12-01",
        "sharing_type": "DOUBLE"
    }, headers={"Authorization": f"Bearer {tenant_token}"})
    booking_id = res_bk.get_json()["data"]["id"]

    client.post(f"/api/bookings/{booking_id}/approve", json={"remarks": "Approved"}, headers={"Authorization": f"Bearer {owner_token}"})
    assert db.session.get(Bed, bed_id).status == "RESERVED"

    # Force reservation to be in the past
    booking = db.session.get(Booking, booking_id)
    booking.reservation_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.session.commit()

    # Trigger maintenance expiry endpoint
    res_exp = client.post("/api/bookings/expire-reservations")
    assert res_exp.status_code == 200
    assert res_exp.get_json()["data"]["expired_count"] >= 1

    # Verify bed returned to AVAILABLE and booking is EXPIRED
    bed = db.session.get(Bed, bed_id)
    assert bed.status == "AVAILABLE"
    assert db.session.get(Booking, booking_id).status == "EXPIRED"

    # Idempotent re-run
    res_exp2 = client.post("/api/bookings/expire-reservations")
    assert res_exp2.status_code == 200
    assert res_exp2.get_json()["data"]["expired_count"] == 0

