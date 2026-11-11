from datetime import date, time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.tenant import Tenant, RoomAllocation, VisitorLog
from app.models.room_bed import Room, Bed
from app.models.user import User, OwnerProfile, ManagerAssignment
from app.models.property import PGProperty
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.schemas.validators import validate_positive_amount
from app.services.tenant_service import check_in_tenant, check_out_tenant

tenant_bp = Blueprint("tenants", __name__, url_prefix="/api/tenants")

@tenant_bp.route("/check-in", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def check_in():
    current_user = get_current_user()
    data = request.get_json() or {}

    user_id = data.get("user_id")
    bed_id = data.get("bed_id")
    booking_id = data.get("booking_id")
    rent_val = validate_positive_amount(data.get("monthly_rent_agreed"), "Monthly rent")
    deposit_val = validate_positive_amount(data.get("security_deposit_paid"), "Security deposit")
    
    check_in_str = data.get("check_in_date") or date.today().isoformat()
    try:
        check_in_date_val = date.fromisoformat(check_in_str)
    except ValueError:
        raise APIException("Invalid check_in_date format. Expected YYYY-MM-DD.", status_code=400, code="VALIDATION_ERROR")

    allocation = check_in_tenant(
        user_id=user_id,
        bed_id=bed_id,
        check_in_date_val=check_in_date_val,
        monthly_rent=rent_val,
        deposit_paid=deposit_val,
        booking_id=booking_id,
        performed_by_user_id=current_user.id
    )

    return jsonify({
        "success": True,
        "message": "Tenant checked in successfully and bed marked OCCUPIED.",
        "data": allocation.to_dict()
    }), 201

@tenant_bp.route("/allocations/<int:allocation_id>/check-out", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def check_out(allocation_id):
    current_user = get_current_user()
    data = request.get_json() or {}

    check_out_str = data.get("check_out_date") or date.today().isoformat()
    try:
        check_out_date_val = date.fromisoformat(check_out_str)
    except ValueError:
        raise APIException("Invalid check_out_date format.", status_code=400, code="VALIDATION_ERROR")

    refund_amt = validate_positive_amount(data.get("refund_amount", 0.0), "Refund amount")
    deduction_amt = validate_positive_amount(data.get("deductions_amount", 0.0), "Deductions amount")
    deduction_reason = data.get("deduction_reason", "")
    needs_repair = bool(data.get("needs_maintenance", False))

    allocation = check_out_tenant(
        allocation_id=allocation_id,
        check_out_date_val=check_out_date_val,
        refund_amount=refund_amt,
        deduction_amount=deduction_amt,
        deduction_reason=deduction_reason,
        needs_maintenance=needs_repair,
        performed_by_user_id=current_user.id
    )

    return jsonify({
        "success": True,
        "message": "Tenant checked out successfully and bed released.",
        "data": allocation.to_dict()
    }), 200

@tenant_bp.route("/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def list_property_tenants(property_id):
    allocs = db.session.query(RoomAllocation).join(Bed, RoomAllocation.bed_id == Bed.id).join(Room, Bed.room_id == Room.id).filter(
        Room.property_id == property_id,
        RoomAllocation.is_active == True
    ).all()

    return jsonify({
        "success": True,
        "data": [
            {
                "allocation": a.to_dict(),
                "tenant": a.tenant.to_dict()
            }
            for a in allocs
        ]
    }), 200

@tenant_bp.route("/my-stay", methods=["GET"])
@jwt_required()
@role_required("TENANT")
def get_my_stay():
    current_user = get_current_user()
    tenant = Tenant.query.filter_by(user_id=current_user.id).first()
    if not tenant:
        return jsonify({"success": True, "data": None}), 200

    active_alloc = RoomAllocation.query.filter_by(tenant_id=tenant.id, is_active=True).first()
    if not active_alloc:
        return jsonify({"success": True, "data": None}), 200

    prop = active_alloc.bed.room.property
    return jsonify({
        "success": True,
        "data": {
            "allocation": active_alloc.to_dict(),
            "room": active_alloc.bed.room.to_dict(include_beds=False),
            "bed": active_alloc.bed.to_dict(),
            "property": prop.to_dict()
        }
    }), 200

@tenant_bp.route("/visitors", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def add_visitor_log():
    data = request.get_json() or {}
    prop_id = data.get("property_id")
    tenant_id = data.get("tenant_id")
    name = (data.get("visitor_name") or "").strip()
    phone = (data.get("visitor_phone") or "").strip()
    rel = (data.get("relationship") or "Friend").strip()

    if not prop_id or not tenant_id or not name or not phone:
        raise APIException("Property, tenant, visitor name, and phone are required.", status_code=400, code="VALIDATION_ERROR")

    now = datetime.now()
    log = VisitorLog(
        property_id=prop_id,
        tenant_id=tenant_id,
        visitor_name=name,
        visitor_phone=phone,
        visit_date=date.today(),
        check_in_time=now.time(),
        relationship=rel
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Visitor entry logged.",
        "data": log.to_dict()
    }), 201

@tenant_bp.route("/visitors/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def get_visitor_logs(property_id):
    logs = VisitorLog.query.filter_by(property_id=property_id).order_by(VisitorLog.created_at.desc()).limit(50).all()
    return jsonify({
        "success": True,
        "data": [l.to_dict() for l in logs]
    }), 200

