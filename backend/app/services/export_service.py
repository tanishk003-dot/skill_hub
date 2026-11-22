import io
import csv
import hashlib
from typing import List, Dict, Any, Generator, Optional
from datetime import datetime, timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

def sanitize_cell_value(val: Any) -> Any:
    """Escapes strings starting with dangerous formula characters to prevent Excel/CSV injection."""
    if isinstance(val, str):
        if val.startswith(DANGEROUS_FORMULA_PREFIXES):
            return f"'{val}"
    return val

def generate_pseudonymous_id(user_id: int) -> str:
    """Generates a stable, pseudonymous ID from user ID."""
    digest = hashlib.sha256(f"ASE_SALT_{user_id}".encode()).hexdigest()[:8]
    return f"ASE-{digest.upper()}"

def get_allowed_mentee_ids(db: Session, mentor_id: int) -> List[int]:
    """Returns list of mentee IDs assigned to the given mentor."""
    assignments = db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == mentor_id).all()
    return [a[0] for a in assignments]


def get_export_data(
    db: Session,
    entity: str,
    requesting_user: User,
    include_pii: bool = False
) -> List[Dict[str, Any]]:
    """Fetches and formats tabular data for export with strict scoping and sanitization."""
    # Scope check
    is_mentor = (requesting_user.role == UserRole.MENTOR)
    is_admin = (requesting_user.role == UserRole.ADMIN)

    if not (is_admin or is_mentor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can export data.")

    mentee_ids = get_allowed_mentee_ids(db, requesting_user.id) if is_mentor else None

    # Only admins can opt in to global PII; mentors only get PII for their own mentees if requested
    can_include_pii = include_pii and (is_admin or is_mentor)

    data: List[Dict[str, Any]] = []

    if entity == "assessments":
        query = db.query(Assessment)
        for ass in query.all():
            data.append({
                "Assessment ID": ass.id,
                "Title": sanitize_cell_value(ass.title),
                "Type": ass.type.value if hasattr(ass.type, "value") else str(ass.type),
                "Duration (Minutes)": ass.total_duration_minutes,
                "Passing %": ass.passing_percentage,
                "Webcam Mode": getattr(ass, "webcam_mode", "REQUIRED"),
                "Created At (UTC)": ass.created_at.isoformat() if ass.created_at else None
            })

    elif entity == "results":
        query = db.query(AssessmentAttempt).join(User, AssessmentAttempt.ase_id == User.id)
        if is_mentor and mentee_ids is not None:
            query = query.filter(AssessmentAttempt.ase_id.in_(mentee_ids))

        for att in query.all():
            row = {
                "Attempt ID": att.id,
                "Candidate ID": generate_pseudonymous_id(att.ase_id),
                "Status": att.status.value if hasattr(att.status, "value") else str(att.status),
                "Score": att.total_score,
                "Max Score": att.max_score,
                "Percentage": att.percentage,
                "Passed": "YES" if att.passed else "NO",
                "Violation Count": att.violation_count,
                "Camera Status": getattr(att, "camera_status", "N/A"),
                "Started At (UTC)": att.started_at.isoformat() if att.started_at else None,
                "Submitted At (UTC)": att.submitted_at.isoformat() if att.submitted_at else None
            }
            if can_include_pii and att.ase:
                row["Candidate Name"] = sanitize_cell_value(att.ase.name)
                row["Candidate Email"] = sanitize_cell_value(att.ase.email)
            data.append(row)

    elif entity == "cohorts":
        query = db.query(CohortMember).join(Cohort, CohortMember.cohort_id == Cohort.id)
        if is_mentor and mentee_ids is not None:
            query = query.filter(CohortMember.ase_id.in_(mentee_ids))

        for cm in query.all():
            row = {
                "Cohort ID": cm.cohort_id,
                "Cohort Name": sanitize_cell_value(cm.cohort.name if cm.cohort else "N/A"),
                "Candidate ID": generate_pseudonymous_id(cm.ase_id),
                "Joined At (UTC)": cm.joined_at.isoformat() if cm.joined_at else None
            }
            if can_include_pii and cm.ase:
                row["Candidate Name"] = sanitize_cell_value(cm.ase.name)
                row["Candidate Email"] = sanitize_cell_value(cm.ase.email)
            data.append(row)

    elif entity == "trainings":
        query = db.query(TrainingAssignment).join(Training, TrainingAssignment.training_id == Training.id)
        if is_mentor and mentee_ids is not None:
            query = query.filter(TrainingAssignment.ase_id.in_(mentee_ids))

        for ta in query.all():
            row = {
                "Training ID": ta.training_id,
                "Training Title": sanitize_cell_value(ta.training.title if ta.training else "N/A"),
                "Candidate ID": generate_pseudonymous_id(ta.ase_id),
                "Status": ta.status.value if hasattr(ta.status, "value") else str(ta.status),
                "Progress %": ta.progress_percent,
                "Assigned At (UTC)": ta.assigned_at.isoformat() if ta.assigned_at else None,
                "Completed At (UTC)": ta.completed_at.isoformat() if ta.completed_at else None
            }
            if can_include_pii and ta.ase:
                row["Candidate Name"] = sanitize_cell_value(ta.ase.name)
                row["Candidate Email"] = sanitize_cell_value(ta.ase.email)
            data.append(row)

    elif entity == "attendance":
        query = db.query(LiveClassAttendee).join(LiveClass, LiveClassAttendee.live_class_id == LiveClass.id)
        if is_mentor and mentee_ids is not None:
            query = query.filter(LiveClassAttendee.ase_id.in_(mentee_ids))

        for lca in query.all():
            row = {
                "Live Class ID": lca.live_class_id,
                "Class Title": sanitize_cell_value(lca.live_class.title if lca.live_class else "N/A"),
                "Candidate ID": generate_pseudonymous_id(lca.ase_id),
                "Status": lca.status,
                "Marked At (UTC)": lca.marked_at.isoformat() if lca.marked_at else None
            }
            if can_include_pii and lca.ase:
                row["Candidate Name"] = sanitize_cell_value(lca.ase.name)
                row["Candidate Email"] = sanitize_cell_value(lca.ase.email)
            data.append(row)

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported entity: {entity}")

    return data


def generate_csv_string(data: List[Dict[str, Any]]) -> str:
    """Generates CSV text with formula injection protections."""
    if not data:
        return ""
    output = io.StringIO()
    headers = list(data[0].keys())
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in data:
        cleaned_row = {k: sanitize_cell_value(v) for k, v in row.items()}
        writer.writerow(cleaned_row)
    return output.getvalue()


def generate_excel_bytes(data: List[Dict[str, Any]], sheet_title: str = "SkillHub Export") -> bytes:
    """Generates styled Excel .xlsx binary buffer with formula escaping."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:30]

    if not data:
        ws.append(["No Data Available"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    headers = list(data[0].keys())
    ws.append(headers)

    # Style header row
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Add data rows
    for row_idx, row in enumerate(data, start=2):
        row_values = [sanitize_cell_value(row.get(h, "")) for h in headers]
        ws.append(row_values)

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
