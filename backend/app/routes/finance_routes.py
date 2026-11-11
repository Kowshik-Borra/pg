from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.finance import RentInvoice, Payment, Expense, SecurityDeposit
from app.models.tenant import Tenant, RoomAllocation
from app.models.property import PGProperty
from app.models.user import OwnerProfile, ManagerAssignment
from app.middleware.error_handlers import APIException
from app.middleware.rbac import role_required, get_current_user
from app.schemas.validators import validate_positive_amount
from app.services.finance_service import (
    generate_invoice_for_allocation,
    record_payment,
    get_property_financial_summary
)
from app.services.audit_service import log_audit

finance_bp = Blueprint("finance", __name__, url_prefix="/api/finance")

@finance_bp.route("/invoices", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def create_invoice():
    data = request.get_json() or {}
    alloc_id = data.get("allocation_id")
    month = data.get("billing_month")
    year = data.get("billing_year")

    if not alloc_id or not month or not year:
        raise APIException("Allocation ID, billing month, and billing year are required.", status_code=400, code="VALIDATION_ERROR")

    electricity = validate_positive_amount(data.get("electricity_charges", 0.0), "Electricity charges")
    food = validate_positive_amount(data.get("food_charges", 0.0), "Food charges")
    late_fee = validate_positive_amount(data.get("late_fee_amount", 0.0), "Late fee")

    invoice = generate_invoice_for_allocation(
        allocation_id=alloc_id,
        month=int(month),
        year=int(year),
        electricity=electricity,
        food=food,
        late_fee=late_fee
    )

    return jsonify({
        "success": True,
        "message": f"Invoice {invoice.invoice_number} created successfully.",
        "data": invoice.to_dict()
    }), 201

@finance_bp.route("/payments", methods=["POST"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def make_payment():
    current_user = get_current_user()
    data = request.get_json() or {}

    invoice_id = data.get("invoice_id")
    amount = validate_positive_amount(data.get("amount"), "Payment amount")
    method = (data.get("payment_method") or "").strip().upper()
    tx_ref = data.get("transaction_reference")
    notes = data.get("notes")

    if not invoice_id:
        raise APIException("Invoice ID is required.", status_code=400, code="VALIDATION_ERROR")

    if method not in ["CASH", "UPI", "BANK_TRANSFER", "CHEQUE"]:
        raise APIException("Payment method must be CASH, UPI, BANK_TRANSFER, or CHEQUE.", status_code=400, code="VALIDATION_ERROR")

    payment = record_payment(
        invoice_id=invoice_id,
        amount=amount,
        method=method,
        transaction_ref=tx_ref,
        notes=notes,
        recorded_by_user_id=current_user.id
    )

    return jsonify({
        "success": True,
        "message": f"Payment of Rs. {amount:.2f} recorded.",
        "data": payment.to_dict()
    }), 201

@finance_bp.route("/invoices/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def list_property_invoices(property_id):
    invoices = RentInvoice.query.filter_by(property_id=property_id).order_by(RentInvoice.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [inv.to_dict() for inv in invoices]
    }), 200

@finance_bp.route("/invoices/my-invoices", methods=["GET"])
@jwt_required()
@role_required("TENANT")
def list_my_invoices():
    current_user = get_current_user()
    tenant = Tenant.query.filter_by(user_id=current_user.id).first()
    if not tenant:
        return jsonify({"success": True, "data": []}), 200

    invoices = RentInvoice.query.filter_by(tenant_id=tenant.id).order_by(RentInvoice.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [inv.to_dict() for inv in invoices]
    }), 200

@finance_bp.route("/expenses", methods=["POST"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def record_expense():
    current_user = get_current_user()
    data = request.get_json() or {}

    property_id = data.get("property_id")
    category = (data.get("category") or "").strip().upper()
    amount = validate_positive_amount(data.get("amount"), "Expense amount")
    desc = (data.get("description") or "").strip()
    exp_date_str = data.get("expense_date") or date.today().isoformat()

    if not property_id or not desc:
        raise APIException("Property ID and description are required.", status_code=400, code="VALIDATION_ERROR")

    if category not in ["ELECTRICITY", "WATER", "MAINTENANCE", "INTERNET", "GROCERY_FOOD", "SALARY", "TAX", "MISCELLANEOUS"]:
        raise APIException("Invalid expense category.", status_code=400, code="VALIDATION_ERROR")

    try:
        exp_date_val = date.fromisoformat(exp_date_str)
    except ValueError:
        raise APIException("Invalid date format.", status_code=400, code="VALIDATION_ERROR")

    expense = Expense(
        property_id=property_id,
        category=category,
        amount=amount,
        expense_date=exp_date_val,
        description=desc,
        recorded_by_user_id=current_user.id
    )
    db.session.add(expense)
    db.session.commit()

    log_audit("RECORD_EXPENSE", "expenses", expense.id, {"category": category, "amount": amount}, user_id=current_user.id)

    return jsonify({
        "success": True,
        "message": "Expense recorded successfully.",
        "data": expense.to_dict()
    }), 201

@finance_bp.route("/expenses/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def list_property_expenses(property_id):
    expenses = Expense.query.filter_by(property_id=property_id).order_by(Expense.expense_date.desc()).all()
    return jsonify({
        "success": True,
        "data": [e.to_dict() for e in expenses]
    }), 200

@finance_bp.route("/summary/property/<int:property_id>", methods=["GET"])
@jwt_required()
@role_required("OWNER", "MANAGER", "SUPER_ADMIN")
def get_financial_summary(property_id):
    summary = get_property_financial_summary(property_id)
    return jsonify({
        "success": True,
        "data": summary
    }), 200
