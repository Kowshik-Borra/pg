import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.complaint import Complaint, ComplaintUpdate
from app.models.tenant import Tenant, RoomAllocation
from app.models.user import Staff
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.services.notification_service import send_notification
from app.services.audit_service import log_audit
from app.utils.file_uploader import save_uploaded_file

complaint_bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")

def generate_ticket_number():
    return f"TKT-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

@complaint_bp.route("", methods=["POST"])
@jwt_required()
@role_required("TENANT")
def submit_complaint():
    current_user = get_current_user()
    tenant = Tenant.query.filter_by(user_id=current_user.id).first()
    if not tenant:
        raise APIException("Tenant profile not found.", status_code=400, code="PROFILE_NOT_FOUND")

    active_alloc = RoomAllocation.query.filter_by(tenant_id=tenant.id, is_active=True).first()
    if not active_alloc:
        raise APIException("You must have an active room stay to file a complaint.", status_code=403, code="FORBIDDEN")

    category = (request.form.get("category") or "").strip().upper()
    title = (request.form.get("title") or "").strip()
    desc = (request.form.get("description") or "").strip()
    priority = (request.form.get("priority") or "MEDIUM").strip().upper()

    valid_cats = ["PLUMBING", "ELECTRICAL", "WIFI_NETWORK", "CLEANING", "FOOD_QUALITY", "NOISE_DISTURBANCE", "OTHER"]
    if category not in valid_cats:
        raise APIException(f"Invalid category. Allowed: {', '.join(valid_cats)}.", status_code=400, code="VALIDATION_ERROR")

    if not title or not desc:
        raise APIException("Title and description are required.", status_code=400, code="VALIDATION_ERROR")

    photo_path = None
    if "photo" in request.files and request.files["photo"].filename:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        photo_path = save_uploaded_file(request.files["photo"], upload_folder, subfolder="complaints")

    ticket_num = generate_ticket_number()
    bed = active_alloc.bed
    prop_id = bed.room.property_id

    complaint = Complaint(
        ticket_number=ticket_num,
        property_id=prop_id,
        tenant_id=tenant.id,
        room_id=bed.room_id,
        category=category,
        title=title,
        description=desc,
        photo_file_path=photo_path,
        priority=priority if priority in ["LOW", "MEDIUM", "HIGH", "URGENT"] else "MEDIUM",
        status="OPEN"
    )
    db.session.add(complaint)
    db.session.flush()

    # Initial history log
    init_update = ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by_user_id=current_user.id,
        status="OPEN",
        note="Ticket opened by tenant."
    )
    db.session.add(init_update)
    db.session.commit()

    log_audit("COMPLAINT_SUBMIT", "complaints", complaint.id, {"ticket": ticket_num, "category": category}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"Complaint registered under ticket #{ticket_num}.",
        "data": complaint.to_dict()
    }), 201

@complaint_bp.route("/my-complaints", methods=["GET"])
@jwt_required()
@role_required("TENANT")
def get_my_complaints():
    current_user = get_current_user()
    tenant = Tenant.query.filter_by(user_id=current_user.id).first()
    if not tenant:
        return jsonify({"success": True, "data": []}), 200

    complaints = Complaint.query.filter_by(tenant_id=tenant.id).order_by(Complaint.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [c.to_dict() for c in complaints]
    }), 200

@complaint_bp.route("/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def list_property_complaints(property_id):
    complaints = Complaint.query.filter_by(property_id=property_id).order_by(Complaint.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [c.to_dict() for c in complaints]
    }), 200

@complaint_bp.route("/<int:complaint_id>/status", methods=["PATCH"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def update_complaint_status(complaint_id):
    current_user = get_current_user()
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        raise APIException("Complaint not found.", status_code=404, code="NOT_FOUND")

    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip().upper()
    note = (data.get("note") or "").strip()
    staff_id = data.get("assigned_staff_id")

    valid_statuses = ["OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    if new_status not in valid_statuses:
        raise APIException(f"Invalid status. Allowed: {', '.join(valid_statuses)}.", status_code=400, code="VALIDATION_ERROR")

    if not note:
        raise APIException("A status update note or explanation is required.", status_code=400, code="VALIDATION_ERROR")

    complaint.status = new_status
    if staff_id:
        complaint.assigned_staff_id = staff_id

    if new_status in ["RESOLVED", "CLOSED"]:
        complaint.resolved_at = datetime.now(timezone.utc)

    update_record = ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by_user_id=current_user.id,
        status=new_status,
        note=note
    )
    db.session.add(update_record)
    db.session.commit()

    send_notification(
        complaint.tenant.user_id,
        "Complaint Update",
        f"Your ticket #{complaint.ticket_number} status is now {new_status}: {note}",
        "COMPLAINT",
        "complaints",
        complaint.id
    )

    log_audit("COMPLAINT_STATUS_UPDATE", "complaints", complaint.id, {"status": new_status, "note": note}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": f"Complaint status updated to {new_status}.",
        "data": complaint.to_dict()
    }), 200
