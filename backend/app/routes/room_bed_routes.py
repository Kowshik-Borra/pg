from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.room_bed import Room, Bed
from app.models.property import PGProperty
from app.models.user import OwnerProfile, ManagerAssignment
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.schemas.validators import validate_positive_amount
from app.services.audit_service import log_audit

room_bed_bp = Blueprint("rooms_beds", __name__, url_prefix="/api")

def verify_property_access(property_id, user):
    if user.role == "SUPER_ADMIN":
        return True
    if user.role == "OWNER":
        profile = OwnerProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return False
        prop = db.session.get(PGProperty, property_id)
        return prop and prop.owner_id == profile.id
    if user.role == "MANAGER":
        assignment = ManagerAssignment.query.filter_by(
            manager_user_id=user.id,
            property_id=property_id,
            is_active=True
        ).first()
        return assignment is not None
    return False

@room_bed_bp.route("/properties/<int:property_id>/rooms", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def create_room(property_id):
    current_user = get_current_user()
    if not verify_property_access(property_id, current_user):
        raise APIException("Access denied for this property.", status_code=403, code="FORBIDDEN")

    data = request.get_json() or {}
    room_number = (data.get("room_number") or "").strip()
    floor_number = int(data.get("floor_number", 1))
    sharing_type = (data.get("sharing_type") or "").strip().upper()
    has_ac = bool(data.get("has_ac", False))
    has_attached_bathroom = bool(data.get("has_attached_bathroom", False))
    monthly_rent = validate_positive_amount(data.get("monthly_rent_per_bed"), "Monthly rent")
    security_deposit = validate_positive_amount(data.get("security_deposit_per_bed"), "Security deposit")

    if not room_number:
        raise APIException("Room number is required.", status_code=400, code="VALIDATION_ERROR")

    if sharing_type not in ["SINGLE", "DOUBLE", "TRIPLE", "FOUR"]:
        raise APIException("Sharing type must be SINGLE, DOUBLE, TRIPLE, or FOUR.", status_code=400, code="VALIDATION_ERROR")

    # Check for duplicate room number in property
    existing = Room.query.filter_by(property_id=property_id, room_number=room_number).first()
    if existing:
        raise APIException(f"Room '{room_number}' already exists in this property.", status_code=409, code="CONFLICT")

    room = Room(
        property_id=property_id,
        room_number=room_number,
        floor_number=floor_number,
        sharing_type=sharing_type,
        has_ac=has_ac,
        has_attached_bathroom=has_attached_bathroom,
        monthly_rent_per_bed=monthly_rent,
        security_deposit_per_bed=security_deposit,
        is_active=True
    )
    db.session.add(room)
    db.session.flush()

    # Automatically generate individual physical beds based on sharing type
    bed_count_map = {"SINGLE": 1, "DOUBLE": 2, "TRIPLE": 3, "FOUR": 4}
    num_beds = bed_count_map[sharing_type]
    bed_labels = ["A", "B", "C", "D"][:num_beds]

    for label in bed_labels:
        bed = Bed(
            room_id=room.id,
            bed_label=f"Bed {label}",
            status="AVAILABLE",
            last_status_change=datetime.now(timezone.utc),
            notes=f"Auto-initialized bed for {sharing_type} sharing"
        )
        db.session.add(bed)

    db.session.commit()
    log_audit("ROOM_CREATE", "rooms", room.id, {"room_number": room_number, "sharing_type": sharing_type}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"Room {room_number} created with {num_beds} available physical beds.",
        "data": room.to_dict(include_beds=True)
    }), 201

@room_bed_bp.route("/rooms/<int:room_id>", methods=["PUT"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def update_room(room_id):
    current_user = get_current_user()
    room = db.session.get(Room, room_id)
    if not room:
        raise APIException("Room not found.", status_code=404, code="NOT_FOUND")

    if not verify_property_access(room.property_id, current_user):
        raise APIException("Access denied.", status_code=403, code="FORBIDDEN")

    data = request.get_json() or {}
    if "monthly_rent_per_bed" in data:
        room.monthly_rent_per_bed = validate_positive_amount(data["monthly_rent_per_bed"], "Monthly rent")
    if "security_deposit_per_bed" in data:
        room.security_deposit_per_bed = validate_positive_amount(data["security_deposit_per_bed"], "Security deposit")
    if "has_ac" in data:
        room.has_ac = bool(data["has_ac"])
    if "has_attached_bathroom" in data:
        room.has_attached_bathroom = bool(data["has_attached_bathroom"])
    if "is_active" in data:
        room.is_active = bool(data["is_active"])

    db.session.commit()
    log_audit("ROOM_UPDATE", "rooms", room.id, {"updated_fields": list(data.keys())}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Room details updated.",
        "data": room.to_dict(include_beds=True)
    }), 200

@room_bed_bp.route("/beds/<int:bed_id>/status", methods=["PATCH"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def update_bed_status(bed_id):
    current_user = get_current_user()
    bed = db.session.get(Bed, bed_id)
    if not bed:
        raise APIException("Bed not found.", status_code=404, code="NOT_FOUND")

    room = bed.room
    if not verify_property_access(room.property_id, current_user):
        raise APIException("Access denied.", status_code=403, code="FORBIDDEN")

    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip().upper()
    notes = data.get("notes")

    if new_status not in ["AVAILABLE", "MAINTENANCE", "INACTIVE"]:
        raise APIException("Manual status change allowed only for: AVAILABLE, MAINTENANCE, INACTIVE. RESERVED and OCCUPIED are managed through the booking and check-in workflows.", status_code=400, code="VALIDATION_ERROR")

    if bed.status == "OCCUPIED" and new_status != "OCCUPIED":
        raise APIException("Cannot manually change status of an OCCUPIED bed. Please process tenant check-out first.", status_code=400, code="CONFLICT")

    old_status = bed.status
    bed.status = new_status
    bed.last_status_change = datetime.now(timezone.utc)
    if notes:
        bed.notes = notes

    db.session.commit()
    log_audit("BED_STATUS_CHANGE", "beds", bed.id, {"from": old_status, "to": new_status, "notes": notes}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"Bed status updated to {new_status}.",
        "data": bed.to_dict()
    }), 200

