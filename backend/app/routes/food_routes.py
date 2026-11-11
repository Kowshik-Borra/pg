from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.food import FoodMenu
from app.models.property import PGProperty
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.services.audit_service import log_audit

food_bp = Blueprint("food", __name__, url_prefix="/api/food")

@food_bp.route("/property/<int:property_id>", methods=["GET"])
def get_property_menu(property_id):
    prop = PGProperty.query.get(property_id)
    if not prop or not prop.is_active:
        raise APIException("Property not found or inactive.", status_code=404, code="NOT_FOUND")

    menus = FoodMenu.query.filter_by(property_id=property_id).all()
    # Group by day of week
    schedule = {
        "MONDAY": [], "TUESDAY": [], "WEDNESDAY": [], "THURSDAY": [],
        "FRIDAY": [], "SATURDAY": [], "SUNDAY": []
    }
    for m in menus:
        if m.day_of_week in schedule:
            schedule[m.day_of_week].append(m.to_dict())

    return jsonify({
        "success": True,
        "data": {
            "property_id": property_id,
            "property_name": prop.name,
            "schedule": schedule,
            "all_items": [m.to_dict() for m in menus]
        }
    }), 200

@food_bp.route("/property/<int:property_id>/meal", methods=["POST", "PUT"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def update_or_create_meal(property_id):
    current_user = get_current_user()
    data = request.get_json() or {}

    day = (data.get("day_of_week") or "").strip().upper()
    meal = (data.get("meal_type") or "").strip().upper()
    items = (data.get("items_menu") or "").strip()
    is_veg = bool(data.get("is_veg", True))
    dietary_notes = (data.get("special_dietary_notes") or "").strip()

    valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    valid_meals = ["BREAKFAST", "LUNCH", "DINNER", "EVENING_SNACKS"]

    if day not in valid_days or meal not in valid_meals:
        raise APIException("Invalid day of week or meal type.", status_code=400, code="VALIDATION_ERROR")

    if not items:
        raise APIException("Menu items description is required.", status_code=400, code="VALIDATION_ERROR")

    existing = FoodMenu.query.filter_by(property_id=property_id, day_of_week=day, meal_type=meal).first()
    if existing:
        existing.items_menu = items
        existing.is_veg = is_veg
        existing.special_dietary_notes = dietary_notes
        existing.updated_at = datetime.now(timezone.utc)
        menu_item = existing
    else:
        menu_item = FoodMenu(
            property_id=property_id,
            day_of_week=day,
            meal_type=meal,
            items_menu=items,
            is_veg=is_veg,
            special_dietary_notes=dietary_notes
        )
        db.session.add(menu_item)

    db.session.commit()
    log_audit("UPDATE_FOOD_MENU", "food_menus", menu_item.id, {"day": day, "meal": meal}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"{day} {meal} menu updated successfully.",
        "data": menu_item.to_dict()
    }), 200
