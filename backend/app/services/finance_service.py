import uuid
from datetime import date, datetime, timezone
from sqlalchemy import func
from app.extensions import db
from app.models.finance import RentInvoice, Payment, Expense, SecurityDeposit
from app.models.tenant import RoomAllocation
from app.models.room_bed import Room, Bed
from app.models.property import PGProperty
from app.middleware.error_handlers import APIException
from app.services.notification_service import send_notification
from app.services.audit_service import log_audit

def generate_invoice_for_allocation(allocation_id: int, month: int, year: int, electricity: float = 0.0, food: float = 0.0, late_fee: float = 0.0):
    allocation = db.session.get(RoomAllocation, allocation_id)
    if not allocation or not allocation.is_active:
        raise APIException("Active room allocation not found.", status_code=404, code="NOT_FOUND")

    # Check for duplicate invoice for same month/year
    existing = RentInvoice.query.filter_by(
        allocation_id=allocation_id,
        billing_month=month,
        billing_year=year
    ).first()
    if existing:
        raise APIException(f"Invoice for month {month}/{year} already exists for this tenant (Invoice #{existing.invoice_number}).", status_code=409, code="CONFLICT")

    base_rent = float(allocation.monthly_rent_agreed)
    total_due = base_rent + electricity + food + late_fee
    due_date_val = date(year, month, min(5, 28))  # default 5th of month

    inv_num = f"INV-{year}{month:02d}-{uuid.uuid4().hex[:6].upper()}"
    invoice = RentInvoice(
        invoice_number=inv_num,
        property_id=allocation.bed.room.property_id,
        tenant_id=allocation.tenant_id,
        allocation_id=allocation_id,
        billing_month=month,
        billing_year=year,
        base_rent_amount=base_rent,
        electricity_charges=electricity,
        food_charges=food,
        late_fee_amount=late_fee,
        total_amount_due=total_due,
        amount_paid=0.00,
        due_date=due_date_val,
        status="PENDING"
    )
    db.session.add(invoice)
    db.session.commit()

    send_notification(
        allocation.tenant.user_id,
        "New Rent Invoice",
        f"Rent invoice ({inv_num}) for {month}/{year} has been generated. Amount due: Rs. {total_due:.2f}.",
        "RENT",
        "rent_invoices",
        invoice.id
    )

    return invoice

def record_payment(invoice_id: int, amount: float, method: str, transaction_ref: str = None, notes: str = None, recorded_by_user_id: int = None):
    invoice = db.session.get(RentInvoice, invoice_id)
    if not invoice:
        raise APIException("Invoice not found.", status_code=404, code="NOT_FOUND")

    if invoice.status == "PAID":
        raise APIException("This invoice is already fully paid.", status_code=400, code="ALREADY_PAID")

    pay_ref = f"PAY-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    payment = Payment(
        payment_reference=pay_ref,
        invoice_id=invoice.id,
        tenant_id=invoice.tenant_id,
        amount=amount,
        payment_method=method,
        transaction_reference=transaction_ref,
        payment_date=date.today(),
        status="COMPLETED",
        verified_by_user_id=recorded_by_user_id,
        notes=notes
    )
    db.session.add(payment)

    # Update invoice totals
    new_paid = float(invoice.amount_paid) + amount
    invoice.amount_paid = new_paid
    total_due = float(invoice.total_amount_due)

    if new_paid >= total_due:
        invoice.status = "PAID"
    elif new_paid > 0:
        invoice.status = "PARTIALLY_PAID"

    db.session.commit()

    send_notification(
        invoice.tenant.user_id,
        "Payment Recorded",
        f"Payment of Rs. {amount:.2f} for Invoice {invoice.invoice_number} recorded successfully.",
        "PAYMENT",
        "payments",
        payment.id
    )

    log_audit("RECORD_PAYMENT", "payments", payment.id, {"amount": amount, "method": method, "invoice": invoice.invoice_number}, user_id=recorded_by_user_id)
    return payment

def get_property_financial_summary(property_id: int):
    # Total billed
    billed_res = db.session.query(func.coalesce(func.sum(RentInvoice.total_amount_due), 0.00)).filter(
        RentInvoice.property_id == property_id
    ).scalar()

    # Total collected
    collected_res = db.session.query(func.coalesce(func.sum(RentInvoice.amount_paid), 0.00)).filter(
        RentInvoice.property_id == property_id
    ).scalar()

    # Total expenses
    expense_res = db.session.query(func.coalesce(func.sum(Expense.amount), 0.00)).filter(
        Expense.property_id == property_id
    ).scalar()

    total_billed = float(billed_res)
    total_collected = float(collected_res)
    total_expenses = float(expense_res)
    pending_receivables = max(0.0, total_billed - total_collected)
    net_operating_income = total_collected - total_expenses

    # Real bed stats
    prop = db.session.get(PGProperty, property_id)
    total_beds = 0
    occupied_beds = 0
    available_beds = 0

    if prop:
        for r in prop.rooms:
            if not r.is_active:
                continue
            for b in r.beds:
                total_beds += 1
                if b.status == "OCCUPIED":
                    occupied_beds += 1
                elif b.status == "AVAILABLE":
                    available_beds += 1

    occupancy_pct = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0

    return {
        "property_id": property_id,
        "total_billed": total_billed,
        "total_collected": total_collected,
        "pending_receivables": pending_receivables,
        "total_expenses": total_expenses,
        "net_operating_income": net_operating_income,
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "occupancy_percentage": occupancy_pct
    }

