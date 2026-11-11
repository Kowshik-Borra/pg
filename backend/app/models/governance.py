from datetime import datetime, timezone
from app.extensions import db

class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    allocation_id = db.Column(db.Integer, db.ForeignKey("room_allocations.id", ondelete="CASCADE"), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    cleanliness_rating = db.Column(db.Integer, nullable=False)
    food_rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    reviewer = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "user_id": self.user_id,
            "reviewer_name": self.reviewer.full_name if self.reviewer else "Verified Resident",
            "rating": self.rating,
            "cleanliness_rating": self.cleanliness_rating,
            "food_rating": self.food_rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Wishlist(db.Model):
    __tablename__ = "wishlists"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "property_id", name="uq_user_property_wishlist"),
    )

    property = db.relationship("PGProperty")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "property_id": self.property_id,
            "property": self.property.to_dict() if self.property else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # BOOKING, RENT, COMPLAINT, SYSTEM
    related_entity_type = db.Column(db.String(50), nullable=True)
    related_entity_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class PropertyVerification(db.Model):
    __tablename__ = "property_verifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(
        db.Enum("SUBMITTED", "IN_REVIEW", "APPROVED", "REJECTED", name="verification_status_type"),
        default="SUBMITTED",
        nullable=False
    )
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    property = db.relationship("PGProperty", backref="verification_records")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_admin_id])

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "property_name": self.property.name if self.property else None,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "reviewed_by": self.reviewer.full_name if self.reviewer else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # CREATE_BOOKING, APPROVE_PROPERTY, RECORD_PAYMENT, etc.
    entity_name = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    details_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "System",
            "action": self.action,
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "ip_address": self.ip_address,
            "details": self.details_json,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
