import io
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.finance import RentInvoice, Payment
from app.models.property import PGProperty
from app.models.tenant import RoomAllocation
from app.middleware.error_handlers import APIException

def generate_pdf_receipt(invoice_id: int) -> io.BytesIO:
    invoice = RentInvoice.query.get(invoice_id)
    if not invoice:
        raise APIException("Invoice not found.", status_code=404, code="NOT_FOUND")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#111827"),
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B")
    )
    normal_style = styles["Normal"]
    bold_style = ParagraphStyle(
        "BoldStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold"
    )

    elements = []

    # Header
    elements.append(Paragraph("PG CONNECT - OFFICIAL RENT INVOICE & RECEIPT", title_style))
    elements.append(Paragraph(f"Invoice Number: {invoice.invoice_number} | Status: {invoice.status}", subtitle_style))
    elements.append(Spacer(1, 15))

    # Property and Tenant Information Table
    prop = invoice.property
    tenant = invoice.tenant
    tenant_name = tenant.user.full_name if tenant and tenant.user else "Resident"
    prop_name = prop.name if prop else "PG Property"
    prop_address = f"{prop.address_line1}, {prop.locality}, {prop.city} - {prop.pincode}" if prop else ""

    info_data = [
        [Paragraph("<b>Property Details:</b>", normal_style), Paragraph("<b>Tenant Details:</b>", normal_style)],
        [Paragraph(prop_name, bold_style), Paragraph(tenant_name, bold_style)],
        [Paragraph(prop_address, normal_style), Paragraph(f"Phone: {tenant.user.phone if tenant and tenant.user else ''}", normal_style)],
        [Paragraph(f"Contact: {prop.contact_phone if prop else ''}", normal_style), Paragraph(f"Due Date: {invoice.due_date.isoformat()}", normal_style)]
    ]

    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Line Items Breakdown Table
    breakdown_data = [
        [Paragraph("<b>Description</b>", bold_style), Paragraph("<b>Amount (INR)</b>", bold_style)],
        [f"Base Monthly Room Rent ({invoice.billing_month}/{invoice.billing_year})", f"{float(invoice.base_rent_amount):.2f}"],
        ["Electricity & Utility Charges", f"{float(invoice.electricity_charges):.2f}"],
        ["Food & Mess Charges", f"{float(invoice.food_charges):.2f}"],
        ["Late Payment Surcharge", f"{float(invoice.late_fee_amount):.2f}"],
        [Paragraph("<b>Total Amount Billed</b>", bold_style), Paragraph(f"<b>Rs. {float(invoice.total_amount_due):.2f}</b>", bold_style)],
        [Paragraph("<b>Total Amount Paid</b>", bold_style), Paragraph(f"<b>Rs. {float(invoice.amount_paid):.2f}</b>", bold_style)],
        [Paragraph("<b>Outstanding Balance Due</b>", bold_style), Paragraph(f"<b>Rs. {float(invoice.total_amount_due - invoice.amount_paid):.2f}</b>", bold_style)]
    ]

    breakdown_table = Table(breakdown_data, colWidths=[380, 160])
    breakdown_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, -3), (-1, -1), colors.HexColor("#F1F5F9")),
    ]))
    elements.append(breakdown_table)
    elements.append(Spacer(1, 25))

    # Footer note
    elements.append(Paragraph("This is a computer-generated receipt from the PG Connect platform. No signature required.", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_excel_financial_report(property_id: int) -> io.BytesIO:
    prop = PGProperty.query.get(property_id)
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")

    invoices = RentInvoice.query.filter_by(property_id=property_id).order_by(RentInvoice.created_at.desc()).all()
    records = []
    for inv in invoices:
        records.append({
            "Invoice Number": inv.invoice_number,
            "Tenant Name": inv.tenant.user.full_name if inv.tenant and inv.tenant.user else "N/A",
            "Month": inv.billing_month,
            "Year": inv.billing_year,
            "Base Rent (INR)": float(inv.base_rent_amount),
            "Electricity (INR)": float(inv.electricity_charges),
            "Food (INR)": float(inv.food_charges),
            "Late Fee (INR)": float(inv.late_fee_amount),
            "Total Due (INR)": float(inv.total_amount_due),
            "Amount Paid (INR)": float(inv.amount_paid),
            "Balance Due (INR)": float(inv.total_amount_due - inv.amount_paid),
            "Due Date": inv.due_date.isoformat(),
            "Status": inv.status
        })

    df = pd.DataFrame(records)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Invoices and Rent")

    output.seek(0)
    return output
