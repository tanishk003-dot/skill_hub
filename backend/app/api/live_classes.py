from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.live_class import LiveClass, LiveClassAttendee
from app.schemas.live_class import (
    LiveClassCreate, LiveClassUpdate, LiveClassOut, AttendeeOut,
    AttendanceBatchUpdate
)
from app.schemas.phase13_schemas import (
    AttendancePreviewOut, AttendanceConfirmRequest, AttendanceConfirmOut
)
from app.services.attendance_provider import (
    get_attendance_provider, generate_attendance_preview, confirm_attendance_import,
    AttendanceReportError
)
from app.services.meeting_provider import get_meeting_provider, MeetingValidationError
from app.services.notification_service import create_notification

router = APIRouter(prefix="/classes", tags=["Live Classes"])

def get_mentor_mentee_ids(db: Session, mentor_id: int) -> List[int]:
    rows = db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == mentor_id).all()
    return [r[0] for r in rows]

def format_live_class_out(lc: LiveClass) -> LiveClassOut:
    attendees_out: List[AttendeeOut] = []
    total_attended = 0
    for a in lc.attendees:
        if a.status == "ATTENDED":
            total_attended += 1
        attendees_out.append(AttendeeOut(
            ase_id=a.ase_id,
            ase_name=a.ase.name if a.ase else f"ASE #{a.ase_id}",
            ase_email=a.ase.email if a.ase else "",
            status=a.status,
            marked_at=a.marked_at,
            marked_by_name=a.marker.name if a.marker else None
        ))

    return LiveClassOut(
        id=lc.id,
        title=lc.title,
        description=lc.description,
        start_time=lc.start_time,
        duration_minutes=lc.duration_minutes,
        audience_type=lc.audience_type,
        cohort_id=lc.cohort_id,
        cohort_name=lc.cohort.name if lc.cohort else None,
        meeting_link=lc.meeting_link,
        provider=lc.provider,
        created_by=lc.created_by,
        creator_name=lc.creator.name if lc.creator else None,
        total_invited=len(attendees_out),
        total_attended=total_attended,
        attendees=attendees_out,
        created_at=lc.created_at
    )

@router.get("/", response_model=List[LiveClassOut])
def list_live_classes(
    cohort_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LiveClass)

    if current_user.role == UserRole.ASE:
        # ASE only sees classes they were invited to
        invited_class_ids = db.query(LiveClassAttendee.live_class_id).filter(LiveClassAttendee.ase_id == current_user.id).all()
        class_ids = [c[0] for c in invited_class_ids]
        query = query.filter(LiveClass.id.in_(class_ids))
    elif current_user.role == UserRole.MENTOR:
        # Mentor sees classes they created or cohorts they mentor
        query = query.filter(LiveClass.created_by == current_user.id)

    if cohort_id:
        query = query.filter(LiveClass.cohort_id == cohort_id)

    classes = query.order_by(LiveClass.start_time.asc()).all()
    return [format_live_class_out(c) for c in classes]

@router.post("/", response_model=LiveClassOut, status_code=status.HTTP_201_CREATED)
def schedule_live_class(
    payload: LiveClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins and Mentors can schedule live classes.")

    # Validate meeting link through provider
    try:
        provider = get_meeting_provider(payload.provider)
        validated_link = provider.create_or_validate_link(
            link_input=payload.meeting_link,
            title=payload.title,
            duration_minutes=payload.duration_minutes
        )
    except MeetingValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    mentor_mentee_ids = get_mentor_mentee_ids(db, current_user.id) if current_user.role == UserRole.MENTOR else []

    # Determine invited ASEs (Requirement 1: support ALL, COHORT, SELECTED)
    target_ase_ids: List[int] = []
    if payload.audience_type == "ALL":
        if current_user.role == UserRole.MENTOR:
            target_ase_ids = mentor_mentee_ids
        else:
            ases = db.query(User.id).filter(User.role == UserRole.ASE, User.is_active == True).all()
            target_ase_ids = [a[0] for a in ases]
    elif payload.audience_type == "COHORT":
        if not payload.cohort_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cohort_id is required when audience is COHORT.")
        members = db.query(CohortMember.ase_id).filter(CohortMember.cohort_id == payload.cohort_id).all()
        cohort_ases = [m[0] for m in members]
        if current_user.role == UserRole.MENTOR:
            target_ase_ids = [aid for aid in cohort_ases if aid in mentor_mentee_ids]
        else:
            target_ase_ids = cohort_ases
    elif payload.audience_type == "SELECTED":
        if not payload.ase_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ase_ids list cannot be empty for SELECTED audience.")
        if current_user.role == UserRole.MENTOR:
            unauthorized = [aid for aid in payload.ase_ids if aid not in mentor_mentee_ids]
            if unauthorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentors can invite only their own assigned mentees to live classes."
                )
        target_ase_ids = payload.ase_ids
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audience_type.")

    live_class = LiveClass(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        audience_type=payload.audience_type,
        cohort_id=payload.cohort_id,
        meeting_link=validated_link,
        provider=payload.provider,
        created_by=current_user.id
    )
    db.add(live_class)
    db.commit()
    db.refresh(live_class)

    # Populate live_class_attendees for every invited ASE
    for ase_id in set(target_ase_ids):
        attendee = LiveClassAttendee(
            live_class_id=live_class.id,
            ase_id=ase_id,
            status="INVITED"
        )
        db.add(attendee)

        # Notify ASE
        create_notification(
            db=db,
            user_id=ase_id,
            title=f"New Live Class: {live_class.title}",
            message=f"You are invited to '{live_class.title}' scheduled for {live_class.start_time.strftime('%Y-%m-%d %H:%M UTC')}. Meeting link: {validated_link}",
            notification_type="LIVE_CLASS",
            link="/ase/schedule"
        )

    db.commit()
    db.refresh(live_class)

    return format_live_class_out(live_class)

