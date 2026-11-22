import json
from datetime import datetime, timezone
from app.core.datetime_util import ensure_utc, utc_now
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.chat import AIInsightsCache
from app.schemas.analytics import ASEDashboardResponse, MentorDashboardResponse, AdminDashboardResponse, AIInsightsResponse
from app.api.deps import get_current_user, require_mentor_or_admin, require_admin
from app.services.insights_service import insights_service
from app.services.llm_service import is_demo_mode

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/ase/dashboard", response_model=ASEDashboardResponse)
def get_ase_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ASE Performance Dashboard:
    Radar profile, section breakdown, progress over time (line chart),
    and prioritized 'What to improve' actionable insights.
    """
    if current_user.role != UserRole.ASE and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only ASEs can access candidate dashboard")

    # Fetch all completed or submitted attempts for this user
    attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == current_user.id,
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
    ).order_by(AssessmentAttempt.started_at.asc()).all()

    if not attempts:
        # Safe zero-state: handle ASE with no attempts gracefully without crashing
        return ASEDashboardResponse(
            summary={
                "total_attempts": 0,
                "passed_attempts": 0,
                "average_score": 0.0,
                "latest_score": 0.0,
                "has_attempts": False
            },
            radar_skills={"labels": [], "values": []},
            section_scores={"labels": [], "scores": [], "max_scores": []},
            progress_history=[],
            strong_areas=[],
            weak_areas=[],
            what_to_improve=[],
            latest_attempt_id=None
        )

    # Latest attempt
    latest = attempts[-1]

    # Summary metrics
    total_attempts = len(attempts)
    passed_attempts = sum(1 for a in attempts if a.passed)
    avg_score = round(sum(a.percentage for a in attempts) / max(1, total_attempts), 1)

    # Progress History (Line chart)
    progress_history = []
    for a in attempts:
        date_str = a.submitted_at.strftime("%b %d, %H:%M") if a.submitted_at else a.started_at.strftime("%b %d")
        progress_history.append({
            "attempt_id": a.id,
            "assessment_title": a.assignment.assessment.title if (a.assignment and a.assignment.assessment) else "Assessment",
            "date": date_str,
            "percentage": round(a.percentage, 1),
            "total_score": round(a.total_score, 1),
            "max_score": round(a.max_score, 1),
            "passed": a.passed
        })

    # Radar Chart
    skill_pcts = latest.skill_percentages or {}
    radar_labels = list(skill_pcts.keys())
    radar_values = [round(float(v), 1) for v in skill_pcts.values()]

    # Section Bar Chart
    sec_scores = latest.section_scores or []
    bar_labels = [s.get("title", f"Sec {idx+1}") for idx, s in enumerate(sec_scores)]
    bar_scores = [round(float(s.get("score", 0)), 1) for s in sec_scores]
    bar_maxes = [round(float(s.get("max", 0)), 1) for s in sec_scores]

    # Rule-based insights
    insights = insights_service.generate_candidate_improvements(skill_pcts)

    return ASEDashboardResponse(
        summary={
            "total_attempts": total_attempts,
            "passed_attempts": passed_attempts,
            "average_score": avg_score,
            "latest_score": round(latest.percentage, 1),
            "latest_passed": latest.passed,
            "has_attempts": True
        },
        radar_skills={"labels": radar_labels, "values": radar_values},
        section_scores={"labels": bar_labels, "scores": bar_scores, "max_scores": bar_maxes},
        progress_history=progress_history,
        strong_areas=insights["strong_areas"],
        weak_areas=insights["weak_areas"],
        what_to_improve=insights["improvements"],
        latest_attempt_id=latest.id
    )


@router.get("/mentor/dashboard", response_model=MentorDashboardResponse)
def get_mentor_dashboard(
    cohort_id: Optional[int] = Query(None, description="Optional cohort filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    """
    Mentor Performance & Cohort Analytics Dashboard:
    - Mentors see strictly only their assigned mentees (even in a shared cohort).
    - Cohort average radar, weak-area heatmap, ASE ranking, and 'Needs Attention' alerts.
    - Handles ASEs with no attempts safely (no division by zero).
    """
    # 1. Determine cohort options
    if current_user.role == UserRole.ADMIN:
        cohorts = db.query(Cohort).order_by(Cohort.name.asc()).all()
        cohort_options = [{"id": c.id, "name": c.name} for c in cohorts]
    else:
        mentee_ids_all = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        cohorts = db.query(Cohort).outerjoin(CohortMember, CohortMember.cohort_id == Cohort.id).filter(
            or_(
                Cohort.created_by == current_user.id,
                CohortMember.ase_id.in_(mentee_ids_all)
            )
        ).distinct().order_by(Cohort.name.asc()).all()
        cohort_options = [{"id": c.id, "name": c.name} for c in cohorts]

    # 2. Determine target ASEs
    if current_user.role == UserRole.MENTOR:
        target_ase_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        if cohort_id:
            cohort_ase_ids = set(r[0] for r in db.query(CohortMember.ase_id).filter(CohortMember.cohort_id == cohort_id).all())
            target_ase_ids = [aid for aid in target_ase_ids if aid in cohort_ase_ids]
    else:
        # Admin
        if cohort_id:
            target_ase_ids = [r[0] for r in db.query(CohortMember.ase_id).filter(CohortMember.cohort_id == cohort_id).all()]
        else:
            target_ase_ids = [r[0] for r in db.query(User.id).filter(User.role == UserRole.ASE, User.is_active == True).all()]

    target_ases = db.query(User).filter(User.id.in_(target_ase_ids), User.is_active == True).order_by(User.name.asc()).all()

    # 3. Process ASE attempts, heatmap, ranking, and needs attention
    all_known_skills = set()
    ase_stats = []
    needs_attention = []

    for ase in target_ases:
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ase.id,
            AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
        ).order_by(AssessmentAttempt.started_at.desc()).all()

        assignments_count = db.query(AssessmentAssignment).filter(AssessmentAssignment.ase_id == ase.id).count()

        latest_attempt = attempts[0] if attempts else None
        latest_attempt_dict = None

        if latest_attempt:
            latest_attempt_dict = {
                "id": latest_attempt.id,
                "percentage": latest_attempt.percentage,
                "passed": latest_attempt.passed,
                "status": latest_attempt.status.value,
                "violation_count": latest_attempt.violation_count,
                "skill_percentages": latest_attempt.skill_percentages or {}
            }
            for sk in (latest_attempt.skill_percentages or {}).keys():
                all_known_skills.add(sk)

        ase_info = {"id": ase.id, "name": ase.name, "email": ase.email}

        # Check needs attention
        alert = insights_service.evaluate_needs_attention(
            ase_info=ase_info,
            latest_attempt=latest_attempt_dict,
            has_assignment=(assignments_count > 0)
        )
        if alert:
            needs_attention.append(alert)

        # Average score (handles 0 attempts without divide-by-zero)
        if attempts:
            avg_score = round(sum(a.percentage for a in attempts) / len(attempts), 1)
            passed_cnt = sum(1 for a in attempts if a.passed)
            focus_area = insights_service.compute_suggested_focus_area(latest_attempt.skill_percentages or {})
            is_flagged = any((a.violation_count > 0 or a.status == AttemptStatus.AUTO_SUBMITTED_VIOLATION) for a in attempts)
            has_att = True
        else:
            avg_score = None
            passed_cnt = 0
            focus_area = "No Attempts Yet"
            is_flagged = False
            has_att = False

        ase_stats.append({
            "ase_id": ase.id,
            "ase_name": ase.name,
            "ase_email": ase.email,
            "average_score": avg_score,
            "attempts_count": len(attempts),
            "passed_count": passed_cnt,
            "flagged": is_flagged,
            "suggested_focus": focus_area,
            "latest_attempt_id": latest_attempt.id if latest_attempt else None,
            "has_attempt": has_att,
            "skill_percentages": latest_attempt.skill_percentages if latest_attempt else {}
        })

    # Default fallback skills if no assessments completed yet
    if not all_known_skills:
        all_known_skills = {"Deductive Logic", "Pattern Recognition", "Critical Reasoning", "Quantitative Aptitude"}

    skills_sorted = sorted(list(all_known_skills))

    # Heatmap Matrix
    heatmap_rows = []
    cohort_skill_totals = {sk: [] for sk in skills_sorted}

    for stat in ase_stats:
        scores_map = {}
        for sk in skills_sorted:
            val = stat["skill_percentages"].get(sk)
            if val is not None:
                val = round(float(val), 1)
                cohort_skill_totals[sk].append(val)
            scores_map[sk] = val

        heatmap_rows.append({
            "ase_id": stat["ase_id"],
            "ase_name": stat["ase_name"],
            "scores": scores_map,
            "has_attempt": stat["has_attempt"]
        })

    # Cohort Average Radar
    cohort_radar_labels = []
    cohort_radar_values = []
    for sk in skills_sorted:
        vals = cohort_skill_totals[sk]
        cohort_radar_labels.append(sk)
        cohort_radar_values.append(round(sum(vals) / len(vals), 1) if vals else 0.0)

    # Ranking Table (Sort by average_score DESC; None at bottom)
    ase_stats.sort(key=lambda x: (1 if x["average_score"] is not None else 0, x["average_score"] or 0), reverse=True)
    ranking_table = []
    for rank, stat in enumerate(ase_stats, start=1):
        ranking_table.append({
            "rank": rank if stat["has_attempt"] else "-",
            "ase_id": stat["ase_id"],
            "ase_name": stat["ase_name"],
            "ase_email": stat["ase_email"],
            "average_score": stat["average_score"] if stat["average_score"] is not None else 0.0,
            "attempts_count": stat["attempts_count"],
            "passed_count": stat["passed_count"],
            "flagged": stat["flagged"],
            "suggested_focus": stat["suggested_focus"],
            "latest_attempt_id": stat["latest_attempt_id"],
            "has_attempt": stat["has_attempt"]
        })

    # Phase 5: Training metrics for mentor's mentees
    now = datetime.now(timezone.utc)
    relevant_ase_ids = [s["ase_id"] for s in ase_stats]
    ta_query = db.query(TrainingAssignment).filter(TrainingAssignment.ase_id.in_(relevant_ase_ids)) if relevant_ase_ids else db.query(TrainingAssignment).filter(False)
    if cohort_id:
        ta_query = ta_query.filter(TrainingAssignment.cohort_id == cohort_id)
    all_ta = ta_query.all()

    total_ta = len(all_ta)
    completed_ta = sum(1 for t in all_ta if t.status == "COMPLETED")
    in_prog_ta = sum(1 for t in all_ta if t.status == "IN_PROGRESS")
    not_start_ta = sum(1 for t in all_ta if t.status == "NOT_STARTED")
    completion_rate_ta = round((completed_ta / max(1, total_ta)) * 100, 1) if total_ta else 0.0

    overdue_ta = [
        {
            "assignment_id": t.id,
            "training_title": t.training.title if t.training else "Training",
            "ase_id": t.ase_id,
            "ase_name": t.ase.name if t.ase else "ASE",
            "due_date": t.due_date.strftime("%Y-%m-%d %H:%M UTC"),
            "progress_percent": t.progress_percent
        }
        for t in all_ta if t.due_date and ensure_utc(t.due_date) < now and t.status != "COMPLETED"
    ]

    training_metrics = {
        "total_assigned": total_ta,
        "completed": completed_ta,
        "in_progress": in_prog_ta,
        "not_started": not_start_ta,
        "completion_rate": completion_rate_ta,
        "overdue_count": len(overdue_ta)
    }

    # Phase 5: Live class attendance metrics for mentor
    classes = db.query(LiveClass).filter(LiveClass.created_by == current_user.id).all()
    class_ids = [c.id for c in classes]
    attendees = db.query(LiveClassAttendee).filter(LiveClassAttendee.live_class_id.in_(class_ids)).all() if class_ids else []

    total_invited = len(attendees)
    total_attended = sum(1 for a in attendees if a.status == "ATTENDED")
    total_absent = sum(1 for a in attendees if a.status == "ABSENT")
    attendance_rate = round((total_attended / max(1, total_invited)) * 100, 1) if total_invited else 0.0

    attendance_metrics = {
        "total_classes": len(classes),
        "total_invited": total_invited,
        "total_attended": total_attended,
        "total_absent": total_absent,
        "attendance_rate": attendance_rate
    }

    return MentorDashboardResponse(
        cohort_options=cohort_options,
        selected_cohort_id=cohort_id,
        cohort_radar={"labels": cohort_radar_labels, "values": cohort_radar_values},
        heatmap={"skills": skills_sorted, "rows": heatmap_rows},
        ranking_table=ranking_table,
        needs_attention=needs_attention,
        training_metrics=training_metrics,
        attendance_metrics=attendance_metrics,
        overdue_trainings=overdue_ta
    )


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Org-Wide Executive Analytics Dashboard:
    - Multi-cohort comparison
    - Assessment completion funnels
    - Org-wide skill gap benchmarks
    - Pending and inactive user summaries
    """
    # 1. Cohort comparison
    all_cohorts = db.query(Cohort).all()
    cohort_comparison = []

    for c in all_cohorts:
        member_ids = [m.ase_id for m in c.members]
        if member_ids:
            attempts = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.ase_id.in_(member_ids),
                AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
            ).all()

            avg_score = round(sum(a.percentage for a in attempts) / max(1, len(attempts)), 1) if attempts else 0.0
            passing_rate = round((sum(1 for a in attempts if a.passed) / max(1, len(attempts))) * 100, 1) if attempts else 0.0
        else:
            avg_score = 0.0
            passing_rate = 0.0

        cohort_comparison.append({
            "cohort_id": c.id,
            "cohort_name": c.name,
            "member_count": len(member_ids),
            "average_score": avg_score,
            "passing_rate": passing_rate
        })

    # 2. Completion rate
    total_assignments = db.query(AssessmentAssignment).count()
    completed_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
    ).count()
    in_progress = db.query(AssessmentAttempt).filter(AssessmentAttempt.status == AttemptStatus.IN_PROGRESS).count()
    unattempted = max(0, total_assignments - completed_attempts - in_progress)
    completion_pct = round((completed_attempts / max(1, total_assignments)) * 100, 1) if total_assignments else 0.0

    completion_rate = {
        "total_assigned": total_assignments,
        "completed": completed_attempts,
        "in_progress": in_progress,
        "expired_or_unattempted": unattempted,
        "percentage": completion_pct
    }

    # 3. Org-wide skill gaps
    all_completed = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
    ).all()

    skill_totals = {}
    for a in all_completed:
        if a.skill_percentages:
            for sk, val in a.skill_percentages.items():
                skill_totals.setdefault(sk, []).append(float(val))

    benchmark = 70.0
    org_skill_gaps = []
    for sk, vals in skill_totals.items():
        avg_val = round(sum(vals) / max(1, len(vals)), 1)
        gap = round(benchmark - avg_val, 1)
        org_skill_gaps.append({
            "skill": sk,
            "average_score": avg_val,
            "benchmark": benchmark,
            "gap": max(0.0, gap),
            "is_gap": avg_val < benchmark
        })

    org_skill_gaps.sort(key=lambda x: x["average_score"])

    # 4. User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users

    users_summary = {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "pending_attempts": unattempted
    }

    # Phase 5: Org-wide Training metrics
    now = datetime.now(timezone.utc)
    all_ta = db.query(TrainingAssignment).all()
    total_ta = len(all_ta)
    completed_ta = sum(1 for t in all_ta if t.status == "COMPLETED")
    in_prog_ta = sum(1 for t in all_ta if t.status == "IN_PROGRESS")
    not_start_ta = sum(1 for t in all_ta if t.status == "NOT_STARTED")
    completion_rate_ta = round((completed_ta / max(1, total_ta)) * 100, 1) if total_ta else 0.0

    overdue_ta = [
        {
            "assignment_id": t.id,
            "training_title": t.training.title if t.training else "Training",
            "ase_id": t.ase_id,
            "ase_name": t.ase.name if t.ase else "ASE",
            "due_date": t.due_date.strftime("%Y-%m-%d %H:%M UTC"),
            "progress_percent": t.progress_percent
        }
        for t in all_ta if t.due_date and ensure_utc(t.due_date) < now and t.status != "COMPLETED"
    ]

    training_metrics = {
        "total_assigned": total_ta,
        "completed": completed_ta,
        "in_progress": in_prog_ta,
        "not_started": not_start_ta,
        "completion_rate": completion_rate_ta,
        "overdue_count": len(overdue_ta)
    }

    # Phase 5: Org-wide Live Class attendance metrics
    all_classes = db.query(LiveClass).all()
    all_attendees = db.query(LiveClassAttendee).all()
    total_invited = len(all_attendees)
    total_attended = sum(1 for a in all_attendees if a.status == "ATTENDED")
    total_absent = sum(1 for a in all_attendees if a.status == "ABSENT")
    attendance_rate = round((total_attended / max(1, total_invited)) * 100, 1) if total_invited else 0.0

    attendance_metrics = {
        "total_classes": len(all_classes),
        "total_invited": total_invited,
        "total_attended": total_attended,
        "total_absent": total_absent,
        "attendance_rate": attendance_rate
    }

    return AdminDashboardResponse(
        cohort_comparison=cohort_comparison,
        completion_rate=completion_rate,
        org_skill_gaps=org_skill_gaps,
        users_summary=users_summary,
        training_metrics=training_metrics,
        attendance_metrics=attendance_metrics,
        overdue_trainings=overdue_ta
    )


