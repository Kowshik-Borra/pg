from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.governance import Review, Wishlist
from app.models.tenant import Tenant, RoomAllocation
from app.models.property import PGProperty
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.services.audit_service import log_audit

review_bp = Blueprint("reviews", __name__, url_prefix="/api")

@review_bp.route("/reviews", methods=["POST"])
@jwt_required()
@role_required("TENANT")
def submit_review():
    current_user = get_current_user()
    tenant = Tenant.query.filter_by(user_id=current_user.id).first()
    if not tenant:
        raise APIException("Tenant profile required to review.", status_code=400, code="PROFILE_NOT_FOUND")

    data = request.get_json() or {}
    allocation_id = data.get("allocation_id")
    rating = data.get("rating")
    cleanliness = data.get("cleanliness_rating") or rating
    food_rating = data.get("food_rating") or rating
    comment = (data.get("comment") or "").strip()

    if not allocation_id or not rating or not comment:
        raise APIException("Allocation ID, rating (1-5), and written comment are required.", status_code=400, code="VALIDATION_ERROR")

    try:
        rating = int(rating)
        cleanliness = int(cleanliness)
        food_rating = int(food_rating)
    except ValueError:
        raise APIException("Ratings must be integers between 1 and 5.", status_code=400, code="VALIDATION_ERROR")

    for r in [rating, cleanliness, food_rating]:
        if not (1 <= r <= 5):
            raise APIException("All ratings must be between 1 and 5.", status_code=400, code="VALIDATION_ERROR")

    allocation = RoomAllocation.query.get(allocation_id)
    if not allocation or allocation.tenant_id != tenant.id:
        raise APIException("You can only review a property where you have a verified stay record.", status_code=403, code="FORBIDDEN")

    existing = Review.query.filter_by(allocation_id=allocation_id).first()
    if existing:
        raise APIException("You have already submitted a review for this stay.", status_code=409, code="CONFLICT")

    prop_id = allocation.bed.room.property_id
    review = Review(
        property_id=prop_id,
        user_id=current_user.id,
        allocation_id=allocation_id,
        rating=rating,
        cleanliness_rating=cleanliness,
        food_rating=food_rating,
        comment=comment,
        is_approved=True
    )
    db.session.add(review)
    db.session.commit()

    log_audit("SUBMIT_REVIEW", "reviews", review.id, {"rating": rating, "property_id": prop_id}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Verified review published successfully.",
        "data": review.to_dict()
    }), 201

@review_bp.route("/properties/<int:property_id>/reviews", methods=["GET"])
def get_property_reviews(property_id):
    reviews = Review.query.filter_by(property_id=property_id, is_approved=True).order_by(Review.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [r.to_dict() for r in reviews]
    }), 200

@review_bp.route("/wishlist", methods=["GET"])
@jwt_required()
@role_required("TENANT")
def get_wishlist():
    current_user = get_current_user()
    items = Wishlist.query.filter_by(user_id=current_user.id).order_by(Wishlist.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [w.to_dict() for w in items]
    }), 200

@review_bp.route("/wishlist/<int:property_id>", methods=["POST"])
@jwt_required()
@role_required("TENANT")
def add_to_wishlist(property_id):
    current_user = get_current_user()
    prop = PGProperty.query.get(property_id)
    if not prop or not prop.is_active:
        raise APIException("Property not found or inactive.", status_code=404, code="NOT_FOUND")

    existing = Wishlist.query.filter_by(user_id=current_user.id, property_id=property_id).first()
    if existing:
        return jsonify({
            "success": True,
            "message": "Property is already in your wishlist.",
            "data": existing.to_dict()
        }), 200

    wishlist = Wishlist(user_id=current_user.id, property_id=property_id)
    db.session.add(wishlist)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Property added to wishlist.",
        "data": wishlist.to_dict()
    }), 201

@review_bp.route("/wishlist/<int:property_id>", methods=["DELETE"])
@jwt_required()
@role_required("TENANT")
def remove_from_wishlist(property_id):
    current_user = get_current_user()
    item = Wishlist.query.filter_by(user_id=current_user.id, property_id=property_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()

    return jsonify({
        "success": True,
        "message": "Property removed from wishlist."
    }), 200
