from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.training import Training, TrainingAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.phase9_models import AILearningRoadmap
from app.services.llm_service import get_llm_provider, is_demo_mode

def get_or_generate_roadmap(db: Session, ase_id: int, force_regenerate: bool = False) -> AILearningRoadmap:
    current = db.query(AILearningRoadmap).filter(
        AILearningRoadmap.ase_id == ase_id
    ).order_by(AILearningRoadmap.id.desc()).first()

    if current and not current.is_stale and not force_regenerate:
        return current

    # 1. Identify weak skills from latest attempts
    latest_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == ase_id,
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
    ).order_by(AssessmentAttempt.id.desc()).limit(3).all()

    weak_skills = []
    for att in latest_attempts:
        if att.weak_areas and isinstance(att.weak_areas, list):
            weak_skills.extend(att.weak_areas)
        elif att.skill_percentages and isinstance(att.skill_percentages, dict):
            for skill, val in att.skill_percentages.items():
                if float(val) < 70.0:
                    weak_skills.append(skill)

    weak_skills = list(dict.fromkeys(weak_skills)) # deduplicate
    if not weak_skills:
        weak_skills = ["System Architecture & Modular Design", "Asynchronous Error Handling", "Performance Optimization"]

    # 2. Find matching trainings
    trainings = db.query(Training).all()
    matched_trainings = []
    for w in weak_skills:
        for t in trainings:
            if t.skill_category.lower() in w.lower() or w.lower() in t.skill_category.lower() or w.lower() in t.title.lower():
                if t not in matched_trainings:
                    matched_trainings.append(t)

    # 3. Build roadmap items
    roadmap_items = []
    base_date = datetime.now(timezone.utc).date()
    for idx, skill in enumerate(weak_skills[:4], start=1):
        target_training = matched_trainings[idx - 1] if len(matched_trainings) >= idx else None
        due_str = (base_date + timedelta(days=idx * 2)).strftime("%Y-%m-%d")

        item = {
            "id": f"item_{idx}_{int(datetime.now(timezone.utc).timestamp())}",
            "title": f"Mastery Drill: {skill}",
            "skill": skill,
            "training_id": target_training.id if target_training else None,
            "training_title": target_training.title if target_training else "Core Conceptual Review",
            "action": f"Review {target_training.title if target_training else skill} and complete hands-on practice lab.",
            "completed": False,
            "due_date": due_str
        }
        roadmap_items.append(item)

    # Add a final practical synthesis milestone
    roadmap_items.append({
        "id": f"item_final_{int(datetime.now(timezone.utc).timestamp())}",
        "title": "Comprehensive Self-Evaluation Drill",
        "skill": "Integration & Readiness",
        "training_id": None,
        "training_title": "Timed Practice Evaluation",
        "action": "Take a 20-minute practice simulation covering this week's prioritized topics.",
        "completed": False,
        "due_date": (base_date + timedelta(days=7)).strftime("%Y-%m-%d")
    })

    version = (current.version + 1) if current else 1
    new_roadmap = AILearningRoadmap(
        ase_id=ase_id,
        week_number=1,
        generated_from_weak_skills=weak_skills,
        roadmap_items_json=roadmap_items,
        version=version,
        is_stale=False
    )
    db.add(new_roadmap)
    db.commit()
    db.refresh(new_roadmap)
    return new_roadmap

def update_roadmap_item_status(db: Session, ase_id: int, roadmap_id: int, item_id: str, completed: bool) -> AILearningRoadmap:
    roadmap = db.query(AILearningRoadmap).filter(
        AILearningRoadmap.id == roadmap_id,
        AILearningRoadmap.ase_id == ase_id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning roadmap not found.")

    items = list(roadmap.roadmap_items_json or [])
    found = False
    for item in items:
        if item.get("id") == item_id:
            item["completed"] = completed
            found = True
            break

    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap item not found.")

    roadmap.roadmap_items_json = items
    db.commit()
    db.refresh(roadmap)
    return roadmap
