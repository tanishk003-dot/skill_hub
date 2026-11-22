from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.phase9_models import (
    ReadinessConfig, ReadinessAuditLog, AseReadinessHistory, AseGamification
)
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.coding import CodingSubmission
from app.models.training import TrainingAssignment
from app.models.live_class import LiveClassAttendee

DEFAULT_WEIGHTS = {
    "assessment_weight": 0.30,
    "coding_weight": 0.25,
    "training_weight": 0.20,
    "attendance_weight": 0.15,
    "consistency_weight": 0.10
}

FORMULA_TEXT = (
    "Readiness Score = (Assessment Score × {w_ass:.2f}) + (Coding Score × {w_cod:.2f}) + "
    "(Training Score × {w_tra:.2f}) + (Attendance Score × {w_att:.2f}) + (Consistency Score × {w_con:.2f})"
)

LEGAL_DISCLAIMER = (
    "This score supports onboarding and learning. It is not a basis for hiring, promotion or termination decisions."
)

def get_or_create_readiness_config(db: Session) -> ReadinessConfig:
    cfg = db.query(ReadinessConfig).order_by(ReadinessConfig.id.desc()).first()
    if not cfg:
        cfg = ReadinessConfig(
            assessment_weight=DEFAULT_WEIGHTS["assessment_weight"],
            coding_weight=DEFAULT_WEIGHTS["coding_weight"],
            training_weight=DEFAULT_WEIGHTS["training_weight"],
            attendance_weight=DEFAULT_WEIGHTS["attendance_weight"],
            consistency_weight=DEFAULT_WEIGHTS["consistency_weight"]
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

def calculate_ase_readiness(db: Session, ase_id: int) -> Dict[str, Any]:
    cfg = get_or_create_readiness_config(db)
    
    # 1. Assessment score (average percentage from submitted attempts)
    attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == ase_id,
        AssessmentAttempt.status.in_([
            AttemptStatus.SUBMITTED,
            AttemptStatus.AUTO_SUBMITTED,
            AttemptStatus.AUTO_SUBMITTED_VIOLATION
        ])
    ).all()
    if attempts:
        ass_score = sum(a.percentage for a in attempts) / len(attempts)
    else:
        ass_score = 0.0

    # 2. Coding score (average percentage from coding submissions)
    submissions = db.query(CodingSubmission).filter(
        CodingSubmission.ase_id == ase_id
    ).all()
    if submissions:
        sub_scores = [
            (s.total_passed / s.total_cases * 100.0) if s.total_cases > 0 else min(100.0, s.score)
            for s in submissions
        ]
        coding_score = sum(sub_scores) / len(sub_scores)
    else:
        coding_score = 0.0

    # 3. Training score (average progress percentage)
    trainings = db.query(TrainingAssignment).filter(
        TrainingAssignment.ase_id == ase_id
    ).all()
    if trainings:
        training_score = sum(t.progress_percent for t in trainings) / len(trainings)
    else:
        training_score = 0.0

    # 4. Attendance score (attended / total invited)
    classes = db.query(LiveClassAttendee).filter(
        LiveClassAttendee.ase_id == ase_id
    ).all()
    if classes:
        attended = sum(1 for c in classes if c.status == "ATTENDED")
        att_score = (attended / len(classes)) * 100.0
    else:
        att_score = 0.0

    # 5. Consistency score (gamification streak & activity recency)
    gam = db.query(AseGamification).filter(AseGamification.ase_id == ase_id).first()
    if gam:
        streak_val = min(50.0, gam.streak_days * 10.0)
        xp_factor = min(50.0, gam.xp * 0.1)
        consistency_score = streak_val + xp_factor
    else:
        consistency_score = 0.0

    # Weighted sum
    overall = (
        (ass_score * cfg.assessment_weight) +
        (coding_score * cfg.coding_weight) +
        (training_score * cfg.training_weight) +
        (att_score * cfg.attendance_weight) +
        (consistency_score * cfg.consistency_weight)
    )
    overall = round(min(100.0, max(0.0, overall)), 1)

    formula_str = FORMULA_TEXT.format(
        w_ass=cfg.assessment_weight,
        w_cod=cfg.coding_weight,
        w_tra=cfg.training_weight,
        w_att=cfg.attendance_weight,
        w_con=cfg.consistency_weight
    )

    # 6. Skill DNA generation (Vector of core competencies)
    # Aggregate skill percentages across all attempts and submissions
    skill_sums: Dict[str, List[float]] = {}
    for att in attempts:
        if att.skill_percentages and isinstance(att.skill_percentages, dict):
            for skill, val in att.skill_percentages.items():
                skill_sums.setdefault(skill, []).append(float(val))

    # Standard default DNA axes
    dna_axes = ["Logical Thinking", "System Architecture", "Code Reliability", "Problem Solving", "Operational Resilience"]
    skill_dna: Dict[str, float] = {}
    for axis in dna_axes:
        if axis in skill_sums:
            skill_dna[axis] = round(sum(skill_sums[axis]) / len(skill_sums[axis]), 1)
        else:
            # Baseline derived from overall score
            base = max(10.0, overall * 0.85)
            skill_dna[axis] = round(base, 1)

    breakdown = {
        "assessment": {
            "score": round(ass_score, 1),
            "weight": cfg.assessment_weight,
            "weighted_value": round(ass_score * cfg.assessment_weight, 2),
            "count": len(attempts)
        },
        "coding": {
            "score": round(coding_score, 1),
            "weight": cfg.coding_weight,
            "weighted_value": round(coding_score * cfg.coding_weight, 2),
            "count": len(submissions)
        },
        "training": {
            "score": round(training_score, 1),
            "weight": cfg.training_weight,
            "weighted_value": round(training_score * cfg.training_weight, 2),
            "count": len(trainings)
        },
        "attendance": {
            "score": round(att_score, 1),
            "weight": cfg.attendance_weight,
            "weighted_value": round(att_score * cfg.attendance_weight, 2),
            "count": len(classes)
        },
        "consistency": {
            "score": round(consistency_score, 1),
            "weight": cfg.consistency_weight,
            "weighted_value": round(consistency_score * cfg.consistency_weight, 2),
            "streak_days": gam.streak_days if gam else 0
        }
    }

    # Save to history for trend tracking
    history = AseReadinessHistory(
        ase_id=ase_id,
        overall_score=overall,
        breakdown_json=breakdown,
        skill_dna_json=skill_dna,
        formula_snapshot=formula_str
    )
    db.add(history)
    db.commit()

    return {
        "ase_id": ase_id,
        "overall_score": overall,
        "breakdown": breakdown,
        "skill_dna": skill_dna,
        "formula": formula_str,
        "disclaimer": LEGAL_DISCLAIMER,
        "weights": {
            "assessment_weight": cfg.assessment_weight,
            "coding_weight": cfg.coding_weight,
            "training_weight": cfg.training_weight,
            "attendance_weight": cfg.attendance_weight,
            "consistency_weight": cfg.consistency_weight
        }
    }

