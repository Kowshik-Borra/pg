import uuid
from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models.booking import Booking, BookingHistory
from app.models.room_bed import Room, Bed
from app.models.property import PGProperty
from app.models.user import User
from app.middleware.error_handlers import APIException
from app.middleware.rbac import verify_property_access
from app.services.notification_service import send_notification
from app.services.audit_service import log_audit

def generate_booking_reference():
    return f"BK-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

def create_booking_request(customer_id: int, property_id: int, room_id: int, move_in_date, sharing_type: str, bed_id: int = None):
    prop = db.session.get(PGProperty, property_id)
    if not prop or not prop.is_active:
        raise APIException("Property not available for booking.", status_code=404, code="NOT_FOUND")

    room = db.session.get(Room, room_id)
    if not room or room.property_id != property_id or not room.is_active:
        raise APIException("Selected room is not valid for this property.", status_code=400, code="VALIDATION_ERROR")

    # If specific bed specified, verify
    target_bed = None
    if bed_id:
        target_bed = db.session.get(Bed, bed_id)
        if not target_bed or target_bed.room_id != room_id:
            raise APIException("Selected bed does not belong to the selected room.", status_code=400, code="VALIDATION_ERROR")
        if target_bed.status != "AVAILABLE":
            raise APIException(f"Selected bed ({target_bed.bed_label}) is currently {target_bed.status}. Please choose another bed.", status_code=409, code="CONFLICT")
    else:
        # Find first available bed
        target_bed = Bed.query.filter_by(room_id=room_id, status="AVAILABLE").first()
        if not target_bed:
            raise APIException("No available beds in the selected room.", status_code=409, code="CONFLICT")

    booking_ref = generate_booking_reference()
    booking = Booking(
        booking_reference=booking_ref,
        customer_id=customer_id,
        property_id=property_id,
        room_id=room_id,
        bed_id=target_bed.id,
        preferred_move_in_date=move_in_date,
        sharing_type=sharing_type or room.sharing_type,
        status="PENDING"
    )
    db.session.add(booking)
    db.session.flush()

    # Log status history
    history = BookingHistory(
        booking_id=booking.id,
        from_status=None,
        to_status="PENDING",
        changed_by_user_id=customer_id,
        change_reason="Booking request submitted by customer."
    )
    db.session.add(history)
    db.session.commit()

    # Notify property owner
    owner_user = prop.owner_profile.user if prop.owner_profile else None
    if owner_user:
        send_notification(
            owner_user.id,
            "New Booking Request",
            f"New booking request ({booking_ref}) received for {prop.name}, Room {room.room_number}.",
            "BOOKING",
            "bookings",
            booking.id
        )

    log_audit("BOOKING_REQUEST", "bookings", booking.id, {"ref": booking_ref, "property": prop.name}, user_id=customer_id)
    return booking

