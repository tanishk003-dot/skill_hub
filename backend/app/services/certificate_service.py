import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.barcode import qr
from app.models.user import User
from app.models.phase9_models import IssuedCertificate, AseGamification, PublicVerifyRateLog

CERT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "certificates"))

def ensure_cert_dir():
    os.makedirs(CERT_DIR, exist_ok=True)

def generate_certificate_pdf(cert_uuid: str, student_name: str, course_title: str, issue_date_str: str) -> str:
    ensure_cert_dir()
    pdf_filename = f"{cert_uuid}.pdf"
    file_path = os.path.join(CERT_DIR, pdf_filename)

    # Landscape Letter (11 x 8.5 inches)
    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CertHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1 # Center
    )

    subtitle_style = ParagraphStyle(
        'CertSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )

    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )

    course_style = ParagraphStyle(
        'CertCourse',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#F97316'),
        alignment=1
    )

    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#334155'),
        alignment=1
    )

    meta_style = ParagraphStyle(
        'CertMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        alignment=0
    )

    elements = []
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("L&K SKILL HUB — CERTIFICATE OF COMPLETION", title_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Verified Technical Upskilling & Engineering Competency", subtitle_style))
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("This is to certify that", body_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(student_name, name_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("has successfully completed the curriculum and mastery evaluations for", body_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(course_title, course_style))
    elements.append(Spacer(1, 20))

    # Verification QR Code
    verify_url = f"http://localhost:4300/verify-certificate/{cert_uuid}"
    qr_widget = qr.QrCodeWidget(verify_url)
    qr_widget.barWidth = 65
    qr_widget.barHeight = 65
    qr_widget.qrVersion = 1

    d = Drawing(65, 65)
    d.add(qr_widget)

    info_text = (
        f"<b>Certificate ID:</b> {cert_uuid}<br/>"
        f"<b>Issue Date:</b> {issue_date_str}<br/>"
        f"<b>Verification:</b> Scan QR code or visit /verify-certificate/{cert_uuid}"
    )

    footer_table = Table([[d, Paragraph(info_text, meta_style)]], colWidths=[80, 500])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
    ]))

    elements.append(Spacer(1, 25))
    elements.append(footer_table)

    def draw_border(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#1E3A8A'))
        canvas.setLineWidth(3)
        canvas.rect(18, 18, landscape(letter)[0] - 36, landscape(letter)[1] - 36)
        canvas.setStrokeColor(colors.HexColor('#F97316'))
        canvas.setLineWidth(1)
        canvas.rect(22, 22, landscape(letter)[0] - 44, landscape(letter)[1] - 44)
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_border)
    return file_path

def issue_certificate(
    db: Session,
    ase_id: int,
    title: str,
    entity_type: str,
    entity_id: int
) -> IssuedCertificate:
    ase = db.query(User).filter(User.id == ase_id).first()
    if not ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    cert_uuid = str(uuid.uuid4())
    issue_dt = datetime.now(timezone.utc)
    date_str = issue_dt.strftime("%B %d, %Y")

    file_path = generate_certificate_pdf(cert_uuid, ase.name, title, date_str)

    cert = IssuedCertificate(
        cert_uuid=cert_uuid,
        ase_id=ase_id,
        title=title,
        entity_type=entity_type,
        entity_id=entity_id,
        issue_date=issue_dt,
        pdf_file_path=file_path,
        is_revoked=False
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert

def verify_certificate_public(db: Session, cert_uuid: str, client_ip: str) -> Dict[str, Any]:
    """
    Requirement 4: Rate limit public verify endpoint.
    Shows ONLY: first name + last initial (full name only if show_full_name_publicly enabled),
    course title, issue date, and status. No email, IDs, scores, or other data.
    """
    # 1. Rate limiting check (max 30 verify calls per minute per IP)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    ip_calls = db.query(PublicVerifyRateLog).filter(
        PublicVerifyRateLog.ip_address == client_ip,
        PublicVerifyRateLog.created_at >= cutoff
    ).count()

    if ip_calls >= 30:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before verifying more certificates."
        )

    db.add(PublicVerifyRateLog(ip_address=client_ip))
    db.commit()

    # 2. Fetch certificate
    cert = db.query(IssuedCertificate).filter(IssuedCertificate.cert_uuid == cert_uuid).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found or invalid identifier.")

    ase = db.query(User).filter(User.id == cert.ase_id).first()
    if not ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient record not found.")

    # Check gamification privacy setting for full name
    gam = db.query(AseGamification).filter(AseGamification.ase_id == ase.id).first()
    if gam and gam.show_full_name_publicly:
        display_name = ase.name
    else:
        parts = ase.name.split()
        first = parts[0] if parts else "Candidate"
        last_init = f" {parts[-1][0]}." if len(parts) > 1 else ""
        display_name = f"{first}{last_init}"

    status_str = "Revoked" if cert.is_revoked else "Valid"

    return {
        "status": status_str,
        "recipient_name": display_name,
        "course_title": cert.title,
        "issue_date": cert.issue_date.strftime("%B %d, %Y"),
        "certificate_id": cert.cert_uuid
    }