def update_readiness_weights(db: Session, admin_id: int, weights: Dict[str, float]) -> ReadinessConfig:
    # Requirement 2: each between 0 and 1, total must equal 1.0 (server-side validation, 422 otherwise)
    ass_w = float(weights.get("assessment_weight", 0.0))
    cod_w = float(weights.get("coding_weight", 0.0))
    tra_w = float(weights.get("training_weight", 0.0))
    att_w = float(weights.get("attendance_weight", 0.0))
    con_w = float(weights.get("consistency_weight", 0.0))

    for w_name, val in [
        ("assessment_weight", ass_w),
        ("coding_weight", cod_w),
        ("training_weight", tra_w),
        ("attendance_weight", att_w),
        ("consistency_weight", con_w)
    ]:
        if val < 0.0 or val > 1.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Weight '{w_name}' must be between 0.0 and 1.0. Provided: {val}"
            )

    total = round(ass_w + cod_w + tra_w + att_w + con_w, 4)
    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sum of readiness weights must equal 1.0. Current sum: {total}"
        )

    current_cfg = get_or_create_readiness_config(db)
    old_weights_dict = {
        "assessment_weight": current_cfg.assessment_weight,
        "coding_weight": current_cfg.coding_weight,
        "training_weight": current_cfg.training_weight,
        "attendance_weight": current_cfg.attendance_weight,
        "consistency_weight": current_cfg.consistency_weight
    }
    new_weights_dict = {
        "assessment_weight": ass_w,
        "coding_weight": cod_w,
        "training_weight": tra_w,
        "attendance_weight": att_w,
        "consistency_weight": con_w
    }

    # Audit log
    audit = ReadinessAuditLog(
        changed_by=admin_id,
        old_weights=old_weights_dict,
        new_weights=new_weights_dict
    )
    db.add(audit)

    current_cfg.assessment_weight = ass_w
    current_cfg.coding_weight = cod_w
    current_cfg.training_weight = tra_w
    current_cfg.attendance_weight = att_w
    current_cfg.consistency_weight = con_w
    current_cfg.updated_by = admin_id
    current_cfg.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_cfg)
    return current_cfg
