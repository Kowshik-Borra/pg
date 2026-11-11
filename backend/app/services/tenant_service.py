import uuid
from datetime import datetime, date, timezone
from app.extensions import db
from app.models.tenant import Tenant, RoomAllocation, VisitorLog
from app.models.room_bed import Room, Bed
from app.models.finance import SecurityDeposit, RentInvoice
from app.models.booking import Booking, BookingHistory
from app.middleware.error_handlers import APIException
from app.services.notification_service import send_notification
from app.services.audit_service import log_audit

def check_in_tenant(user_id: int, bed_id: int, check_in_date_val: date, monthly_rent: float, deposit_paid: float, booking_id: int = None, performed_by_user_id: int = None):
    # Lock the bed record with row-level locking
    bed = db.session.query(Bed).filter(Bed.id == bed_id).with_for_update().one_or_none()
    if not bed:
        raise APIException("Bed not found.", status_code=404, code="NOT_FOUND")

    # If it was RESERVED for this booking, that is allowed; or if AVAILABLE
    if bed.status not in ["AVAILABLE", "RESERVED"]:
        raise APIException(f"Cannot check in to bed with status '{bed.status}'. Bed is not available.", status_code=409, code="CONFLICT")

    tenant = Tenant.query.filter_by(user_id=user_id).first()
    if not tenant:
        raise APIException("Tenant profile does not exist. Please complete tenant details first.", status_code=400, code="PROFILE_MISSING")

    # Check if tenant already has an active allocation
    active_alloc = RoomAllocation.query.filter_by(tenant_id=tenant.id, is_active=True).first()
    if active_alloc:
        raise APIException("Tenant already has an active room allocation in the system.", status_code=409, code="CONFLICT")

    room = bed.room
    prop = room.property

    allocation = RoomAllocation(
        tenant_id=tenant.id,
        bed_id=bed.id,
        check_in_date=check_in_date_val,
        monthly_rent_agreed=monthly_rent,
        security_deposit_paid=deposit_paid,
        is_active=True
    )
    db.session.add(allocation)
    db.session.flush()

    # Bed is now OCCUPIED
    bed.status = "OCCUPIED"
    bed.last_status_change = datetime.now(timezone.utc)
    bed.notes = f"Occupied by {tenant.user.full_name} (Tenant ID: {tenant.id})"

    # Create security deposit record
    sec_deposit = SecurityDeposit(
        tenant_id=tenant.id,
        property_id=prop.id,
        amount_deposited=deposit_paid,
        deposit_date=check_in_date_val,
        refund_status="HELD"
    )
    db.session.add(sec_deposit)

    # If linked to a booking, mark COMPLETED
    if booking_id:
        booking = Booking.query.get(booking_id)
        if booking:
            booking.status = "COMPLETED"
            hist = BookingHistory(
                booking_id=booking.id,
                from_status="APPROVED",
                to_status="COMPLETED",
                changed_by_user_id=performed_by_user_id,
                change_reason="Tenant checked in successfully."
            )
            db.session.add(hist)

    # Generate initial first-month invoice
    inv_num = f"INV-{check_in_date_val.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    invoice = RentInvoice(
        invoice_number=inv_num,
        property_id=prop.id,
        tenant_id=tenant.id,
        allocation_id=allocation.id,
        billing_month=check_in_date_val.month,
        billing_year=check_in_date_val.year,
        base_rent_amount=monthly_rent,
        total_amount_due=monthly_rent,
        amount_paid=0.00,
        due_date=check_in_date_val,
        status="PENDING"
    )
    db.session.add(invoice)

    db.session.commit()

    send_notification(
        user_id,
        "Check-In Complete",
        f"Welcome to {prop.name}! You are allocated Room {room.room_number}, {bed.bed_label}.",
        "CHECK_IN",
        "room_allocations",
        allocation.id
    )

    log_audit("TENANT_CHECK_IN", "room_allocations", allocation.id, {"room": room.room_number, "bed": bed.bed_label}, user_id=performed_by_user_id)
    return allocation

def check_out_tenant(allocation_id: int, check_out_date_val: date, refund_amount: float, deduction_amount: float, deduction_reason: str, needs_maintenance: bool = False, performed_by_user_id: int = None):
    allocation = RoomAllocation.query.get(allocation_id)
    if not allocation or not allocation.is_active:
        raise APIException("Active allocation not found.", status_code=404, code="NOT_FOUND")

    bed = allocation.bed
    prop = bed.room.property

    allocation.is_active = False
    allocation.check_out_date = check_out_date_val

    # Update bed status
    bed.status = "MAINTENANCE" if needs_maintenance else "AVAILABLE"
    bed.last_status_change = datetime.now(timezone.utc)
    bed.notes = "Vacated upon tenant checkout"

    # Settle security deposit record
    sec_deposit = SecurityDeposit.query.filter_by(tenant_id=allocation.tenant_id, property_id=prop.id, refund_status="HELD").first()
    if sec_deposit:
        sec_deposit.deductions_amount = deduction_amount
        sec_deposit.deduction_reason = deduction_reason
        sec_deposit.refund_amount = refund_amount
        sec_deposit.refund_date = check_out_date_val
        sec_deposit.refund_status = "FULLY_REFUNDED" if deduction_amount == 0 else "PARTIALLY_REFUNDED"

    db.session.commit()

    send_notification(
        allocation.tenant.user_id,
        "Check-Out Complete",
        f"You have been successfully checked out from {prop.name}. We hope you had a pleasant stay.",
        "CHECK_OUT",
        "room_allocations",
        allocation.id
    )

    log_audit("TENANT_CHECK_OUT", "room_allocations", allocation.id, {"refund": refund_amount, "deduction": deduction_amount}, user_id=performed_by_user_id)
    return allocation
