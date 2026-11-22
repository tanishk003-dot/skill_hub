from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.phase9_models import AseGamification, OnboardingMilestone

DEFAULT_MILESTONES = [
    # 30-Day: Foundations
    (30, "ASSESSMENT", "Complete Initial Technical & Logical Baseline Assessment"),
    (30, "TRAINING", "Finish Core Software Engineering Practices Module"),
    (30, "LIVE_CLASS", "Attend First Mentor Interactive Architecture Session"),
    (30, "REASSESSMENT", "Complete 30-Day Foundational Progress Re-Assessment"),
    
    # 60-Day: Specialization
    (60, "TRAINING", "Complete Advanced Microservices & Asynchronous Patterns"),
    (60, "ASSESSMENT", "Submit Sandboxed Coding Challenge with 80%+ Test Passing"),
    (60, "LIVE_CLASS", "Participate in Production Incident Simulation Workshop"),
    (60, "REASSESSMENT", "Complete 60-Day Midpoint Growth Re-Assessment"),

    # 90-Day: Production Readiness
    (90, "TRAINING", "Complete Observability, Security & Production Resilience Lab"),
    (90, "ASSESSMENT", "Deliver End-to-End Capstone Assessment"),
    (90, "REASSESSMENT", "Final 90-Day Readiness Graduation Evaluation")
]

BADGE_DEFINITIONS = [
    {"id": "fast_starter", "name": "Fast Starter", "icon": "bolt", "desc": "Completed first onboarding milestone within initial 7 days."},
    {"id": "consistent_learner", "name": "Consistent Learner", "icon": "local_fire_department", "desc": "Maintained an active 5-day continuous learning streak."},
    {"id": "clean_coder", "name": "Clean Code Craftsman", "icon": "verified", "desc": "Submitted a coding assessment with 100% test case pass rate."},
    {"id": "resilience_champion", "name": "Resilience Champion", "icon": "shield", "desc": "Successfully completed resilience and production readiness labs."}
]

def get_or_create_gamification(db: Session, ase_id: int) -> AseGamification:
    gam = db.query(AseGamification).filter(AseGamification.ase_id == ase_id).first()
    if not gam:
        gam = AseGamification(
            ase_id=ase_id,
            xp=100,
            level=1,
            streak_days=1,
            last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            badges_json=[BADGE_DEFINITIONS[0]], # Fast Starter
            leaderboard_opt_in=False, # STRICT DEFAULT OFF
            show_full_name_publicly=False
        )
        db.add(gam)
        db.commit()
        db.refresh(gam)
    return gam

def record_activity_and_update_streak(db: Session, ase_id: int, xp_gain: int = 25):
    gam = get_or_create_gamification(db, ase_id)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if gam.last_active_date:
        try:
            last_dt = datetime.strptime(gam.last_active_date, "%Y-%m-%d").date()
            today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
            delta = (today_dt - last_dt).days
            if delta == 1:
                gam.streak_days += 1
            elif delta > 1:
                gam.streak_days = 1
        except Exception:
            gam.streak_days = 1
    else:
        gam.streak_days = 1

    gam.last_active_date = today_str
    gam.xp += xp_gain

    # Level calculation: every 250 XP
    gam.level = max(1, (gam.xp // 250) + 1)

    # Award badge if streak >= 5
    badges = list(gam.badges_json or [])
    badge_ids = [b["id"] for b in badges]
    if gam.streak_days >= 5 and "consistent_learner" not in badge_ids:
        badges.append(BADGE_DEFINITIONS[1])
        gam.badges_json = badges

    db.commit()
    db.refresh(gam)

def get_or_create_milestones(db: Session, ase_id: int) -> List[OnboardingMilestone]:
    existing = db.query(OnboardingMilestone).filter(
        OnboardingMilestone.ase_id == ase_id
    ).order_by(OnboardingMilestone.day_phase, OnboardingMilestone.id).all()

    if not existing:
        for phase, m_type, title in DEFAULT_MILESTONES:
            m = OnboardingMilestone(
                ase_id=ase_id,
                day_phase=phase,
                milestone_type=m_type,
                title=title,
                is_completed=(phase == 30 and m_type == "ASSESSMENT") # initial completed
            )
            db.add(m)
        db.commit()
        existing = db.query(OnboardingMilestone).filter(
            OnboardingMilestone.ase_id == ase_id
        ).order_by(OnboardingMilestone.day_phase, OnboardingMilestone.id).all()

    return existing

def toggle_milestone_completion(db: Session, milestone_id: int, ase_id: int, completed: bool) -> OnboardingMilestone:
    m = db.query(OnboardingMilestone).filter(
        OnboardingMilestone.id == milestone_id,
        OnboardingMilestone.ase_id == ase_id
    ).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

    m.is_completed = completed
    m.completed_at = datetime.now(timezone.utc) if completed else None
    if completed:
        record_activity_and_update_streak(db, ase_id, xp_gain=50)
    db.commit()
    db.refresh(m)
    return m

def get_leaderboard(db: Session, current_user_id: int) -> List[Dict[str, Any]]:
    """
    Requirement 6: Opt-in only, default OFF.
    Shows ONLY: name, XP, level, streak_days, badges_count.
    NO scores, risk, or weak skills.
    """
    # Query only opted-in users
    opted_in_gam = db.query(AseGamification).filter(
        AseGamification.leaderboard_opt_in == True
    ).order_by(AseGamification.xp.desc()).all()

    leaderboard = []
    for rank, g in enumerate(opted_in_gam, start=1):
        user = db.query(User).filter(User.id == g.ase_id).first()
        if not user or not user.is_active:
            continue

        # Privacy formatting: show full name only if preference enabled
        if g.show_full_name_publicly:
            display_name = user.name
        else:
            parts = user.name.split()
            first = parts[0] if parts else "Engineer"
            last_init = f" {parts[-1][0]}." if len(parts) > 1 else ""
            display_name = f"{first}{last_init}"

        leaderboard.append({
            "rank": rank,
            "display_name": display_name,
            "level": g.level,
            "xp": g.xp,
            "streak_days": g.streak_days,
            "badges_count": len(g.badges_json or []),
            "is_me": (user.id == current_user_id)
        })

    return leaderboard
