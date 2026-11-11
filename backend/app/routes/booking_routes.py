from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.booking import Booking
from app.models.property import PGProperty
from app.models.user import OwnerProfile, ManagerAssignment
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user, verify_property_access
from app.services.booking_service import (
    create_booking_request,
    approve_booking_request,
    reject_booking_request,
    cancel_booking_by_customer,
    expire_stale_reservations
)

booking_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")

@booking_bp.route("", methods=["POST"])
@jwt_required()
@role_required("TENANT")
def request_booking():
    current_user = get_current_user()
    data = request.get_json() or {}
    
    property_id = data.get("property_id")
    room_id = data.get("room_id")
    bed_id = data.get("bed_id")
    move_in_str = data.get("preferred_move_in_date")
    sharing_type = data.get("sharing_type", "")

    if not property_id or not room_id or not move_in_str:
        raise APIException("Property ID, Room ID, and Preferred Move-in Date are required.", status_code=400, code="VALIDATION_ERROR")

    try:
        move_in_date = date.fromisoformat(move_in_str)
    except ValueError:
        raise APIException("Invalid date format. Expected YYYY-MM-DD.", status_code=400, code="VALIDATION_ERROR")

    booking = create_booking_request(
        customer_id=current_user.id,
        property_id=property_id,
        room_id=room_id,
        move_in_date=move_in_date,
        sharing_type=sharing_type,
        bed_id=bed_id
    )

    return jsonify({
        "success": True,
        "message": "Booking request submitted successfully. The PG owner will review your request.",
        "data": booking.to_dict()
    }), 201

@booking_bp.route("/my-bookings", methods=["GET"])
@jwt_required()
@role_required("TENANT")
def get_my_bookings():
    current_user = get_current_user()
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [b.to_dict() for b in bookings]
    }), 200

@booking_bp.route("/<int:booking_id>", methods=["GET"])
@jwt_required()
def get_booking_details(booking_id):
    current_user = get_current_user()
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise APIException("Booking not found.", status_code=404, code="NOT_FOUND")

    # Authorization check
    if current_user.role == "TENANT":
        if booking.customer_id != current_user.id:
            raise APIException("Access denied.", status_code=403, code="FORBIDDEN")
    else:
        verify_property_access(booking.property_id, current_user)

    data = booking.to_dict()
    data["history"] = [h.to_dict() for h in booking.history]
    return jsonify({
        "success": True,
        "data": data
    }), 200

@booking_bp.route("/<int:booking_id>/approve", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def approve_booking(booking_id):
    current_user = get_current_user()
    data = request.get_json() or {}
    remarks = data.get("remarks")

    booking = approve_booking_request(booking_id, current_user.id, remarks)
    return jsonify({
        "success": True,
        "message": "Booking approved. Bed reserved for tenant.",
        "data": booking.to_dict()
    }), 200

@booking_bp.route("/<int:booking_id>/reject", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def reject_booking(booking_id):
    current_user = get_current_user()
    data = request.get_json() or {}
    reason = (data.get("reason") or "Unavailable as per PG schedule.").strip()

    booking = reject_booking_request(booking_id, current_user.id, reason)
    return jsonify({
        "success": True,
        "message": "Booking rejected.",
        "data": booking.to_dict()
    }), 200

@booking_bp.route("/<int:booking_id>/cancel", methods=["POST"])
@jwt_required()
@role_required("TENANT")
def cancel_booking(booking_id):
    current_user = get_current_user()
    data = request.get_json() or {}
    reason = (data.get("reason") or "Cancelled by user.").strip()

    booking = cancel_booking_by_customer(booking_id, current_user.id, reason)
    return jsonify({
        "success": True,
        "message": "Booking cancelled.",
        "data": booking.to_dict()
    }), 200

@booking_bp.route("/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def get_property_bookings(property_id):
    current_user = get_current_user()
    verify_property_access(property_id, current_user)
    bookings = Booking.query.filter_by(property_id=property_id).order_by(Booking.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [b.to_dict() for b in bookings]
    }), 200

@booking_bp.route("/expire-reservations", methods=["POST"])
def trigger_expire_reservations():
    """
    Safe maintenance trigger to expire overdue reservations and release reserved beds.
    Idempotent and safe to run on demand or via automation.
    """
    count = expire_stale_reservations()
    return jsonify({
        "success": True,
        "message": f"Reservation expiry process completed. Expired {count} reservation(s).",
        "data": {"expired_count": count}
    }), 200

