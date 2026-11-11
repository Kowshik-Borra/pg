from datetime import date
from tests.conftest import get_auth_token
from app.extensions import db
from app.models.tenant import RoomAllocation

def test_finance_invoice_and_payment(client, seeded_users):
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {owner_token}"}

    tenant_id = seeded_users["tenant_id"]
    bed_id = seeded_users["bed2_id"]

    # Create allocation directly
    alloc = RoomAllocation(
        tenant_id=1,
        bed_id=bed_id,
        check_in_date=date(2026, 1, 1),
        monthly_rent_agreed=10000.00,
        security_deposit_paid=15000.00,
        is_active=True
    )
    db.session.add(alloc)
    db.session.commit()

    # Generate invoice
    res_inv = client.post("/api/finance/invoices", json={
        "allocation_id": alloc.id,
        "billing_month": 4,
        "billing_year": 2026,
        "electricity_charges": 500.00
    }, headers=headers)

    assert res_inv.status_code == 201
    inv_data = res_inv.get_json()["data"]
    inv_id = inv_data["id"]
    assert inv_data["total_amount_due"] == 10500.00
    assert inv_data["status"] == "PENDING"

    # Record partial payment
    res_pay = client.post("/api/finance/payments", json={
        "invoice_id": inv_id,
        "amount": 5000.00,
        "payment_method": "UPI",
        "transaction_reference": "UPI/123456789"
    }, headers=headers)

    assert res_pay.status_code == 201

    # Record second payment to fully pay
    res_pay2 = client.post("/api/finance/payments", json={
        "invoice_id": inv_id,
        "amount": 5500.00,
        "payment_method": "CASH"
    }, headers=headers)

    assert res_pay2.status_code == 201
