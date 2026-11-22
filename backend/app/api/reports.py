import io
import csv
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.assessment_attempt import AssessmentAttempt
from app.api.deps import get_current_user

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])

def sanitize_csv_cell(val: Any) -> str:
    """
    Prevents CSV Formula Injection by prepending a single quote
    if the cell starts with =, +, -, @, tab, or carriage return.
    """
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


@router.get("/ase/{attempt_id}/pdf")
def export_ase_pdf_report(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a PDF Performance Report for an Assessment Attempt.
    Enforces strict access permissions:
      - ASE can only download their own PDF.
      - Mentor can only download their assigned mentees' PDF.
      - Admin can download any.
      - Returns 403 Forbidden otherwise.
    """
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")

    # Permission check
    is_admin = (current_user.role == UserRole.ADMIN)
    is_owner_ase = (current_user.role == UserRole.ASE and attempt.ase_id == current_user.id)
    is_assigned_mentor = False

    if current_user.role == UserRole.MENTOR:
        mentor_rel = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == attempt.ase_id
        ).first()
        is_assigned_mentor = (mentor_rel is not None)

    if not (is_admin or is_owner_ase or is_assigned_mentor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to download this report"
        )

    # Build PDF in memory
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
    primary_color = colors.HexColor("#1E3A8A")
    accent_color = colors.HexColor("#F97316")
    success_color = colors.HexColor("#10B981")
    danger_color = colors.HexColor("#EF4444")
    dark_gray = colors.HexColor("#1F2937")
    light_bg = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=accent_color,
        fontName='Helvetica-Bold'
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=4
    )
    normal_style = ParagraphStyle(
        'DocNormal',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=dark_gray
    )
    badge_style_pass = ParagraphStyle(
        'BadgePass',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        textColor=success_color,
        fontName='Helvetica-Bold'
    )
    badge_style_fail = ParagraphStyle(
        'BadgeFail',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        textColor=danger_color,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("L&K SKILL HUB", subtitle_style))
    story.append(Paragraph("Candidate Assessment Performance Report", title_style))
    story.append(Spacer(1, 6))

    sub_date = attempt.submitted_at.strftime("%B %d, %Y %H:%M UTC") if attempt.submitted_at else "In Progress"
    status_label = Paragraph("PASSED", badge_style_pass) if attempt.passed else Paragraph("FAILED", badge_style_fail)

    meta_data = [
        [Paragraph("<b>Candidate:</b>", normal_style), Paragraph(attempt.ase.name if attempt.ase else "", normal_style),
         Paragraph("<b>Outcome:</b>", normal_style), status_label],
        [Paragraph("<b>Email:</b>", normal_style), Paragraph(attempt.ase.email if attempt.ase else "", normal_style),
         Paragraph("<b>Percentage:</b>", normal_style), Paragraph(f"<b>{attempt.percentage:.1f}%</b> (Req: {attempt.assignment.assessment.passing_percentage}%)", normal_style)],
        [Paragraph("<b>Assessment:</b>", normal_style), Paragraph(attempt.assignment.assessment.title if attempt.assignment else "", normal_style),
         Paragraph("<b>Score:</b>", normal_style), Paragraph(f"{attempt.total_score:.1f} / {attempt.max_score:.1f}", normal_style)],
        [Paragraph("<b>Submitted At:</b>", normal_style), Paragraph(sub_date, normal_style),
         Paragraph("<b>Status:</b>", normal_style), Paragraph(str(attempt.status.value), normal_style)]
    ]
    meta_table = Table(meta_data, colWidths=[80, 200, 70, 190])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Proctoring Summary
    story.append(Paragraph("Proctoring & Integrity Summary", h2_style))
    proctor_flag = "Flagged" if attempt.violation_count > 0 else "Clean (No Violations)"
    p_style = badge_style_fail if attempt.violation_count > 0 else badge_style_pass
    proctor_data = [
        [Paragraph("Security Status:", normal_style), Paragraph(proctor_flag, p_style)],
        [Paragraph("Total Violations Recorded:", normal_style), Paragraph(str(attempt.violation_count), normal_style)],
        [Paragraph("Auto-Submit Reason:", normal_style), Paragraph(attempt.auto_submit_reason or "N/A", normal_style)]
    ]
    proctor_table = Table(proctor_data, colWidths=[150, 390])
    proctor_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(proctor_table)
    story.append(Spacer(1, 10))

    # Section-wise Scores
    story.append(Paragraph("Section-Wise Performance", h2_style))
    sec_rows = [[Paragraph("<b>Section Title</b>", normal_style), Paragraph("<b>Score</b>", normal_style), Paragraph("<b>Max</b>", normal_style), Paragraph("<b>Percentage</b>", normal_style)]]
    for s in (attempt.section_scores or []):
        sec_rows.append([
            Paragraph(s.get("title", ""), normal_style),
            Paragraph(str(s.get("score", 0)), normal_style),
            Paragraph(str(s.get("max", 0)), normal_style),
            Paragraph(f"{s.get('percentage', 0):.1f}%", normal_style)
        ])
    if len(sec_rows) == 1:
        sec_rows.append([Paragraph("No sections recorded", normal_style), Paragraph("-", normal_style), Paragraph("-", normal_style), Paragraph("-", normal_style)])
    sec_table = Table(sec_rows, colWidths=[240, 100, 100, 100])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 10))

    # Competency Strengths & Focus Areas
    story.append(Paragraph("Competency & Skill Insights", h2_style))
    skill_rows = [[Paragraph("<b>Competency Area</b>", normal_style), Paragraph("<b>Proficiency Score</b>", normal_style), Paragraph("<b>Classification</b>", normal_style)]]
    for sk, pct in (attempt.skill_percentages or {}).items():
        cls_str = "Strength (>= 70%)" if pct >= 70.0 else ("Moderate (50-70%)" if pct >= 50.0 else "Needs Improvement (< 50%)")
        skill_rows.append([
            Paragraph(sk, normal_style),
            Paragraph(f"{pct:.1f}%", normal_style),
            Paragraph(cls_str, normal_style)
        ])
    if len(skill_rows) == 1:
        skill_rows.append([Paragraph("No skills evaluated", normal_style), Paragraph("-", normal_style), Paragraph("-", normal_style)])
    skill_table = Table(skill_rows, colWidths=[240, 150, 150])
    skill_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(skill_table)
    story.append(Spacer(1, 14))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=6))
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"<i>Report generated by L&K Skill Hub automated examination platform on {gen_time}.</i>", ParagraphStyle('F', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor("#64748B"))))

    doc.build(story)
    buffer.seek(0)

    filename = f"skillhub_report_attempt_{attempt.id}_{attempt.ase.name.replace(' ', '_')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/cohort/{cohort_id}/csv")
def export_cohort_csv(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports a sanitized CSV containing assessment performance of all ASEs in a cohort.
    Enforces strict access permissions:
      - Admin can export any cohort.
      - Mentors can export ONLY their own assigned mentees in that cohort.
      - ASEs cannot export cohort CSV (returns 403 Forbidden).
    Mitigates CSV Formula Injection by prepending ' to formula trigger characters (=, +, -, @).
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins and Mentors can export cohort results")

    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    # Determine eligible ASEs
    if current_user.role == UserRole.MENTOR:
        mentee_ids = set(r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all())
        members = [m for m in cohort.members if m.ase_id in mentee_ids]
    else:
        members = cohort.members

    # Prepare CSV stream
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Cohort Name",
        "Candidate Name",
        "Candidate Email",
        "Mentor Name",
        "Assessment Title",
        "Latest Score (%)",
        "Total Score",
        "Max Score",
        "Pass/Fail",
        "Status",
        "Violations Count",
        "Flagged",
        "Strong Areas",
        "Weak Areas",
        "Submitted At"
    ])

    for m in members:
        ase = m.ase
        mentor_rel = ase.mentor_assignment
        mentor_name = mentor_rel.mentor.name if (mentor_rel and mentor_rel.mentor) else "Unassigned"

        # Fetch latest attempt
        latest = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ase.id
        ).order_by(AssessmentAttempt.started_at.desc()).first()

        if latest:
            asmt_title = latest.assignment.assessment.title if (latest.assignment and latest.assignment.assessment) else "N/A"
            score_pct = f"{latest.percentage:.1f}" if latest.status.value != "IN_PROGRESS" else "In Progress"
            tot_sc = f"{latest.total_score:.1f}" if latest.status.value != "IN_PROGRESS" else "In Progress"
            max_sc = f"{latest.max_score:.1f}"
            pass_str = "PASSED" if latest.passed else "FAILED"
            status_str = latest.status.value
            v_count = str(latest.violation_count)
            flagged_str = "YES" if latest.violation_count > 0 else "NO"
            strong_str = ", ".join(latest.strong_areas or [])
            weak_str = ", ".join(latest.weak_areas or [])
            sub_date = latest.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if latest.submitted_at else "N/A"
        else:
            asmt_title = "None"
            score_pct = "Not Attempted"
            tot_sc = "0"
            max_sc = "0"
            pass_str = "N/A"
            status_str = "NOT_ATTEMPTED"
            v_count = "0"
            flagged_str = "NO"
            strong_str = ""
            weak_str = ""
            sub_date = "N/A"

        row = [
            sanitize_csv_cell(cohort.name),
            sanitize_csv_cell(ase.name),
            sanitize_csv_cell(ase.email),
            sanitize_csv_cell(mentor_name),
            sanitize_csv_cell(asmt_title),
            sanitize_csv_cell(score_pct),
            sanitize_csv_cell(tot_sc),
            sanitize_csv_cell(max_sc),
            sanitize_csv_cell(pass_str),
            sanitize_csv_cell(status_str),
            sanitize_csv_cell(v_count),
            sanitize_csv_cell(flagged_str),
            sanitize_csv_cell(strong_str),
            sanitize_csv_cell(weak_str),
            sanitize_csv_cell(sub_date)
        ]
        writer.writerow(row)

    output.seek(0)
    filename = f"cohort_{cohort.id}_{cohort.name.replace(' ', '_')}_results.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