@router.get("/ase/{ase_id}/ai-insights", response_model=AIInsightsResponse)
def get_ase_ai_insights(
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns AI-generated improvement recommendations, study plan, and suggested trainings.
    PRIVACY & PERMISSIONS:
    - ASE can only access their own AI insights.
    - Mentor can access only their assigned mentees' AI insights.
    - Admin has global access.
    Returns 403 Forbidden on any unauthorized access attempt.
    """
    if current_user.role == UserRole.ASE:
        if current_user.id != ase_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: ASEs can only access their own AI insights."
            )
    elif current_user.role == UserRole.MENTOR:
        is_mentee = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == ase_id
        ).first()
        if not is_mentee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Mentors can only view AI insights for their assigned mentees."
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

    ase = db.query(User).filter(User.id == ase_id, User.role == UserRole.ASE).first()
    if not ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ASE user not found.")

    latest = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == ase_id,
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
    ).order_by(AssessmentAttempt.submitted_at.desc()).first()

    # Check cache
    cache = db.query(AIInsightsCache).filter(AIInsightsCache.ase_id == ase_id).first()
    if cache and not cache.is_stale and (latest is None or cache.latest_attempt_id == latest.id):
        try:
            cached_data = json.loads(cache.insights_json)
            cached_data["cached"] = True
            return AIInsightsResponse(**cached_data)
        except Exception:
            pass

    # Generate insights
    skill_pcts = latest.skill_percentages if latest else {}
    improvements_data = insights_service.generate_candidate_improvements(skill_pcts)

    weak_skills = improvements_data.get("weak_areas", [])
    suggested_trainings = []
    if weak_skills:
        matching = db.query(Training).filter(
            Training.skill_category.in_(weak_skills)
        ).limit(3).all()
        for tr in matching:
            suggested_trainings.append({
                "id": tr.id,
                "title": tr.title,
                "skill_category": tr.skill_category,
                "type": tr.type,
                "duration_hours": tr.duration_hours
            })

    study_plan = improvements_data.get("ai_study_plan") or (
        "Personalized AI Study Plan:\n"
        "1. Dedicate 45 minutes daily to targeted problem sets in your lowest-scoring domain.\n"
        "2. Complete assigned interactive modules on the My Learning dashboard.\n"
        "3. Review section time allocations before attempting next evaluation."
    )

    result_payload = {
        "ase_id": ase.id,
        "ase_name": ase.name,
        "is_ai": improvements_data.get("is_ai", True),
        "provider": improvements_data.get("provider", "mock"),
        "demo_mode": is_demo_mode(),
        "study_plan": study_plan,
        "priority_skills": weak_skills,
        "suggested_trainings": suggested_trainings,
        "cached": False
    }

    if not cache:
        cache = AIInsightsCache(
            ase_id=ase.id,
            latest_attempt_id=latest.id if latest else None,
            insights_json=json.dumps(result_payload),
            provider=result_payload["provider"],
            is_stale=False
        )
        db.add(cache)
    else:
        cache.latest_attempt_id = latest.id if latest else None
        cache.insights_json = json.dumps(result_payload)
        cache.provider = result_payload["provider"]
        cache.is_stale = False
        cache.updated_at = datetime.now(timezone.utc)
    db.commit()

    return AIInsightsResponse(**result_payload)


@router.get("/ase/{ase_id}/onboarding-progress")
def get_ase_onboarding_progress(
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the overall onboarding progress for an ASE:
    Assessments (40%), Trainings (40%), Live Classes (20%).
    Permissions: ASE can view self; Mentor can view assigned mentee; Admin can view all.
    """
    if current_user.role == UserRole.ASE and current_user.id != ase_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.MENTOR:
        is_mentee = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == ase_id
        ).first()
        if not is_mentee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: ASE is not your mentee")
    elif current_user.role != UserRole.ADMIN and current_user.role != UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    ase = db.query(User).filter(User.id == ase_id).first()
    if not ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ASE not found")

    # 1. Assessments (40%)
    assigned_assessments = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.ase_id == ase_id
    ).all()
    total_assessments = len(assigned_assessments)
    completed_assessments = 0
    if total_assessments > 0:
        assignment_ids = [a.id for a in assigned_assessments]
        completed_assessments = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.assignment_id.in_(assignment_ids),
            AssessmentAttempt.ase_id == ase_id,
            AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
        ).distinct(AssessmentAttempt.assignment_id).count()
        assessments_pct = round((completed_assessments / total_assessments) * 100.0, 1)
    else:
        assessments_pct = 100.0 if db.query(AssessmentAttempt).filter(AssessmentAttempt.ase_id == ase_id).count() > 0 else 0.0

    # 2. Trainings (40%)
    assigned_trainings = db.query(TrainingAssignment).filter(
        TrainingAssignment.ase_id == ase_id
    ).all()
    total_trainings = len(assigned_trainings)
    completed_trainings = 0
    if total_trainings > 0:
        completed_trainings = sum(1 for t in assigned_trainings if t.status == "COMPLETED" or (t.progress_percentage or 0) >= 100)
        trainings_pct = round(sum(t.progress_percentage or 0 for t in assigned_trainings) / float(total_trainings), 1)
    else:
        trainings_pct = 0.0

    # 3. Live Classes (20%)
    assigned_classes = db.query(LiveClassAttendee).filter(
        LiveClassAttendee.ase_id == ase_id
    ).all()
    total_classes = len(assigned_classes)
    attended_classes = 0
    if total_classes > 0:
        attended_classes = sum(1 for c in assigned_classes if c.attended)
        classes_pct = round((attended_classes / float(total_classes)) * 100.0, 1)
    else:
        classes_pct = 0.0

    overall = round(0.40 * assessments_pct + 0.40 * trainings_pct + 0.20 * classes_pct, 1)

    return {
        "ase_id": ase_id,
        "ase_name": ase.name,
        "overall_percentage": min(100.0, max(0.0, overall)),
        "assessments": {
            "completed": completed_assessments,
            "total": total_assessments,
            "percentage": assessments_pct,
            "weight": 40
        },
        "trainings": {
            "completed": completed_trainings,
            "total": total_trainings,
            "percentage": trainings_pct,
            "weight": 40
        },
        "live_classes": {
            "attended": attended_classes,
            "total": total_classes,
            "percentage": classes_pct,
            "weight": 20
        }
    }


