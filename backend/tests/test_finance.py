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

    # Record an expense
    prop_id = seeded_users["property_id"]
    res_exp = client.post("/api/finance/expenses", json={
        "property_id": prop_id,
        "category": "ELECTRICITY",
        "amount": 1200.00,
        "description": "Common area electricity bill"
    }, headers=headers)
    assert res_exp.status_code == 201

    # Get property financial summary
    res_sum = client.get(f"/api/finance/summary/property/{prop_id}", headers=headers)
    assert res_sum.status_code == 200
    sum_data = res_sum.get_json()["data"]
    assert sum_data["total_collected"] == 10500.00
    assert sum_data["total_expenses"] == 1200.00
    assert sum_data["net_operating_income"] == 9300.00

    # Generate PDF receipt
    res_pdf = client.get(f"/api/reports/invoices/{inv_id}/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == "application/pdf"

    # Generate Excel financial report
    res_excel = client.get(f"/api/reports/properties/{prop_id}/excel", headers=headers)
    assert res_excel.status_code == 200
    assert "spreadsheetml" in res_excel.mimetype or "octet-stream" in res_excel.mimetype

def test_admin_analytics_endpoint(client, seeded_users):
    admin_token = get_auth_token(client, "admin@test.com", "Admin@123")
    res = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "users" in data
    assert "properties" in data
    assert "operations" in data

def test_tenant_checkout_releases_bed(client, seeded_users):
    owner_token = get_auth_token(client, "owner@test.com", "Owner@123")
    headers = {"Authorization": f"Bearer {owner_token}"}
    bed_id = seeded_users["bed1_id"]

    # Allocate bed
    alloc = RoomAllocation(
        tenant_id=1,
        bed_id=bed_id,
        check_in_date=date(2026, 1, 1),
        monthly_rent_agreed=10000.00,
        security_deposit_paid=15000.00,
        is_active=True
    )
    db.session.add(alloc)
    from app.models.room_bed import Bed
    bed = db.session.get(Bed, bed_id)
    bed.status = "OCCUPIED"
    db.session.commit()

    # Checkout tenant
    res_out = client.post(f"/api/tenants/allocations/{alloc.id}/check-out", json={
        "check_out_date": "2026-05-01",
        "refund_amount": 14000.00,
        "deductions_amount": 1000.00,
        "deduction_reason": "Room cleaning fee",
        "needs_maintenance": False
    }, headers=headers)

    assert res_out.status_code == 200
    assert not alloc.is_active
    # Bed released to AVAILABLE
    assert db.session.get(Bed, bed_id).status == "AVAILABLE"

