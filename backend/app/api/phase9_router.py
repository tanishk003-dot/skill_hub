from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.phase9_models import (
    ReadinessConfig, AseGamification, OnboardingMilestone,
    AILearningRoadmap, IssuedCertificate, MockInterviewSession
)
from app.schemas.phase9_schemas import (
    ReadinessWeightsUpdate, ReadinessResponse, LeaderboardOptInUpdate,
    LeaderboardItem, RoadmapResponse, RoadmapItemToggle,
    RiskSignalResponse, NudgeResponse, ReassessmentScheduleCreate,
    ReassessmentScheduleResponse, ReassessmentGrowthResponse,
    CertificateIssueRequest, CertificatePublicVerifyResponse,
    MockInterviewStartRequest, MockInterviewResponseRequest,
    MilestoneToggleRequest
)
from app.services.readiness_service import (
    calculate_ase_readiness, update_readiness_weights, get_or_create_readiness_config
)
from app.services.gamification_journey_service import (
    get_or_create_gamification, get_or_create_milestones,
    toggle_milestone_completion, get_leaderboard
)
from app.services.roadmap_service import (
    get_or_generate_roadmap, update_roadmap_item_status
)
from app.services.early_warning_service import (
    evaluate_ase_risk, get_mentor_risk_matrix, send_supportive_nudge
)
from app.services.certificate_service import (
    issue_certificate, verify_certificate_public
)
from app.services.mock_interview_service import (
    start_mock_interview, submit_interview_response
)
from app.services.reassessment_service import (
    schedule_reassessment, get_reassessment_growth_analytics
)
from app.services.ceo_center_service import (
    get_ceo_command_center_analytics, generate_ceo_executive_pdf
)

router = APIRouter(prefix="", tags=["Phase 9: WOW Pack"])

def verify_mentor_mentee_access(db: Session, mentor_id: int, ase_id: int):
    assignment = db.query(MentorAseAssignment).filter(
        MentorAseAssignment.mentor_id == mentor_id,
        MentorAseAssignment.ase_id == ase_id
    ).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not assigned to this mentee."
        )

# ============================================================================
# 1. Project-Readiness & Skill DNA Endpoints
# ============================================================================

@router.get("/readiness/me", response_model=ReadinessResponse)
def get_my_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = calculate_ase_readiness(db, current_user.id)
    return ReadinessResponse(**result)

