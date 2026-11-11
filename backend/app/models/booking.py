import uuid
from datetime import datetime, timezone
from app.extensions import db

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    bed_id = db.Column(db.Integer, db.ForeignKey("beds.id", ondelete="CASCADE"), nullable=True)
    preferred_move_in_date = db.Column(db.Date, nullable=False)
    sharing_type = db.Column(db.String(20), nullable=False)
    status = db.Column(
        db.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED", "COMPLETED", name="booking_status_type"),
        default="PENDING",
        nullable=False,
        index=True
    )
    admin_remarks = db.Column(db.Text, nullable=True)
    reservation_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    customer = db.relationship("User", backref="bookings", foreign_keys=[customer_id])
    property = db.relationship("PGProperty", backref="bookings", foreign_keys=[property_id])
    history = db.relationship("BookingHistory", backref="booking", cascade="all, delete-orphan", order_by="BookingHistory.recorded_at.desc()")

    def to_dict(self):
        return {
            "id": self.id,
            "booking_reference": self.booking_reference,
            "customer_id": self.customer_id,
            "customer_name": self.customer.full_name if self.customer else None,
            "customer_phone": self.customer.phone if self.customer else None,
            "customer_email": self.customer.email if self.customer else None,
            "property_id": self.property_id,
            "property_name": self.property.name if self.property else None,
            "property_city": self.property.city if self.property else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "bed_id": self.bed_id,
            "bed_label": self.bed.bed_label if self.bed else None,
            "preferred_move_in_date": self.preferred_move_in_date.isoformat() if self.preferred_move_in_date else None,
            "sharing_type": self.sharing_type,
            "status": self.status,
            "admin_remarks": self.admin_remarks,
            "reservation_expires_at": self.reservation_expires_at.isoformat() if self.reservation_expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class BookingHistory(db.Model):
    __tablename__ = "booking_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    from_status = db.Column(db.String(30), nullable=True)
    to_status = db.Column(db.String(30), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    changed_by = db.relationship("User", foreign_keys=[changed_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by.full_name if self.changed_by else "System",
            "change_reason": self.change_reason,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None
        }
