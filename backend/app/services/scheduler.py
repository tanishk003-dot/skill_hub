import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.notification import ReminderSent
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.training import TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.ai_class_summary import ClassTranscript
from app.services.notification_service import create_notification

logger = logging.getLogger("skillhub.scheduler")

def process_due_reminders(db: Session) -> int:
    """
    Checks for upcoming deadlines within 24 hours and sends idempotent reminders.
    Returns count of sent reminders.
    """
    sent_count = 0
    now = datetime.now(timezone.utc)
    in_24h = now + timedelta(hours=24)

    # 1. Assessment assignments due within 24 hours
    due_assessments = (
        db.query(AssessmentAssignment)
        .filter(
            AssessmentAssignment.end_date > now,
            AssessmentAssignment.end_date <= in_24h
        )
        .all()
    )
    for aa in due_assessments:
        # Check if already completed
        attempt = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.assessment_assignment_id == aa.id,
            AssessmentAttempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED", "AUTO_SUBMITTED_VIOLATION"])
        ).first()
        if attempt:
            continue

        # Check idempotent record
        already_sent = db.query(ReminderSent).filter_by(
            user_id=aa.ase_id,
            entity_type="ASSESSMENT",
            entity_id=aa.id,
            reminder_type="24H_BEFORE"
        ).first()
        if not already_sent:
            reminder_rec = ReminderSent(
                user_id=aa.ase_id,
                entity_type="ASSESSMENT",
                entity_id=aa.id,
                reminder_type="24H_BEFORE",
                sent_at=now,
                is_demo=aa.is_demo
            )
            db.add(reminder_rec)
            db.commit()

            title = "Reminder: Assessment Due Soon"
            msg = f"Your assigned assessment '{aa.assessment.title if aa.assessment else 'Assessment'}' is due in less than 24 hours ({aa.end_date.strftime('%Y-%m-%d %H:%M UTC')}). Please complete it on time."
            create_notification(
                db=db,
                user_id=aa.ase_id,
                title=title,
                message=msg,
                notification_type="REMINDER",
                link="/ase/my-assessments",
                is_demo=aa.is_demo
            )
            sent_count += 1

    # 2. Training assignments due within 24 hours
    due_trainings = (
        db.query(TrainingAssignment)
        .filter(
            TrainingAssignment.due_date > now,
            TrainingAssignment.due_date <= in_24h,
            TrainingAssignment.status != "COMPLETED"
        )
        .all()
    )
    for ta in due_trainings:
        already_sent = db.query(ReminderSent).filter_by(
            user_id=ta.ase_id,
            entity_type="TRAINING",
            entity_id=ta.id,
            reminder_type="24H_BEFORE"
        ).first()
        if not already_sent:
            reminder_rec = ReminderSent(
                user_id=ta.ase_id,
                entity_type="TRAINING",
                entity_id=ta.id,
                reminder_type="24H_BEFORE",
                sent_at=now,
                is_demo=ta.is_demo
            )
            db.add(reminder_rec)
            db.commit()

            title = "Reminder: Training Due Soon"
            msg = f"Your training '{ta.training.title if ta.training else 'Training'}' is due in less than 24 hours ({ta.due_date.strftime('%Y-%m-%d %H:%M UTC')}). Current progress: {ta.progress_percent:.0f}%."
            create_notification(
                db=db,
                user_id=ta.ase_id,
                title=title,
                message=msg,
                notification_type="REMINDER",
                link="/ase/learning",
                is_demo=ta.is_demo
            )
            sent_count += 1

    # 3. Live classes starting within 24 hours
    upcoming_classes = (
        db.query(LiveClass)
        .filter(
            LiveClass.start_time > now,
            LiveClass.start_time <= in_24h
        )
        .all()
    )
    for lc in upcoming_classes:
        for attendee in lc.attendees:
            already_sent = db.query(ReminderSent).filter_by(
                user_id=attendee.ase_id,
                entity_type="LIVE_CLASS",
                entity_id=lc.id,
                reminder_type="24H_BEFORE"
            ).first()
            if not already_sent:
                reminder_rec = ReminderSent(
                    user_id=attendee.ase_id,
                    entity_type="LIVE_CLASS",
                    entity_id=lc.id,
                    reminder_type="24H_BEFORE",
                    sent_at=now,
                    is_demo=lc.is_demo
                )
                db.add(reminder_rec)
                db.commit()

                title = "Reminder: Live Class Scheduled Tomorrow"
                msg = f"Your live class '{lc.title}' starts in less than 24 hours at {lc.start_time.strftime('%Y-%m-%d %H:%M UTC')}. Click the calendar or meeting link to join."
                create_notification(
                    db=db,
                    user_id=attendee.ase_id,
                    title=title,
                    message=msg,
                    notification_type="REMINDER",
                    link="/ase/schedule",
                    is_demo=lc.is_demo
                )
                sent_count += 1

    return sent_count

def cleanup_expired_transcripts(db: Session) -> int:
    """
    Retention policy: auto-deletes raw_text for transcripts exceeding TRANSCRIPT_RETENTION_DAYS.
    Summaries and metadata remain intact. Never logs transcript content.
    """
    now = datetime.now(timezone.utc)
    expired = db.query(ClassTranscript).filter(
        ClassTranscript.expires_at <= now,
        ClassTranscript.raw_text != None
    ).all()

    cleaned = 0
    for t in expired:
        t.raw_text = None
        cleaned += 1

    if cleaned > 0:
        db.commit()
    return cleaned

async def start_scheduler_loop(interval_seconds: int = 120):
    """
    Background worker that runs every `interval_seconds` to check for reminders.
    Robustly catches all errors so the server never crashes.
    """
    logger.info("Starting background reminder scheduler loop...")
    while True:
        try:
            with SessionLocal() as db:
                count = process_due_reminders(db)
                if count > 0:
                    logger.info(f"[SCHEDULER] Dispatched {count} deadline reminders.")
                cleaned_transcripts = cleanup_expired_transcripts(db)
                if cleaned_transcripts > 0:
                    logger.info(f"[RETENTION] Auto-purged raw text for {cleaned_transcripts} expired transcripts.")
        except Exception as e:
            logger.error(f"[SCHEDULER ERROR] Failure during reminder check: {str(e)}", exc_info=True)
        
        await asyncio.sleep(interval_seconds)