@router.get("/readiness/ase/{ase_id}", response_model=ReadinessResponse)
def get_ase_readiness(
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ASE and current_user.id != ase_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot view other ASE readiness.")
    elif current_user.role == UserRole.MENTOR:
        verify_mentor_mentee_access(db, current_user.id, ase_id)

    target_ase = db.query(User).filter(User.id == ase_id).first()
    if not target_ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ASE not found.")

    result = calculate_ase_readiness(db, ase_id)
    return ReadinessResponse(**result)

@router.get("/readiness/config")
def get_readiness_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cfg = get_or_create_readiness_config(db)
    return {
        "assessment_weight": cfg.assessment_weight,
        "coding_weight": cfg.coding_weight,
        "training_weight": cfg.training_weight,
        "attendance_weight": cfg.attendance_weight,
        "consistency_weight": cfg.consistency_weight
    }

@router.put("/readiness/config")
def update_weights(
    payload: ReadinessWeightsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can configure readiness weights.")

    updated_cfg = update_readiness_weights(db, current_user.id, payload.dict())
    return {
        "message": "Readiness weights updated and logged to audit successfully.",
        "weights": {
            "assessment_weight": updated_cfg.assessment_weight,
            "coding_weight": updated_cfg.coding_weight,
            "training_weight": updated_cfg.training_weight,
            "attendance_weight": updated_cfg.attendance_weight,
            "consistency_weight": updated_cfg.consistency_weight
        }
    }

# ============================================================================
# 2. Journey Map & Gamification Endpoints
# ============================================================================

@router.get("/journey/my-path")
def get_my_journey(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    gam = get_or_create_gamification(db, current_user.id)
    milestones = get_or_create_milestones(db, current_user.id)

    return {
        "xp": gam.xp,
        "level": gam.level,
        "streak_days": gam.streak_days,
        "badges": gam.badges_json or [],
        "leaderboard_opt_in": gam.leaderboard_opt_in,
        "show_full_name_publicly": gam.show_full_name_publicly,
        "milestones": [
            {
                "id": m.id,
                "day_phase": m.day_phase,
                "milestone_type": m.milestone_type,
                "title": m.title,
                "is_completed": m.is_completed,
                "completed_at": m.completed_at
            }
            for m in milestones
        ]
    }

@router.put("/journey/leaderboard-opt-in")
def update_leaderboard_preferences(
    payload: LeaderboardOptInUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    gam = get_or_create_gamification(db, current_user.id)
    gam.leaderboard_opt_in = payload.opt_in
    if payload.show_full_name is not None:
        gam.show_full_name_publicly = payload.show_full_name
    db.commit()
    return {
        "message": "Leaderboard privacy preference updated.",
        "leaderboard_opt_in": gam.leaderboard_opt_in,
        "show_full_name_publicly": gam.show_full_name_publicly
    }

@router.get("/journey/leaderboard", response_model=List[LeaderboardItem])
def view_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Returns strictly opted-in members with minimal non-sensitive attributes
    return get_leaderboard(db, current_user.id)

@router.put("/journey/milestone/{milestone_id}/toggle")
def toggle_milestone(
    milestone_id: int,
    payload: MilestoneToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = toggle_milestone_completion(db, milestone_id, current_user.id, payload.is_completed)
    return {
        "id": updated.id,
        "is_completed": updated.is_completed,
        "completed_at": updated.completed_at
    }

# ============================================================================
# 3. AI Learning Roadmap Endpoints
# ============================================================================

@router.get("/roadmap/current", response_model=RoadmapResponse)
def get_current_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    roadmap = get_or_generate_roadmap(db, current_user.id)
    return RoadmapResponse(
        id=roadmap.id,
        ase_id=roadmap.ase_id,
        week_number=roadmap.week_number,
        generated_from_weak_skills=roadmap.generated_from_weak_skills or [],
        roadmap_items=roadmap.roadmap_items_json or [],
        version=roadmap.version,
        created_at=roadmap.created_at
    )

@router.post("/roadmap/regenerate", response_model=RoadmapResponse)
def regenerate_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    roadmap = get_or_generate_roadmap(db, current_user.id, force_regenerate=True)
    return RoadmapResponse(
        id=roadmap.id,
        ase_id=roadmap.ase_id,
        week_number=roadmap.week_number,
        generated_from_weak_skills=roadmap.generated_from_weak_skills or [],
        roadmap_items=roadmap.roadmap_items_json or [],
        version=roadmap.version,
        created_at=roadmap.created_at
    )

@router.put("/roadmap/{roadmap_id}/item/{item_id}", response_model=RoadmapResponse)
def toggle_roadmap_item(
    roadmap_id: int,
    item_id: str,
    payload: RoadmapItemToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    roadmap = update_roadmap_item_status(db, current_user.id, roadmap_id, item_id, payload.completed)
    return RoadmapResponse(
        id=roadmap.id,
        ase_id=roadmap.ase_id,
        week_number=roadmap.week_number,
        generated_from_weak_skills=roadmap.generated_from_weak_skills or [],
        roadmap_items=roadmap.roadmap_items_json or [],
        version=roadmap.version,
        created_at=roadmap.created_at
    )

# ============================================================================
# 4. Early Warning System Endpoints
# ============================================================================

@router.get("/early-warning/mentee-risks", response_model=List[RiskSignalResponse])
def get_mentee_risks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Requirement 3: ASEs must NEVER receive risk data in any API response!
    if current_user.role == UserRole.ASE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Learner risk signals are private to mentors and leadership."
        )

    if current_user.role == UserRole.MENTOR:
        matrix = get_mentor_risk_matrix(db, current_user.id)
    else:
        # Admin gets all
        ases = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True).all()
        matrix = []
        for ase in ases:
            sig = evaluate_ase_risk(db, ase.id)
            matrix.append({
                "ase_id": ase.id,
                "name": ase.name,
                "email": ase.email,
                "risk_score": sig.risk_score,
                "risk_level": sig.risk_level,
                "factors": sig.factors_json,
                "ai_explanation": sig.ai_explanation,
                "last_nudged_at": sig.last_nudged_at
            })
        matrix.sort(key=lambda x: x["risk_score"], reverse=True)

    return matrix

@router.post("/early-warning/nudge/{ase_id}", response_model=NudgeResponse)
def nudge_candidate(
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == UserRole.MENTOR:
        verify_mentor_mentee_access(db, current_user.id, ase_id)

    result = send_supportive_nudge(db, current_user.id, ase_id)
    return NudgeResponse(**result)

# ============================================================================
# 5. Re-Assessment Growth & Delta Endpoints
# ============================================================================

@router.post("/reassessments/schedule", response_model=ReassessmentScheduleResponse)
def schedule_reassessment_endpoint(
    payload: ReassessmentScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can schedule re-assessments.")

    if current_user.role == UserRole.MENTOR and payload.ase_id:
        verify_mentor_mentee_access(db, current_user.id, payload.ase_id)

    sched = schedule_reassessment(
        db=db,
        admin_or_mentor_id=current_user.id,
        original_assessment_id=payload.original_assessment_id,
        phase_label=payload.phase_label,
        cohort_id=payload.cohort_id,
        ase_id=payload.ase_id,
        scheduled_days_from_now=payload.scheduled_days_from_now
    )
    return sched

@router.get("/reassessments/growth/{ase_id}", response_model=ReassessmentGrowthResponse)
def get_growth_chart(
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ASE and current_user.id != ase_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == UserRole.MENTOR:
        verify_mentor_mentee_access(db, current_user.id, ase_id)

    analytics = get_reassessment_growth_analytics(db, ase_id)
    return ReassessmentGrowthResponse(**analytics)

# ============================================================================
# 6. Verified Certificates Endpoints
# ============================================================================

@router.post("/certificates/issue")
def issue_cert_endpoint(
    payload: CertificateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can issue certificates.")

    cert = issue_certificate(
        db=db,
        ase_id=payload.ase_id,
        title=payload.title,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id
    )
    return {
        "message": "Certificate issued successfully.",
        "cert_uuid": cert.cert_uuid,
        "title": cert.title,
        "issue_date": cert.issue_date
    }

@router.get("/certificates/my")
def get_my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    certs = db.query(IssuedCertificate).filter(
        IssuedCertificate.ase_id == current_user.id
    ).order_by(IssuedCertificate.issue_date.desc()).all()

    return [
        {
            "cert_uuid": c.cert_uuid,
            "title": c.title,
            "entity_type": c.entity_type,
            "issue_date": c.issue_date.strftime("%B %d, %Y"),
            "is_revoked": c.is_revoked
        }
        for c in certs
    ]

@router.get("/certificates/download/{cert_uuid}")
def download_certificate_pdf(
    cert_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cert = db.query(IssuedCertificate).filter(IssuedCertificate.cert_uuid == cert_uuid).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found.")

    if current_user.role == UserRole.ASE and cert.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot download another user's certificate.")

    if not os.path.exists(cert.pdf_file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate file on server not found.")

    return FileResponse(
        cert.pdf_file_path,
        media_type="application/pdf",
        filename=f"Certificate_{cert_uuid[:8]}.pdf"
    )

@router.get("/certificates/verify/{cert_uuid}", response_model=CertificatePublicVerifyResponse)
def public_verify_certificate(
    cert_uuid: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public verification endpoint (NO authentication required).
    Rate limited by client IP.
    Exposes strictly minimal public data: status, recipient_name, course_title, issue_date, certificate_id.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    res = verify_certificate_public(db, cert_uuid, client_ip)
    return CertificatePublicVerifyResponse(**res)

# ============================================================================
# 7. AI Mock Interviewer Endpoints
# ============================================================================

@router.post("/mock-interview/start")
def start_interview(
    payload: MockInterviewStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Requirement 5: ASE-only
    if current_user.role != UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mock interview drills are available exclusively to ASE trainees.")

    res = start_mock_interview(
        db=db,
        ase_id=current_user.id,
        target_role=payload.target_role or "Associate Software Engineer",
        skill_focus=payload.skill_focus or "Backend Distributed Systems"
    )
    return res

@router.post("/mock-interview/respond")
def submit_interview_answer(
    payload: MockInterviewResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    res = submit_interview_response(
        db=db,
        ase_id=current_user.id,
        session_id=payload.session_id,
        candidate_answer=payload.candidate_answer
    )
    return res

# ============================================================================
# 8. CEO Command Center Endpoints (Admin Only)
# ============================================================================

@router.get("/ceo-center/overview")
def get_ceo_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only system administrators and executive leadership can access the CEO Command Center.")

    return get_ceo_command_center_analytics(db)

@router.get("/ceo-center/executive-pdf")
def export_ceo_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    pdf_path = generate_ceo_executive_pdf(db)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="CEO_Executive_Readiness_Report.pdf"
    )
