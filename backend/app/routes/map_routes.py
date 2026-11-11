from flask import Blueprint, request, jsonify
from app.models.property import PGProperty
from app.utils.geo import haversine_distance_km
from app.schemas.validators import validate_coordinates
from app.middleware.error_handlers import APIException

map_bp = Blueprint("maps", __name__, url_prefix="/api/maps")

@map_bp.route("/nearby", methods=["GET"])
def get_nearby_properties():
    lat_val = request.args.get("lat")
    lng_val = request.args.get("lng")
    radius_km = request.args.get("radius", default=10.0, type=float)

    if not lat_val or not lng_val:
        raise APIException("Latitude and Longitude query parameters are required.", status_code=400, code="VALIDATION_ERROR")

    user_lat, user_lng = validate_coordinates(lat_val, lng_val)
    properties = PGProperty.query.filter_by(is_active=True).all()

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
    query = PGProperty.query.filter_by(is_active=True)
    if city:
        query = query.filter(PGProperty.city.ilike(f"%{city}%"))
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
