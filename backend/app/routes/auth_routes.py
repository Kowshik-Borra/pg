from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from app.models.user import User, OwnerProfile
from app.models.tenant import Tenant
from app.schemas.validators import validate_email, validate_phone, validate_password
from app.middleware.error_handlers import APIException
from app.services.audit_service import log_audit
from app.services.notification_service import send_notification

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    
    email = validate_email(data.get("email"))
    password = validate_password(data.get("password"))
    full_name = (data.get("full_name") or "").strip()
    phone = validate_phone(data.get("phone"))
    role = (data.get("role") or "TENANT").upper()
    
    if not full_name:
        raise APIException("Full name is required.", status_code=400, code="VALIDATION_ERROR")
    
    if role not in ["TENANT", "OWNER", "MANAGER"]:
        raise APIException("Invalid role specified. Allowed: TENANT, OWNER, MANAGER.", status_code=400, code="VALIDATION_ERROR")
    
    if User.query.filter_by(email=email).first():
        raise APIException("An account with this email address already exists.", status_code=409, code="CONFLICT")

    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        role=role,
        is_active=True,
        is_verified=False
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    if role == "OWNER":
        business_name = (data.get("business_name") or full_name).strip()
        pan = (data.get("pan_number") or "").strip()
        aadhaar = (data.get("aadhaar_last4") or "").strip()
        profile = OwnerProfile(
            user_id=user.id,
            business_name=business_name,
            pan_number=pan,
            aadhaar_last4=aadhaar,
            is_approved=False
        )
        db.session.add(profile)
    elif role == "TENANT":
        emergency_name = (data.get("emergency_contact_name") or "Primary Contact").strip()
        emergency_phone = (data.get("emergency_contact_phone") or phone).strip()
        relation = (data.get("emergency_contact_relation") or "Family").strip()
        id_type = (data.get("id_proof_type") or "Aadhaar Card").strip()
        id_masked = (data.get("id_proof_number_masked") or "XXXX-XXXX-XXXX").strip()
        college_or_co = (data.get("college_or_company_name") or "").strip()
        
        tenant = Tenant(
            user_id=user.id,
            emergency_contact_name=emergency_name,
            emergency_contact_phone=emergency_phone,
            emergency_contact_relation=relation,
            id_proof_type=id_type,
            id_proof_number_masked=id_masked,
            college_or_company_name=college_or_co
        )
        db.session.add(tenant)

    db.session.commit()

    log_audit("USER_REGISTER", "users", user.id, {"email": email, "role": role}, user_id=user.id)
    send_notification(user.id, "Welcome to PG Connect", f"Welcome, {full_name}! Your account has been registered successfully.", "SYSTEM")

    additional_claims = {"role": user.role, "email": user.email, "name": user.full_name}
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify({
        "success": True,
        "message": "Registration successful.",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        raise APIException("Email and password are required.", status_code=400, code="VALIDATION_ERROR")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise APIException("Invalid email address or password.", status_code=401, code="UNAUTHORIZED")

    if not user.is_active:
        raise APIException("Your account has been suspended. Please contact platform administration.", status_code=403, code="FORBIDDEN")

    additional_claims = {"role": user.role, "email": user.email, "name": user.full_name}
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

    log_audit("USER_LOGIN", "users", user.id, {"email": email}, user_id=user.id)

    user_info = user.to_dict()
    if user.role == "OWNER" and user.owner_profile:
        user_info["owner_profile"] = user.owner_profile.to_dict()
    elif user.role == "TENANT" and user.tenant_profile:
        user_info["tenant_profile"] = user.tenant_profile.to_dict()

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user_info
        }
    }), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        raise APIException("User account not found.", status_code=404, code="NOT_FOUND")

    info = user.to_dict()
    if user.role == "OWNER" and user.owner_profile:
        info["owner_profile"] = user.owner_profile.to_dict()
    elif user.role == "TENANT" and user.tenant_profile:
        info["tenant_profile"] = user.tenant_profile.to_dict()

    return jsonify({
        "success": True,
        "data": info
    }), 200

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_active:
        raise APIException("User account is inactive or not found.", status_code=401, code="UNAUTHORIZED")

    additional_claims = {"role": user.role, "email": user.email, "name": user.full_name}
    new_access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify({
        "success": True,
        "data": {
            "access_token": new_access_token
        }
    }), 200
