from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.governance import Notification
from app.middleware.rbac import get_current_user

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

@notification_bp.route("", methods=["GET"])
@jwt_required()
def get_user_notifications():
    current_user = get_current_user()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(30).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return jsonify({
        "success": True,
        "data": {
            "unread_count": unread_count,
            "items": [n.to_dict() for n in notifications]
        }
    }), 200

@notification_bp.route("/<int:notif_id>/read", methods=["PATCH"])
@jwt_required()
def mark_notification_read(notif_id):
    current_user = get_current_user()
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    return jsonify({"success": True, "message": "Notification marked as read."}), 200

@notification_bp.route("/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_read():
    current_user = get_current_user()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True, "message": "All notifications marked as read."}), 200

