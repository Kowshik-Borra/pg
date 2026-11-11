from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.user import User, OwnerProfile
from app.models.tenant import Tenant
from app.schemas.validators import validate_phone, validate_password
from app.middleware.error_handlers import APIException
from app.middleware.rbac import get_current_user
from app.services.audit_service import log_audit

user_bp = Blueprint("users", __name__, url_prefix="/api/users")

@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    current_user = get_current_user()
    data = request.get_json() or {}

    if "full_name" in data and data["full_name"].strip():
        current_user.full_name = data["full_name"].strip()

    if "phone" in data:
        current_user.phone = validate_phone(data["phone"])

    if current_user.role == "OWNER" and current_user.owner_profile:
        if "business_name" in data:
            current_user.owner_profile.business_name = data["business_name"].strip()
        if "pan_number" in data:
            current_user.owner_profile.pan_number = data["pan_number"].strip()
        if "aadhaar_last4" in data:
            current_user.owner_profile.aadhaar_last4 = data["aadhaar_last4"].strip()

    elif current_user.role == "TENANT" and current_user.tenant_profile:
        if "emergency_contact_name" in data:
            current_user.tenant_profile.emergency_contact_name = data["emergency_contact_name"].strip()
        if "emergency_contact_phone" in data:
            current_user.tenant_profile.emergency_contact_phone = data["emergency_contact_phone"].strip()
        if "emergency_contact_relation" in data:
            current_user.tenant_profile.emergency_contact_relation = data["emergency_contact_relation"].strip()
        if "college_or_company_name" in data:
            current_user.tenant_profile.college_or_company_name = data["college_or_company_name"].strip()

    db.session.commit()
    log_audit("PROFILE_UPDATE", "users", current_user.id, {"updated_fields": list(data.keys())}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "data": current_user.to_dict()
    }), 200

@user_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    current_user = get_current_user()
    data = request.get_json() or {}
    old_pw = data.get("current_password") or ""
    new_pw = validate_password(data.get("new_password") or "")

    if not current_user.check_password(old_pw):
        raise APIException("Current password does not match.", status_code=400, code="INVALID_CREDENTIALS")

    current_user.set_password(new_pw)
    db.session.commit()
    log_audit("PASSWORD_CHANGE", "users", current_user.id, {}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Password updated successfully."
    }), 200