@router.get("/{class_id}", response_model=LiveClassOut)
def get_live_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")
    
    # ASE check
    if current_user.role == UserRole.ASE:
        is_invited = any(a.ase_id == current_user.id for a in lc.attendees)
        if not is_invited:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not invited to this live class.")

    return format_live_class_out(lc)

@router.put("/{class_id}", response_model=LiveClassOut)
def update_live_class(
    class_id: int,
    payload: LiveClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to edit live class.")

    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only edit their own scheduled classes.")

    original_start_time = lc.start_time
    is_rescheduled = False

    if payload.meeting_link is not None:
        try:
            provider = get_meeting_provider(payload.provider or lc.provider)
            lc.meeting_link = provider.create_or_validate_link(payload.meeting_link)
        except MeetingValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if payload.title is not None:
        lc.title = payload.title
    if payload.description is not None:
        lc.description = payload.description
    if payload.duration_minutes is not None:
        lc.duration_minutes = payload.duration_minutes
    if payload.cohort_id is not None:
        lc.cohort_id = payload.cohort_id

    if payload.start_time is not None and payload.start_time != original_start_time:
        lc.start_time = payload.start_time
        is_rescheduled = True

    db.commit()
    db.refresh(lc)

    # Requirement 9: When a class is rescheduled, notify the invited ASEs.
    if is_rescheduled:
        for attendee in lc.attendees:
            create_notification(
                db=db,
                user_id=attendee.ase_id,
                title=f"Rescheduled: {lc.title}",
                message=f"The live class '{lc.title}' has been rescheduled to {lc.start_time.strftime('%Y-%m-%d %H:%M UTC')}. Meeting link: {lc.meeting_link}",
                notification_type="LIVE_CLASS",
                link="/ase/schedule"
            )

    return format_live_class_out(lc)

@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_live_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to delete live class.")

    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only delete their own classes.")

    db.delete(lc)
    db.commit()
    return None

@router.get("/{class_id}/attendance", response_model=List[AttendeeOut])
def get_class_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only view attendance for their own classes.")

    attendees_out: List[AttendeeOut] = []
    for a in lc.attendees:
        attendees_out.append(AttendeeOut(
            ase_id=a.ase_id,
            ase_name=a.ase.name if a.ase else f"ASE #{a.ase_id}",
            ase_email=a.ase.email if a.ase else "",
            status=a.status,
            marked_at=a.marked_at,
            marked_by_name=a.marker.name if a.marker else None
        ))
    return attendees_out

@router.put("/{class_id}/attendance")
def mark_class_attendance(
    class_id: int,
    payload: AttendanceBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 8: Attendance can be marked only by the class creator mentor or admin, and only for invited ASEs.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to mark attendance.")

    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attendance can be marked only by the class creator mentor or admin."
        )

    invited_map = {a.ase_id: a for a in lc.attendees}
    now = datetime.now(timezone.utc)
    updated_count = 0

    for item in payload.attendances:
        if item.ase_id not in invited_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ASE #{item.ase_id} was not invited to this live class. Cannot mark attendance."
            )
        
        attendee_rec = invited_map[item.ase_id]
        attendee_rec.status = item.status
        attendee_rec.marked_at = now
        attendee_rec.marked_by = current_user.id
        updated_count += 1

    db.commit()
    return {"message": f"Updated attendance for {updated_count} engineer(s).", "count": updated_count}

@router.get("/{class_id}/attendance/import-preview", response_model=AttendancePreviewOut)
def preview_teams_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Imports attendance report from Teams Graph or Mock, matches by email/UPN (case-insensitive),
    and returns an unconfirmed suggestion preview.
    Only the class owner mentor or admin can import attendance.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to import attendance.")

    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attendance can only be imported by the class owner mentor or admin."
        )

    provider = get_attendance_provider()
    try:
        raw_records = provider.fetch_attendance_report(
            meeting_id_or_url=lc.meeting_link,
            organizer_email=lc.creator.email if lc.creator else None
        )
    except AttendanceReportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    preview = generate_attendance_preview(
        db=db,
        live_class=lc,
        raw_records=raw_records,
        imported_by_user_id=current_user.id
    )
    return preview

@router.post("/{class_id}/attendance/import-confirm", response_model=AttendanceConfirmOut)
def confirm_teams_attendance(
    class_id: int,
    payload: AttendanceConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mentor confirms the suggested mappings.
    Updates LiveClassAttendee records and deletes raw staging data.
    Only the class owner mentor or admin can confirm.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to confirm attendance.")

    lc = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attendance can only be confirmed by the class owner mentor or admin."
        )

    mappings_dict = [m.model_dump() for m in payload.mappings]
    try:
        result = confirm_attendance_import(
            db=db,
            import_id=payload.import_id,
            confirmed_by_user_id=current_user.id,
            mappings=mappings_dict
        )
    except AttendanceReportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return result
