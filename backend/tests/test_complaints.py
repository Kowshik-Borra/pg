from datetime import date
from tests.conftest import get_auth_token
from app.extensions import db
from app.models.tenant import RoomAllocation

def test_complaints_flow(client, seeded_users):
    tenant_token = get_auth_token(client, "tenant@test.com", "Tenant@123")
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")

    # Give tenant active stay
    alloc = RoomAllocation(
        tenant_id=1,
        bed_id=seeded_users["bed2_id"],
        check_in_date=date(2026, 1, 1),
        monthly_rent_agreed=10000.00,
        security_deposit_paid=15000.00,
        is_active=True
    )
    db.session.add(alloc)
    db.session.commit()

    # Tenant submits complaint
    res_comp = client.post("/api/complaints", data={
        "category": "PLUMBING",
        "title": "Bathroom tap dripping",
        "description": "The washbasin tap has a steady drip.",
        "priority": "LOW"
    }, headers={"Authorization": f"Bearer {tenant_token}"})

    assert res_comp.status_code == 201
    comp_data = res_comp.get_json()["data"]
    comp_id = comp_data["id"]
    assert comp_data["status"] == "OPEN"

    # Owner updates complaint status to IN_PROGRESS
    res_update = client.patch(f"/api/complaints/{comp_id}/status", json={
        "status": "IN_PROGRESS",
        "note": "Plumber scheduled for tomorrow 10 AM."
    }, headers={"Authorization": f"Bearer {owner_token}"})

    assert res_update.status_code == 200
    assert res_update.get_json()["data"]["status"] == "IN_PROGRESS"

