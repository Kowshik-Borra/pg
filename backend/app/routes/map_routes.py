from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.property import PGProperty
from app.models.user import OwnerProfile
from app.utils.geo import haversine_distance_km
from app.schemas.validators import validate_coordinates
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user

map_bp = Blueprint("maps", __name__, url_prefix="/api/maps")

@map_bp.route("/nearby", methods=["GET"])
def get_nearby_properties():
    lat_val = request.args.get("lat")
    lng_val = request.args.get("lng")
    radius_km = request.args.get("radius", default=10.0, type=float)

    if not lat_val or not lng_val:
        raise APIException("Latitude and Longitude query parameters are required.", status_code=400, code="VALIDATION_ERROR")

    user_lat, user_lng = validate_coordinates(lat_val, lng_val)
    properties = PGProperty.query.filter_by(is_active=True, is_verified=True).all()

    results = []
    for prop in properties:
        if prop.latitude and prop.longitude:
            dist = haversine_distance_km(user_lat, user_lng, float(prop.latitude), float(prop.longitude))
            if dist <= radius_km:
                prop_data = prop.to_dict()
                prop_data["distance_km"] = dist
                prop_data["google_maps_directions_url"] = f"https://www.google.com/maps/dir/?api=1&destination={float(prop.latitude)},{float(prop.longitude)}"
                results.append(prop_data)

    results.sort(key=lambda x: x["distance_km"])

    return jsonify({
        "success": True,
        "data": {
            "user_coordinates": {"latitude": user_lat, "longitude": user_lng},
            "radius_km": radius_km,
            "count": len(results),
            "properties": results
        }
    }), 200

@map_bp.route("/markers", methods=["GET"])
def get_all_markers():
    city = request.args.get("city", "").strip()
    locality = request.args.get("locality", "").strip()
    gender = request.args.get("gender", "").strip().upper()

    # Public map only shows active AND verified properties
    query = PGProperty.query.filter_by(is_active=True, is_verified=True)
    if city:
        query = query.filter(PGProperty.city.ilike(f"%{city}%"))
    if locality:
        query = query.filter(PGProperty.locality.ilike(f"%{locality}%"))
    if gender in ["BOYS", "GIRLS", "CO_ED"]:
        query = query.filter(PGProperty.property_type == gender)

    properties = query.all()

    markers = []
    for p in properties:
        if p.latitude and p.longitude:
            markers.append({
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "latitude": float(p.latitude),
                "longitude": float(p.longitude),
                "property_type": p.property_type,
                "locality": p.locality,
                "city": p.city,
                "available_beds": sum(1 for r in p.rooms for b in r.beds if b.status == "AVAILABLE"),
                "min_rent": float(min([r.monthly_rent_per_bed for r in p.rooms if r.is_active], default=0.0)),
                "is_verified": p.is_verified,
                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={float(p.latitude)},{float(p.longitude)}"
            })

    return jsonify({
        "success": True,
        "data": markers
    }), 200

@map_bp.route("/owner-properties", methods=["GET"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def get_owner_property_markers():
    """
    Returns property markers for the authenticated owner, including both
    verified and pending-verification properties.
    """
    current_user = get_current_user()
    if current_user.role == "SUPER_ADMIN":
        properties = PGProperty.query.filter_by(is_active=True).all()
    else:
        profile = OwnerProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            return jsonify({"success": True, "data": []}), 200
        properties = PGProperty.query.filter_by(owner_id=profile.id, is_active=True).all()

    markers = []
    for p in properties:
        if p.latitude and p.longitude:
            markers.append({
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "latitude": float(p.latitude),
                "longitude": float(p.longitude),
                "property_type": p.property_type,
                "locality": p.locality,
                "city": p.city,
                "address_line1": p.address_line1,
                "is_verified": p.is_verified,
                "available_beds": sum(1 for r in p.rooms for b in r.beds if b.status == "AVAILABLE"),
                "total_beds": sum(len(r.beds) for r in p.rooms),
                "min_rent": float(min([r.monthly_rent_per_bed for r in p.rooms if r.is_active], default=0.0)),
                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={float(p.latitude)},{float(p.longitude)}"
            })

    return jsonify({
        "success": True,
        "data": markers
    }), 200

