from flask import Blueprint, send_file
from flask_jwt_extended import jwt_required
from app.middleware.rbac import role_required, get_current_user
from app.middleware.error_handlers import APIException
from app.extensions import db
from app.models.finance import RentInvoice
from app.services.report_service import generate_pdf_receipt, generate_excel_financial_report

report_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

@report_bp.route("/invoices/<int:invoice_id>/pdf", methods=["GET"])
@jwt_required()
def download_invoice_pdf(invoice_id):
    current_user = get_current_user()
    invoice = db.session.get(RentInvoice, invoice_id)
    if not invoice:
        raise APIException("Invoice not found.", status_code=404, code="NOT_FOUND")

    # Access check: Tenant owning invoice, or owner/manager of property, or admin
    if current_user.role == "TENANT" and invoice.tenant.user_id != current_user.id:
        raise APIException("Access denied.", status_code=403, code="FORBIDDEN")

    pdf_stream = generate_pdf_receipt(invoice_id)
    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Receipt_{invoice.invoice_number}.pdf"
    )

@report_bp.route("/properties/<int:property_id>/excel", methods=["GET"])
@jwt_required()
@role_required("OWNER", "SUPER_ADMIN")
def download_property_excel(property_id):
    excel_stream = generate_excel_financial_report(property_id)
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Property_{property_id}_Rent_Report.xlsx"
    )

