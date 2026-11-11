import uuid
from datetime import datetime, timezone
from app.extensions import db

class PGProperty(db.Model):
    __tablename__ = "pg_properties"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    owner_id = db.Column(db.Integer, db.ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    property_type = db.Column(db.Enum("BOYS", "GIRLS", "CO_ED", name="property_gender_type"), nullable=False)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)
    locality = db.Column(db.String(100), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False, index=True)
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rules = db.Column(db.Text, nullable=True)
    notice_period_days = db.Column(db.Integer, default=30, nullable=False)
    gate_closing_time = db.Column(db.String(20), default="22:30", nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    photos = db.relationship("PropertyPhoto", backref="property", cascade="all, delete-orphan")
    facilities = db.relationship("PropertyFacility", backref="property", uselist=False, cascade="all, delete-orphan")
    rooms = db.relationship("Room", backref="property", cascade="all, delete-orphan")
    food_menus = db.relationship("FoodMenu", backref="property", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="property", cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", backref="property", cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="property", cascade="all, delete-orphan")
    manager_assignments = db.relationship("ManagerAssignment", backref="property", cascade="all, delete-orphan")
    staff = db.relationship("Staff", backref="property", cascade="all, delete-orphan")

    def to_dict(self, include_details=False):
        data = {
            "id": self.id,
            "uuid": self.uuid,
            "owner_id": self.owner_id,
            "name": self.name,
            "slug": self.slug,
            "property_type": self.property_type,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "locality": self.locality,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "latitude": float(self.latitude) if self.latitude else 0.0,
            "longitude": float(self.longitude) if self.longitude else 0.0,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "description": self.description,
            "rules": self.rules,
            "notice_period_days": self.notice_period_days,
            "gate_closing_time": self.gate_closing_time,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "photos": [p.to_dict() for p in self.photos],
            "facilities": self.facilities.to_dict() if self.facilities else None
        }
        
        # Calculate real-time stats from actual rooms & beds
        total_rooms = len(self.rooms)
        total_beds = 0
        available_beds = 0
        occupied_beds = 0
        min_rent = None

        for room in self.rooms:
            if not room.is_active:
                continue
            if min_rent is None or (room.monthly_rent_per_bed and room.monthly_rent_per_bed < min_rent):
                min_rent = room.monthly_rent_per_bed
            for bed in room.beds:
                total_beds += 1
                if bed.status == "AVAILABLE":
                    available_beds += 1
                elif bed.status == "OCCUPIED":
                    occupied_beds += 1

        data["total_rooms"] = total_rooms
        data["total_beds"] = total_beds
        data["available_beds"] = available_beds
        data["occupied_beds"] = occupied_beds
        data["min_rent"] = float(min_rent) if min_rent is not None else 0.0

        if include_details:
            data["rooms"] = [r.to_dict(include_beds=True) for r in self.rooms if r.is_active]
            data["food_menus"] = [f.to_dict() for f in self.food_menus]
            
        return data

class PropertyPhoto(db.Model):
    __tablename__ = "property_photos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(100), nullable=True)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "file_path": self.file_path,
            "caption": self.caption,
            "is_primary": self.is_primary,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class PropertyFacility(db.Model):
    __tablename__ = "property_facilities"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), unique=True, nullable=False)
    has_wifi = db.Column(db.Boolean, default=True, nullable=False)
    has_ac = db.Column(db.Boolean, default=False, nullable=False)
    has_washing_machine = db.Column(db.Boolean, default=True, nullable=False)
    has_parking = db.Column(db.Boolean, default=True, nullable=False)
    has_housekeeping = db.Column(db.Boolean, default=True, nullable=False)
    has_cctv = db.Column(db.Boolean, default=True, nullable=False)
    has_drinking_water = db.Column(db.Boolean, default=True, nullable=False)
    has_power_backup = db.Column(db.Boolean, default=True, nullable=False)
    has_attached_washroom = db.Column(db.Boolean, default=False, nullable=False)
    has_refrigerator = db.Column(db.Boolean, default=False, nullable=False)
    has_biometric_access = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            "has_wifi": self.has_wifi,
            "has_ac": self.has_ac,
            "has_washing_machine": self.has_washing_machine,
            "has_parking": self.has_parking,
            "has_housekeeping": self.has_housekeeping,
            "has_cctv": self.has_cctv,
            "has_drinking_water": self.has_drinking_water,
            "has_power_backup": self.has_power_backup,
            "has_attached_washroom": self.has_attached_washroom,
            "has_refrigerator": self.has_refrigerator,
            "has_biometric_access": self.has_biometric_access
        }
