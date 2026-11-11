import re
import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from app.extensions import db
from app.models.property import PGProperty, PropertyPhoto, PropertyFacility
from app.models.room_bed import Room, Bed
from app.models.user import User, OwnerProfile
from app.models.governance import PropertyVerification
from app.schemas.validators import validate_coordinates, validate_positive_amount
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.services.audit_service import log_audit
from app.utils.file_uploader import save_uploaded_file

property_bp = Blueprint("properties", __name__, url_prefix="/api/properties")

def generate_slug(name, city):
    clean_name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    clean_city = re.sub(r"[^\w\s-]", "", city).strip().lower()
    base_slug = f"{re.sub(r'[-\s]+', '-', clean_name)}-{re.sub(r'[-\s]+', '-', clean_city)}"
    slug = base_slug
    counter = 1
    while PGProperty.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

@property_bp.route("/search", methods=["GET"])
def search_properties():
    city = request.args.get("city", "").strip()
    locality = request.args.get("locality", "").strip()
    gender = request.args.get("gender", "").strip().upper()
    min_rent = request.args.get("min_rent", type=float)
    max_rent = request.args.get("max_rent", type=float)
    sharing = request.args.get("sharing", "").strip().upper()
    has_ac = request.args.get("has_ac", type=lambda v: v.lower() == "true")
    has_wifi = request.args.get("has_wifi", type=lambda v: v.lower() == "true")
    has_food = request.args.get("has_food", type=lambda v: v.lower() == "true")
    verified_only = request.args.get("verified_only", type=lambda v: v.lower() == "true")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 12, type=int)))

    query = PGProperty.query.filter(PGProperty.is_active == True)

    if verified_only:
        query = query.filter(PGProperty.is_verified == True)

    if city:
        query = query.filter(PGProperty.city.ilike(f"%{city}%"))

    if locality:
        query = query.filter(PGProperty.locality.ilike(f"%{locality}%"))

    if gender in ["BOYS", "GIRLS", "CO_ED"]:
        query = query.filter(PGProperty.property_type == gender)

    if has_ac is not None or has_wifi is not None:
        query = query.join(PropertyFacility)
        if has_ac is True:
            query = query.filter(PropertyFacility.has_ac == True)
        if has_wifi is True:
            query = query.filter(PropertyFacility.has_wifi == True)

    # Filter by rent range or sharing type via Room subquery
    if min_rent or max_rent or sharing:
        room_filters = [Room.is_active == True]
        if min_rent is not None:
            room_filters.append(Room.monthly_rent_per_bed >= min_rent)
        if max_rent is not None:
            room_filters.append(Room.monthly_rent_per_bed <= max_rent)
        if sharing in ["SINGLE", "DOUBLE", "TRIPLE", "FOUR"]:
            room_filters.append(Room.sharing_type == sharing)
        
        matching_property_ids = db.session.query(Room.property_id).filter(*room_filters).distinct()
        query = query.filter(PGProperty.id.in_(matching_property_ids))

    total = query.count()
    properties = query.order_by(PGProperty.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    items = [p.to_dict() for p in properties]

    return jsonify({
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
    }), 200

@property_bp.route("/<int:property_id>", methods=["GET"])
def get_property_by_id(property_id):
    prop = PGProperty.query.get(property_id)
    if not prop or not prop.is_active:
        raise APIException("Property not found or inactive.", status_code=404, code="NOT_FOUND")
    return jsonify({
        "success": True,
        "data": prop.to_dict(include_details=True)
    }), 200

@property_bp.route("/slug/<string:slug>", methods=["GET"])
def get_property_by_slug(slug):
    prop = PGProperty.query.filter_by(slug=slug, is_active=True).first()
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")
    return jsonify({
        "success": True,
        "data": prop.to_dict(include_details=True)
    }), 200

@property_bp.route("/compare", methods=["GET"])
def compare_properties():
    ids_param = request.args.get("ids", "").strip()
    if not ids_param:
        raise APIException("Provide at least one property ID for comparison.", status_code=400, code="VALIDATION_ERROR")
    
    try:
        prop_ids = [int(i.strip()) for i in ids_param.split(",") if i.strip()]
    except ValueError:
        raise APIException("Property IDs must be valid integers.", status_code=400, code="VALIDATION_ERROR")
    
    if len(prop_ids) > 4:
        raise APIException("You can compare up to 4 properties at a time.", status_code=400, code="VALIDATION_ERROR")

    properties = PGProperty.query.filter(PGProperty.id.in_(prop_ids), PGProperty.is_active == True).all()
    return jsonify({
        "success": True,
        "data": [p.to_dict(include_details=True) for p in properties]
    }), 200

@property_bp.route("", methods=["POST"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def create_property():
    current_user = get_current_user()
    if not current_user:
        raise APIException("User not authenticated.", status_code=401, code="UNAUTHORIZED")

    # If owner, find owner_profile
    if current_user.role == "OWNER":
        profile = OwnerProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            raise APIException("Owner profile not found. Please complete profile.", status_code=400, code="INVALID_PROFILE")
        owner_id = profile.id
    else:
        # Super admin can assign owner
        owner_id = request.json.get("owner_id")
        if not owner_id:
            raise APIException("Owner ID is required when super admin creates a property.", status_code=400, code="VALIDATION_ERROR")

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    prop_type = (data.get("property_type") or "").strip().upper()
    address1 = (data.get("address_line1") or "").strip()
    locality = (data.get("locality") or "").strip()
    city = (data.get("city") or "").strip()
    state = (data.get("state") or "").strip()
    pincode = (data.get("pincode") or "").strip()
    phone = (data.get("contact_phone") or current_user.phone).strip()
    email = (data.get("contact_email") or current_user.email).strip()
    description = (data.get("description") or "").strip()

    if not name or not address1 or not locality or not city or not state or not pincode or not description:
        raise APIException("All basic property address, name, and description fields are required.", status_code=400, code="VALIDATION_ERROR")

    if prop_type not in ["BOYS", "GIRLS", "CO_ED"]:
        raise APIException("Property type must be BOYS, GIRLS, or CO_ED.", status_code=400, code="VALIDATION_ERROR")

    lat, lng = validate_coordinates(data.get("latitude", 12.9716), data.get("longitude", 77.5946))
    slug = generate_slug(name, city)

    prop = PGProperty(
        owner_id=owner_id,
        name=name,
        slug=slug,
        property_type=prop_type,
        address_line1=address1,
        address_line2=data.get("address_line2", ""),
        locality=locality,
        city=city,
        state=state,
        pincode=pincode,
        latitude=lat,
        longitude=lng,
        contact_phone=phone,
        contact_email=email,
        description=description,
        rules=data.get("rules", "No loud music after 10 PM. Non-smoking premises."),
        notice_period_days=int(data.get("notice_period_days", 30)),
        gate_closing_time=data.get("gate_closing_time", "22:30"),
        is_verified=False,
        is_active=True
    )
    db.session.add(prop)
    db.session.flush()

    # Create default facilities
    fac = data.get("facilities", {})
    facility = PropertyFacility(
        property_id=prop.id,
        has_wifi=fac.get("has_wifi", True),
        has_ac=fac.get("has_ac", False),
        has_washing_machine=fac.get("has_washing_machine", True),
        has_parking=fac.get("has_parking", True),
        has_housekeeping=fac.get("has_housekeeping", True),
        has_cctv=fac.get("has_cctv", True),
        has_drinking_water=fac.get("has_drinking_water", True),
        has_power_backup=fac.get("has_power_backup", True),
        has_attached_washroom=fac.get("has_attached_washroom", False),
        has_refrigerator=fac.get("has_refrigerator", False),
        has_biometric_access=fac.get("has_biometric_access", False)
    )
    db.session.add(facility)

    # Create default submission for verification
    verification = PropertyVerification(
        property_id=prop.id,
        status="SUBMITTED"
    )
    db.session.add(verification)
    db.session.commit()

    log_audit("PROPERTY_CREATE", "pg_properties", prop.id, {"name": name, "city": city}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Property registered successfully and submitted for admin verification.",
        "data": prop.to_dict(include_details=True)
    }), 201

@property_bp.route("/<int:property_id>", methods=["PUT"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def update_property(property_id):
    current_user = get_current_user()
    prop = PGProperty.query.get(property_id)
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")

    if current_user.role == "OWNER":
        profile = OwnerProfile.query.filter_by(user_id=current_user.id).first()
        if not profile or prop.owner_id != profile.id:
            raise APIException("You do not have permission to modify this property.", status_code=403, code="FORBIDDEN")

    data = request.get_json() or {}
    if "name" in data:
        prop.name = data["name"].strip()
    if "property_type" in data and data["property_type"] in ["BOYS", "GIRLS", "CO_ED"]:
        prop.property_type = data["property_type"]
    if "description" in data:
        prop.description = data["description"].strip()
    if "rules" in data:
        prop.rules = data["rules"].strip()
    if "notice_period_days" in data:
        prop.notice_period_days = int(data["notice_period_days"])
    if "gate_closing_time" in data:
        prop.gate_closing_time = data["gate_closing_time"]
    if "contact_phone" in data:
        prop.contact_phone = data["contact_phone"]
    if "contact_email" in data:
        prop.contact_email = data["contact_email"]
    if "latitude" in data and "longitude" in data:
        lat, lng = validate_coordinates(data["latitude"], data["longitude"])
        prop.latitude = lat
        prop.longitude = lng

    if "facilities" in data and prop.facilities:
        fac = data["facilities"]
        for k in ["has_wifi", "has_ac", "has_washing_machine", "has_parking", "has_housekeeping",
                  "has_cctv", "has_drinking_water", "has_power_backup", "has_attached_washroom",
                  "has_refrigerator", "has_biometric_access"]:
            if k in fac:
                setattr(prop.facilities, k, bool(fac[k]))

    db.session.commit()
    log_audit("PROPERTY_UPDATE", "pg_properties", prop.id, {"updated_fields": list(data.keys())}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Property updated successfully.",
        "data": prop.to_dict(include_details=True)
    }), 200

@property_bp.route("/<int:property_id>/photos", methods=["POST"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def upload_property_photo(property_id):
    current_user = get_current_user()
    prop = PGProperty.query.get(property_id)
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")

    if current_user.role == "OWNER":
        profile = OwnerProfile.query.filter_by(user_id=current_user.id).first()
        if not profile or prop.owner_id != profile.id:
            raise APIException("Access denied.", status_code=403, code="FORBIDDEN")

    if "file" not in request.files:
        raise APIException("No photo file uploaded.", status_code=400, code="VALIDATION_ERROR")

    file_obj = request.files["file"]
    caption = request.form.get("caption", "PG View")
    is_primary = request.form.get("is_primary", "false").lower() == "true"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    rel_path = save_uploaded_file(file_obj, upload_folder, subfolder="properties")

    if is_primary:
        # unset previous primaries
        PropertyPhoto.query.filter_by(property_id=prop.id).update({"is_primary": False})

    photo = PropertyPhoto(
        property_id=prop.id,
        file_path=rel_path,
        caption=caption,
        is_primary=is_primary
    )
    db.session.add(photo)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Property photo uploaded successfully.",
        "data": photo.to_dict()
    }), 201

@property_bp.route("/owner/my-properties", methods=["GET"])
@jwt_required()
@role_required("OWNER")
def get_my_properties():
    current_user = get_current_user()
    profile = OwnerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"success": True, "data": []}), 200

    properties = PGProperty.query.filter_by(owner_id=profile.id).order_by(PGProperty.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [p.to_dict(include_details=True) for p in properties]
    }), 200