# ================= PHASE 11: QUESTION ITEM ANALYSIS =================
from app.models.question import QuestionBank
from app.schemas.phase11_schemas import QuestionItemAnalyticsOut, QuestionReviewRequest
from app.services.item_analysis_service import (
    get_or_compute_analytics,
    compute_question_analytics,
    send_question_back_to_review
)

@router.get("/questions", response_model=List[QuestionItemAnalyticsOut])
def list_question_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns item analytics for questions.
    Admin sees all questions; Mentors see questions in their bank/scope.
    """
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ASEs cannot view question analytics.")

    query = db.query(QuestionBank)
    if current_user.role == UserRole.MENTOR:
        query = query.filter((QuestionBank.author_id == current_user.id) | (QuestionBank.author_id == None))

    questions = query.all()
    results = []
    for q in questions:
        an = get_or_compute_analytics(db, q.id, q.version)
        results.append(an)
    return results


@router.get("/questions/{question_id}", response_model=QuestionItemAnalyticsOut)
def get_question_item_analysis(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns detailed item analysis for a specific question."""
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ASEs cannot view question analytics.")

    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    if current_user.role == UserRole.MENTOR and question.author_id not in (None, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this question.")

    return get_or_compute_analytics(db, question.id, question.version)


@router.post("/questions/{question_id}/review", response_model=QuestionItemAnalyticsOut)
def flag_question_for_review(
    question_id: int,
    payload: QuestionReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """One-click 'send back to review' for questions with quality flags."""
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ASEs cannot flag questions for review.")

    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    if current_user.role == UserRole.MENTOR and question.author_id not in (None, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this question.")

    return send_question_back_to_review(db, question_id, payload.reason, current_user.id)


@router.post("/questions/{question_id}/recalculate", response_model=QuestionItemAnalyticsOut)
def recalculate_question_analytics(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually forces recomputation of item analysis for a question."""
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ASEs cannot recalculate analytics.")

    return compute_question_analytics(db, question_id)