def approve_booking_request(booking_id: int, user_id: int, remarks: str = None):
    """
    Approves booking and locks the bed via row-level locking (SELECT FOR UPDATE).
    Enforces that user_id has permission to manage the booking's property.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise APIException("Booking not found.", status_code=404, code="NOT_FOUND")

    user = db.session.get(User, user_id)
    verify_property_access(booking.property_id, user)

    if booking.status != "PENDING":
        raise APIException(f"Cannot approve booking in status '{booking.status}'.", status_code=400, code="INVALID_STATE")

    # Use row lock on bed
    bed = db.session.query(Bed).filter(Bed.id == booking.bed_id).with_for_update().one_or_none()
    if not bed:
        raise APIException("Associated bed not found.", status_code=404, code="NOT_FOUND")

    if bed.status != "AVAILABLE":
        raise APIException(f"Bed is no longer available (currently {bed.status}).", status_code=409, code="CONFLICT")

    # Update bed to RESERVED
    bed.status = "RESERVED"
    bed.last_status_change = datetime.now(timezone.utc)
    bed.notes = f"Reserved for booking {booking.booking_reference}"

    booking.status = "APPROVED"
    booking.admin_remarks = remarks or "Booking approved. Bed reserved for 48 hours."
    booking.reservation_expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    history = BookingHistory(
        booking_id=booking.id,
        from_status="PENDING",
        to_status="APPROVED",
        changed_by_user_id=user_id,
        change_reason=remarks or "Approved by PG authority. Bed reserved for 48 hours."
    )
    db.session.add(history)
    db.session.commit()

    send_notification(
        booking.customer_id,
        "Booking Approved",
        f"Your booking ({booking.booking_reference}) for {booking.property.name} has been approved. Your bed is reserved for 48 hours.",
        "BOOKING",
        "bookings",
        booking.id
    )

    log_audit("BOOKING_APPROVED", "bookings", booking.id, {"remarks": remarks}, user_id=user_id)
    return booking

def reject_booking_request(booking_id: int, user_id: int, reason: str):
    """
    Rejects booking and releases reserved bed if previously approved.
    Enforces property access rights for the acting user.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise APIException("Booking not found.", status_code=404, code="NOT_FOUND")

    user = db.session.get(User, user_id)
    verify_property_access(booking.property_id, user)

    if booking.status not in ["PENDING", "APPROVED"]:
        raise APIException(f"Cannot reject booking in status '{booking.status}'.", status_code=400, code="INVALID_STATE")

    old_status = booking.status

    # If it was approved, release the reserved bed
    if old_status == "APPROVED" and booking.bed_id:
        bed = db.session.get(Bed, booking.bed_id)
        if bed and bed.status == "RESERVED":
            bed.status = "AVAILABLE"
            bed.last_status_change = datetime.now(timezone.utc)
            bed.notes = "Released after booking rejection"

    booking.status = "REJECTED"
    booking.admin_remarks = reason

    history = BookingHistory(
        booking_id=booking.id,
        from_status=old_status,
        to_status="REJECTED",
        changed_by_user_id=user_id,
        change_reason=reason
    )
    db.session.add(history)
    db.session.commit()

    send_notification(
        booking.customer_id,
        "Booking Rejected",
        f"Your booking ({booking.booking_reference}) has been rejected. Reason: {reason}",
        "BOOKING",
        "bookings",
        booking.id
    )

    log_audit("BOOKING_REJECTED", "bookings", booking.id, {"reason": reason}, user_id=user_id)
    return booking

def cancel_booking_by_customer(booking_id: int, customer_id: int, reason: str = None):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.customer_id != customer_id:
        raise APIException("Booking not found.", status_code=404, code="NOT_FOUND")

    if booking.status not in ["PENDING", "APPROVED"]:
        raise APIException("Only pending or approved bookings can be cancelled.", status_code=400, code="INVALID_STATE")

    old_status = booking.status
    if old_status == "APPROVED" and booking.bed_id:
        bed = db.session.get(Bed, booking.bed_id)
        if bed and bed.status == "RESERVED":
            bed.status = "AVAILABLE"
            bed.last_status_change = datetime.now(timezone.utc)
            bed.notes = "Released after customer cancellation"

    booking.status = "CANCELLED"
    booking.admin_remarks = reason or "Cancelled by customer."

    history = BookingHistory(
        booking_id=booking.id,
        from_status=old_status,
        to_status="CANCELLED",
        changed_by_user_id=customer_id,
        change_reason=reason or "Customer requested cancellation."
    )
    db.session.add(history)
    db.session.commit()

    log_audit("BOOKING_CANCELLED", "bookings", booking.id, {"reason": reason}, user_id=customer_id)
    return booking

def expire_stale_reservations():
    """
    Finds all APPROVED bookings whose reservation_expires_at has elapsed,
    transitions them to EXPIRED, and safely releases the reserved bed back to AVAILABLE
    if and only if the bed is still RESERVED for that exact booking.
    Safe to execute repeatedly (idempotent).
    """
    now = datetime.now(timezone.utc)
    stale_bookings = Booking.query.filter(
        Booking.status == "APPROVED",
        Booking.reservation_expires_at.isnot(None),
        Booking.reservation_expires_at <= now
    ).all()

    expired_count = 0
    for booking in stale_bookings:
        booking.status = "EXPIRED"
        booking.admin_remarks = (booking.admin_remarks or "") + " [Reservation window elapsed without check-in]"

        # Release the bed only if it remains RESERVED for this booking
        if booking.bed_id:
            bed = db.session.get(Bed, booking.bed_id)
            if bed and bed.status == "RESERVED":
                bed.status = "AVAILABLE"
                bed.last_status_change = now
                bed.notes = f"Released after booking {booking.booking_reference} reservation expiry"

        history = BookingHistory(
            booking_id=booking.id,
            from_status="APPROVED",
            to_status="EXPIRED",
            changed_by_user_id=None,
            change_reason="Reservation window expired."
        )
        db.session.add(history)
        expired_count += 1

    if expired_count > 0:
        db.session.commit()

    return expired_count

