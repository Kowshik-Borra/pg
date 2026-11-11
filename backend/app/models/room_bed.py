from datetime import datetime, timezone
from app.extensions import db

class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    floor_number = db.Column(db.Integer, default=1, nullable=False)
    sharing_type = db.Column(db.Enum("SINGLE", "DOUBLE", "TRIPLE", "FOUR", name="room_sharing_type"), nullable=False)
    has_ac = db.Column(db.Boolean, default=False, nullable=False)
    has_attached_bathroom = db.Column(db.Boolean, default=False, nullable=False)
    monthly_rent_per_bed = db.Column(db.Numeric(10, 2), nullable=False)
    security_deposit_per_bed = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("property_id", "room_number", name="uq_property_room_number"),
    )

    beds = db.relationship("Bed", backref="room", cascade="all, delete-orphan", lazy="joined")
    bookings = db.relationship("Booking", backref="room", cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", backref="room", cascade="all, delete-orphan")

    def to_dict(self, include_beds=True):
        data = {
            "id": self.id,
            "property_id": self.property_id,
            "room_number": self.room_number,
            "floor_number": self.floor_number,
            "sharing_type": self.sharing_type,
            "has_ac": self.has_ac,
            "has_attached_bathroom": self.has_attached_bathroom,
            "monthly_rent_per_bed": float(self.monthly_rent_per_bed) if self.monthly_rent_per_bed else 0.0,
            "security_deposit_per_bed": float(self.security_deposit_per_bed) if self.security_deposit_per_bed else 0.0,
            "is_active": self.is_active,
            "total_beds": len(self.beds),
            "available_beds": sum(1 for b in self.beds if b.status == "AVAILABLE")
        }
        if include_beds:
            data["beds"] = [b.to_dict() for b in self.beds]
        return data

class Bed(db.Model):
    __tablename__ = "beds"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    bed_label = db.Column(db.String(10), nullable=False)  # Bed A, Bed B, etc.
    status = db.Column(
        db.Enum("AVAILABLE", "RESERVED", "OCCUPIED", "MAINTENANCE", "INACTIVE", name="bed_status_type"),
        default="AVAILABLE",
        nullable=False,
        index=True
    )
    last_status_change = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("room_id", "bed_label", name="uq_room_bed_label"),
    )

    allocations = db.relationship("RoomAllocation", backref="bed", cascade="all, delete-orphan")
    bookings = db.relationship("Booking", backref="bed", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "bed_label": self.bed_label,
            "status": self.status,
            "last_status_change": self.last_status_change.isoformat() if self.last_status_change else None,
            "notes": self.notes
        }

