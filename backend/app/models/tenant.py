from datetime import datetime, timezone
from app.extensions import db

class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    emergency_contact_name = db.Column(db.String(120), nullable=False)
    emergency_contact_phone = db.Column(db.String(20), nullable=False)
    emergency_contact_relation = db.Column(db.String(50), nullable=False)
    id_proof_type = db.Column(db.String(50), nullable=True)  # Deprecated / optional for privacy
    id_proof_number_masked = db.Column(db.String(50), nullable=True)
    college_or_company_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    allocations = db.relationship("RoomAllocation", backref="tenant", cascade="all, delete-orphan")
    invoices = db.relationship("RentInvoice", backref="tenant", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="tenant", cascade="all, delete-orphan")
    security_deposits = db.relationship("SecurityDeposit", backref="tenant", cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", backref="tenant", cascade="all, delete-orphan")
    visitor_logs = db.relationship("VisitorLog", backref="tenant", cascade="all, delete-orphan")

    def to_dict(self):
        active_alloc = next((a for a in self.allocations if a.is_active), None)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user": self.user.to_dict() if self.user else None,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relation": self.emergency_contact_relation,
            "college_or_company_name": self.college_or_company_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "active_allocation": active_alloc.to_dict() if active_alloc else None
        }

class RoomAllocation(db.Model):
    __tablename__ = "room_allocations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    bed_id = db.Column(db.Integer, db.ForeignKey("beds.id", ondelete="CASCADE"), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=True)
    monthly_rent_agreed = db.Column(db.Numeric(10, 2), nullable=False)
    security_deposit_paid = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    invoices = db.relationship("RentInvoice", backref="allocation", cascade="all, delete-orphan")
    review = db.relationship("Review", backref="allocation", uselist=False)

    def to_dict(self):
        bed_obj = self.bed
        room_obj = bed_obj.room if bed_obj else None
        prop_obj = room_obj.property if room_obj else None
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "bed_id": self.bed_id,
            "bed_label": bed_obj.bed_label if bed_obj else None,
            "room_number": room_obj.room_number if room_obj else None,
            "property_id": prop_obj.id if prop_obj else None,
            "property_name": prop_obj.name if prop_obj else None,
            "check_in_date": self.check_in_date.isoformat() if self.check_in_date else None,
            "check_out_date": self.check_out_date.isoformat() if self.check_out_date else None,
            "monthly_rent_agreed": float(self.monthly_rent_agreed) if self.monthly_rent_agreed else 0.0,
            "security_deposit_paid": float(self.security_deposit_paid) if self.security_deposit_paid else 0.0,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class VisitorLog(db.Model):
    __tablename__ = "visitor_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    visitor_name = db.Column(db.String(120), nullable=False)
    visitor_phone = db.Column(db.String(20), nullable=False)
    visit_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.Time, nullable=False)
    check_out_time = db.Column(db.Time, nullable=True)
    relationship = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "tenant_id": self.tenant_id,
            "visitor_name": self.visitor_name,
            "visitor_phone": self.visitor_phone,
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "check_in_time": str(self.check_in_time) if self.check_in_time else None,
            "check_out_time": str(self.check_out_time) if self.check_out_time else None,
            "relationship": self.relationship
        }

