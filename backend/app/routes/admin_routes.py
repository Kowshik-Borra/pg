from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from app.extensions import db
from app.models.user import User, OwnerProfile
from app.models.property import PGProperty
from app.models.room_bed import Room, Bed
from app.models.tenant import RoomAllocation
from app.models.booking import Booking
from app.models.finance import RentInvoice, Payment
from app.models.governance import PropertyVerification, AuditLog
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.services.audit_service import log_audit
from app.services.notification_service import send_notification

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/analytics", methods=["GET"])
@jwt_required()
@role_required("SUPER_ADMIN")
def get_platform_analytics():
    total_users = User.query.count()
    total_owners = User.query.filter_by(role="OWNER").count()
    total_tenants = User.query.filter_by(role="TENANT").count()
    total_managers = User.query.filter_by(role="MANAGER").count()

    total_properties = PGProperty.query.count()
    verified_properties = PGProperty.query.filter_by(is_verified=True).count()
    pending_verifications = PropertyVerification.query.filter_by(status="SUBMITTED").count()

    total_bookings = Booking.query.count()
    active_tenants = RoomAllocation.query.filter_by(is_active=True).count()

    total_revenue_collected = float(db.session.query(func.coalesce(func.sum(Payment.amount), 0.00)).scalar())
    total_rent_billed = float(db.session.query(func.coalesce(func.sum(RentInvoice.total_amount_due), 0.00)).scalar())

    return jsonify({
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "owners": total_owners,
                "tenants": total_tenants,
                "managers": total_managers
            },
            "properties": {
                "total": total_properties,
                "verified": verified_properties,
                "pending_verification": pending_verifications
            },
            "operations": {
                "total_bookings": total_bookings,
                "active_tenants": active_tenants,
                "total_rent_billed": total_rent_billed,
                "total_revenue_collected": total_revenue_collected
            }
        }
    }), 200

@admin_bp.route("/verifications", methods=["GET"])
@jwt_required()
@role_required("SUPER_ADMIN")
def list_verifications():
    verifications = PropertyVerification.query.order_by(PropertyVerification.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [v.to_dict() for v in verifications]
    }), 200

@admin_bp.route("/properties/<int:property_id>/verify", methods=["POST"])
@jwt_required()
@role_required("SUPER_ADMIN")
def verify_property(property_id):
    current_user = get_current_user()
    prop = db.session.get(PGProperty, property_id)
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")

    data = request.get_json() or {}
    decision = (data.get("decision") or "").strip().upper()  # APPROVE or REJECT
    reason = (data.get("reason") or "").strip()

    if decision not in ["APPROVE", "REJECT"]:
        raise APIException("Decision must be APPROVE or REJECT.", status_code=400, code="VALIDATION_ERROR")

    verification = PropertyVerification.query.filter_by(property_id=property_id).order_by(PropertyVerification.created_at.desc()).first()
    if not verification:
        verification = PropertyVerification(property_id=property_id)
        db.session.add(verification)

    verification.reviewed_by_admin_id = current_user.id
    if decision == "APPROVE":
        prop.is_verified = True
        verification.status = "APPROVED"
        verification.rejection_reason = None
        msg = f"Property '{prop.name}' has been verified and approved."
        send_notification(prop.owner_profile.user_id, "Property Listing Approved", f"Your PG listing for '{prop.name}' has been verified by administrators.", "PROPERTY")
    else:
        prop.is_verified = False
        verification.status = "REJECTED"
        verification.rejection_reason = reason or "Documentation or details require revision."
        msg = f"Property '{prop.name}' verification rejected."
        send_notification(prop.owner_profile.user_id, "Property Listing Needs Revision", f"Verification for '{prop.name}' was rejected. Reason: {verification.rejection_reason}", "PROPERTY")

    db.session.commit()
    log_audit("PROPERTY_MODERATION", "pg_properties", prop.id, {"decision": decision, "reason": reason}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": msg,
        "data": prop.to_dict()
    }), 200

@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@role_required("SUPER_ADMIN")
def list_users():
    role_filter = request.args.get("role")
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter.upper())
    users = query.order_by(User.created_at.desc()).limit(100).all()
    return jsonify({
        "success": True,
        "data": [u.to_dict() for u in users]
    }), 200

@admin_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@jwt_required()
@role_required("SUPER_ADMIN")
def toggle_user_status(user_id):
    current_user = get_current_user()
    if current_user.id == user_id:
        raise APIException("Super Admin cannot suspend own account.", status_code=400, code="FORBIDDEN")

    user = db.session.get(User, user_id)
    if not user:
        raise APIException("User not found.", status_code=404, code="NOT_FOUND")

    data = request.get_json() or {}
    is_active = bool(data.get("is_active", not user.is_active))
    user.is_active = is_active
    db.session.commit()

    log_audit("USER_STATUS_CHANGE", "users", user.id, {"is_active": is_active}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"User account has been {'activated' if is_active else 'suspended'}.",
        "data": user.to_dict()
    }), 200

@admin_bp.route("/audit-logs", methods=["GET"])
@jwt_required()
@role_required("SUPER_ADMIN")
def get_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify({
        "success": True,
        "data": [l.to_dict() for l in logs]
    }), 200

