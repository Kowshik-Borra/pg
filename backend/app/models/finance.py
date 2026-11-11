from datetime import datetime, timezone
from app.extensions import db

class RentInvoice(db.Model):
    __tablename__ = "rent_invoices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    allocation_id = db.Column(db.Integer, db.ForeignKey("room_allocations.id", ondelete="CASCADE"), nullable=False)
    billing_month = db.Column(db.Integer, nullable=False)
    billing_year = db.Column(db.Integer, nullable=False)
    base_rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    electricity_charges = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    food_charges = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    late_fee_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total_amount_due = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum("PENDING", "PARTIALLY_PAID", "PAID", "OVERDUE", name="invoice_status_type"),
        default="PENDING",
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    property = db.relationship("PGProperty", backref="invoices")
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "property_id": self.property_id,
            "property_name": self.property.name if self.property else None,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant.user.full_name if self.tenant and self.tenant.user else None,
            "billing_month": self.billing_month,
            "billing_year": self.billing_year,
            "base_rent_amount": float(self.base_rent_amount) if self.base_rent_amount else 0.0,
            "electricity_charges": float(self.electricity_charges) if self.electricity_charges else 0.0,
            "food_charges": float(self.food_charges) if self.food_charges else 0.0,
            "late_fee_amount": float(self.late_fee_amount) if self.late_fee_amount else 0.0,
            "total_amount_due": float(self.total_amount_due) if self.total_amount_due else 0.0,
            "amount_paid": float(self.amount_paid) if self.amount_paid else 0.0,
            "balance_due": float(self.total_amount_due - self.amount_paid) if self.total_amount_due else 0.0,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("rent_invoices.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.Enum("CASH", "UPI", "BANK_TRANSFER", "CHEQUE", name="payment_method_type"), nullable=False)
    transaction_reference = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum("COMPLETED", "PENDING_VERIFICATION", "REFUNDED", name="payment_status_type"),
        default="COMPLETED",
        nullable=False
    )
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    verified_by = db.relationship("User", foreign_keys=[verified_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "payment_reference": self.payment_reference,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice.invoice_number if self.invoice else None,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant.user.full_name if self.tenant and self.tenant.user else None,
            "amount": float(self.amount) if self.amount else 0.0,
            "payment_method": self.payment_method,
            "transaction_reference": self.transaction_reference,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "status": self.status,
            "verified_by": self.verified_by.full_name if self.verified_by else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SecurityDeposit(db.Model):
    __tablename__ = "security_deposits"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    amount_deposited = db.Column(db.Numeric(10, 2), nullable=False)
    deposit_date = db.Column(db.Date, nullable=False)
    deductions_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    deduction_reason = db.Column(db.Text, nullable=True)
    refund_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    refund_date = db.Column(db.Date, nullable=True)
    refund_status = db.Column(
        db.Enum("HELD", "PARTIALLY_REFUNDED", "FULLY_REFUNDED", name="deposit_refund_status"),
        default="HELD",
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    property = db.relationship("PGProperty", backref="security_deposits")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "property_id": self.property_id,
            "property_name": self.property.name if self.property else None,
            "amount_deposited": float(self.amount_deposited) if self.amount_deposited else 0.0,
            "deposit_date": self.deposit_date.isoformat() if self.deposit_date else None,
            "deductions_amount": float(self.deductions_amount) if self.deductions_amount else 0.0,
            "deduction_reason": self.deduction_reason,
            "refund_amount": float(self.refund_amount) if self.refund_amount else 0.0,
            "refund_date": self.refund_date.isoformat() if self.refund_date else None,
            "refund_status": self.refund_status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    category = db.Column(
        db.Enum("ELECTRICITY", "WATER", "MAINTENANCE", "INTERNET", "GROCERY_FOOD", "SALARY", "TAX", "MISCELLANEOUS", name="expense_category_type"),
        nullable=False
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    receipt_file_path = db.Column(db.String(255), nullable=True)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    recorded_by = db.relationship("User", foreign_keys=[recorded_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "category": self.category,
            "amount": float(self.amount) if self.amount else 0.0,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "description": self.description,
            "receipt_file_path": self.receipt_file_path,
            "recorded_by": self.recorded_by.full_name if self.recorded_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
