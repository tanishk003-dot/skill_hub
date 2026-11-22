import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.phase11_models import StaffingProject, StaffingProjectSkill
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.training import Training
from app.services.export_service import generate_pseudonymous_id

def get_utc_now():
    return datetime.now(timezone.utc)

MATCHING_DISCLAIMER = "Decision support only. Not a basis for staffing, promotion or termination decisions."

def get_candidate_skill_levels(db: Session, ase_id: int) -> Dict[str, float]:
    """
    Computes verified skill percentages for a candidate from completed assessment attempts.
    Gracefully returns empty dict if no data.
    """
    attempts = (
        db.query(AssessmentAttempt)
        .filter(
            AssessmentAttempt.ase_id == ase_id,
            AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
        )
        .all()
    )

    skill_totals: Dict[str, List[float]] = {}
    for att in attempts:
        if att.skill_percentages and isinstance(att.skill_percentages, dict):
            for skill, pct in att.skill_percentages.items():
                try:
                    val = float(pct)
                    skill_totals.setdefault(skill.strip().lower(), []).append(val)
                except (ValueError, TypeError):
                    continue

    # Average percentage per skill
    return {skill: round(sum(vals) / len(vals), 1) for skill, vals in skill_totals.items()}


def find_recommended_training(db: Session, skill_name: str) -> Optional[Dict[str, Any]]:
    """Finds a matching training module from the trainings table for a given skill gap."""
    skill_clean = skill_name.strip().lower()
    trainings = db.query(Training).all()

    best_match = None
    for tr in trainings:
        cat_lower = (getattr(tr, "skill_category", None) or "").lower()
        title_lower = (tr.title or "").lower()
        desc_lower = (tr.description or "").lower()

        if skill_clean in cat_lower or cat_lower in skill_clean:
            best_match = tr
            break
        elif skill_clean in title_lower or skill_clean in desc_lower:
            best_match = tr
            break

    if not best_match and trainings:
        best_match = trainings[0]

    if best_match:
        duration_hours = int(getattr(best_match, "duration_hours", 20.0) or 20)
        return {
            "training_id": best_match.id,
            "title": best_match.title,
            "duration_hours": duration_hours
        }
    return None


def calculate_project_matches(
    db: Session,
    project_id: int,
    requesting_user: User
) -> Dict[str, Any]:
    """Ranks candidates for a staffing project, computes gaps, and suggests trainings."""
    # Authorization: Admins see all; Mentors see only their assigned mentees; ASEs cannot view
    if requesting_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ASEs cannot view staffing project matching.")

    project = db.query(StaffingProject).filter(StaffingProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    skills = project.skills
    if not skills:
        return {
            "project_id": project.id,
            "project_name": project.name,
            "disclaimer": MATCHING_DISCLAIMER,
            "candidates": [],
            "message": "No required skills defined for this project."
        }

    # Determine pool of candidates
    if requesting_user.role == UserRole.ADMIN:
        candidates = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True).all()
    else:
        # Mentor: assigned mentees only
        assignments = db.query(MentorAseAssignment).filter(MentorAseAssignment.mentor_id == requesting_user.id).all()
        mentee_ids = [a.ase_id for a in assignments]
        candidates = db.query(User).filter(User.id.in_(mentee_ids), User.is_active == True).all()

    total_weight_denom = sum(s.min_level_pct * (s.weight or 1.0) for s in skills)
    if total_weight_denom <= 0:
        total_weight_denom = 1.0

    ranked_candidates = []
    ready_now_threshold = project.ready_now_threshold_pct or 90.0

    for cand in candidates:
        cand_skills = get_candidate_skill_levels(db, cand.id)
        
        weighted_numerator = 0.0
        skill_breakdowns = []
        total_gap_training_hours = 0
        recommended_trainings_map = {}

        for req_skill in skills:
            s_name = req_skill.skill_name.strip()
            s_name_lower = s_name.lower()
            min_lvl = req_skill.min_level_pct
            weight = req_skill.weight or 1.0

            # Lookup level with graceful fallback to 0.0
            actual_lvl = cand_skills.get(s_name_lower, 0.0)
            
            # Capped contribution to score
            capped_lvl = min(actual_lvl, min_lvl)
            weighted_numerator += (capped_lvl * weight)

            gap = max(0.0, round(min_lvl - actual_lvl, 1))
            training_rec = None
            if gap > 0:
                rec = find_recommended_training(db, s_name)
                if rec:
                    training_rec = rec
                    if rec["training_id"] not in recommended_trainings_map:
                        recommended_trainings_map[rec["training_id"]] = rec
                        total_gap_training_hours += rec.get("duration_hours", 20)

            skill_breakdowns.append({
                "skill_name": s_name,
                "required_level_pct": min_lvl,
                "candidate_level_pct": actual_lvl,
                "gap_pct": gap,
                "weight": weight,
                "recommended_training": training_rec
            })

        match_pct = round((weighted_numerator / total_weight_denom) * 100.0, 1)

        # Classification: Ready Now vs Ready in X Weeks
        is_ready_now = (match_pct >= ready_now_threshold)
        if is_ready_now:
            readiness_label = "Ready now"
            weeks_estimate = 0
        else:
            # Assume 20 hours study per week
            weeks_estimate = max(1, math.ceil(total_gap_training_hours / 20.0))
            readiness_label = f"Ready in {weeks_estimate} week{'s' if weeks_estimate > 1 else ''}"

        ranked_candidates.append({
            "candidate_id": cand.id,
            "pseudonymous_id": generate_pseudonymous_id(cand.id),
            "name": cand.name,
            "email": cand.email,
            "match_percentage": match_pct,
            "readiness_label": readiness_label,
            "weeks_estimate": weeks_estimate,
            "is_ready_now": is_ready_now,
            "skill_breakdowns": skill_breakdowns,
            "recommended_trainings": list(recommended_trainings_map.values()),
            "formula_breakdown": {
                "weighted_numerator": round(weighted_numerator, 2),
                "weighted_denominator": round(total_weight_denom, 2),
                "formula": "Match % = (Sum(min(candidate_level, min_level) * weight) / Sum(min_level * weight)) * 100",
                "ready_now_threshold_pct": ready_now_threshold
            }
        })

    # Sort descending by match percentage
    ranked_candidates.sort(key=lambda x: x["match_percentage"], reverse=True)

    # Privacy check for small groups in aggregate:
    # If total candidate count < 3 and requesting user is mentor, keep transparent, but in aggregate views flag small group
    return {
        "project_id": project.id,
        "project_name": project.name,
        "description": project.description,
        "headcount": project.headcount,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "ready_now_threshold_pct": ready_now_threshold,
        "status": project.status,
        "disclaimer": MATCHING_DISCLAIMER,
        "total_evaluated": len(ranked_candidates),
        "candidates": ranked_candidates
    }
