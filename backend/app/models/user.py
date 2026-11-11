import uuid
from datetime import datetime, timezone
import bcrypt
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    role = db.Column(db.Enum("SUPER_ADMIN", "OWNER", "MANAGER", "TENANT", name="user_roles"), nullable=False, default="TENANT")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    owner_profile = db.relationship("OwnerProfile", backref="user", uselist=False, cascade="all, delete-orphan", foreign_keys="OwnerProfile.user_id")
    tenant_profile = db.relationship("Tenant", backref="user", uselist=False, cascade="all, delete-orphan")
    manager_assignments = db.relationship("ManagerAssignment", backref="manager", cascade="all, delete-orphan", foreign_keys="ManagerAssignment.manager_user_id")
    notifications = db.relationship("Notification", backref="user", cascade="all, delete-orphan")
    wishlist_items = db.relationship("Wishlist", backref="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class OwnerProfile(db.Model):
    __tablename__ = "owner_profiles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    pan_number = db.Column(db.String(20), nullable=True)
    aadhaar_last4 = db.Column(db.String(4), nullable=True)
    bank_account_number = db.Column(db.String(50), nullable=True)
    bank_ifsc = db.Column(db.String(20), nullable=True)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    properties = db.relationship("PGProperty", backref="owner_profile", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "business_name": self.business_name,
            "pan_number": self.pan_number,
            "aadhaar_last4": self.aadhaar_last4,
            "is_approved": self.is_approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None
        }

class ManagerAssignment(db.Model):
    __tablename__ = "manager_assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    manager_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    can_manage_payments = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_complaints = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("manager_user_id", "property_id", name="uq_manager_property"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "manager_user_id": self.manager_user_id,
            "property_id": self.property_id,
            "can_manage_payments": self.can_manage_payments,
            "can_manage_complaints": self.can_manage_complaints,
            "is_active": self.is_active,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None
        }

class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role_designation = db.Column(db.String(60), nullable=False)  # Cook, Housekeeping, Security
    phone = db.Column(db.String(20), nullable=False)
    salary_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "full_name": self.full_name,
            "role_designation": self.role_designation,
            "phone": self.phone,
            "salary_amount": float(self.salary_amount) if self.salary_amount else 0.0,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
