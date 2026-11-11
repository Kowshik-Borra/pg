from flask import request
from app.extensions import db
from app.models.governance import AuditLog

def log_audit(action: str, entity_name: str, entity_id: int = None, details: dict = None, user_id: int = None):
    """
    Standardized audit logging utility.
    """
    try:
        ip = request.remote_addr if request else None
    except Exception:
        ip = None

    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            ip_address=ip,
            details_json=details or {}
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Non-blocking logging failure
        print(f"Warning: Failed to write audit log: {e}")
