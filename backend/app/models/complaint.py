import uuid
from datetime import datetime, timezone
from app.extensions import db

class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    category = db.Column(
        db.Enum("PLUMBING", "ELECTRICAL", "WIFI_NETWORK", "CLEANING", "FOOD_QUALITY", "NOISE_DISTURBANCE", "OTHER", name="complaint_category_type"),
        nullable=False
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_file_path = db.Column(db.String(255), nullable=True)
    priority = db.Column(
        db.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="complaint_priority_type"),
        default="MEDIUM",
        nullable=False
    )
    status = db.Column(
        db.Enum("OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", name="complaint_status_type"),
        default="OPEN",
        nullable=False,
        index=True
    )
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    assigned_staff = db.relationship("Staff", foreign_keys=[assigned_staff_id])
    updates = db.relationship("ComplaintUpdate", backref="complaint", cascade="all, delete-orphan", order_by="ComplaintUpdate.created_at.desc()")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "property_id": self.property_id,
            "property_name": self.property.name if self.property else None,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant.user.full_name if self.tenant and self.tenant.user else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "photo_file_path": self.photo_file_path,
            "priority": self.priority,
            "status": self.status,
            "assigned_staff_name": self.assigned_staff.full_name if self.assigned_staff else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updates": [u.to_dict() for u in self.updates]
        }

class ComplaintUpdate(db.Model):
    __tablename__ = "complaint_updates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "status": self.status,
            "note": self.note,
            "updated_by": self.updated_by.full_name if self.updated_by else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

