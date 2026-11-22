from datetime import datetime, date, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_admin
from app.models.user import User, UserRole
from app.models.quote import MotivationalQuote
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.schemas.quote import (
    MotivationalQuoteCreate,
    MotivationalQuoteUpdate,
    MotivationalQuoteOut,
    DailyQuoteOut
)

router = APIRouter(prefix="/quotes", tags=["quotes"])

EPOCH_DATE = date(2024, 1, 1)

@router.get("/daily")
def get_daily_quote(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get deterministic daily quote for current user role.
    Also returns should_show_splash flag.
    Never show splash if user currently has an IN_PROGRESS assessment attempt.
    """
    today_date = datetime.now(timezone.utc).date()
    today_str = today_date.isoformat()
    
    # Check if user has an IN_PROGRESS assessment attempt
    in_progress_attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == current_user.id,
        AssessmentAttempt.status == AttemptStatus.IN_PROGRESS
    ).first()
    
    should_show = False
    if not in_progress_attempt:
        # Show on fresh login or once per day
        user_last_date = current_user.last_splash_date
        is_fresh = getattr(current_user, "fresh_login", False)
        if is_fresh or user_last_date != today_str:
            should_show = True

    # Role normalization
    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    user_role_str = user_role_str.upper()

    quotes = db.query(MotivationalQuote).filter(
        MotivationalQuote.role == user_role_str,
        MotivationalQuote.is_active == True
    ).order_by(MotivationalQuote.id.asc()).all()

    if not quotes:
        quote_data = {
            "id": 0,
            "role": user_role_str,
            "text": "Consistency and deliberate practice turn potential into excellence.",
            "author": "L&K Team",
            "date": today_str,
            "dismiss_timeout_ms": 5000
        }
    else:
        # Deterministic day index
        day_diff = (today_date - EPOCH_DATE).days
        chosen_idx = day_diff % len(quotes)
        q = quotes[chosen_idx]
        quote_data = {
            "id": q.id,
            "role": q.role,
            "text": q.text,
            "author": q.author,
            "date": today_str,
            "dismiss_timeout_ms": 5000
        }

    return {
        "should_show_splash": should_show,
        "quote": quote_data
    }

@router.post("/ack-splash")
def acknowledge_splash(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark that the user has seen or dismissed the splash screen.
    """
    today_str = datetime.now(timezone.utc).date().isoformat()
    current_user.last_splash_date = today_str
    current_user.fresh_login = False
    db.commit()
    return {"message": "Splash acknowledged", "date": today_str}

# Admin CRUD
@router.get("/admin", response_model=List[MotivationalQuoteOut])
def list_quotes_admin(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(MotivationalQuote)
    if role:
        query = query.filter(MotivationalQuote.role == role.upper())
    if is_active is not None:
        query = query.filter(MotivationalQuote.is_active == is_active)
    return query.order_by(MotivationalQuote.id.asc()).all()

@router.post("/admin", response_model=MotivationalQuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote_admin(
    quote_in: MotivationalQuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    new_quote = MotivationalQuote(
        role=quote_in.role.upper(),
        text=quote_in.text.strip(),
        author=quote_in.author.strip() or "L&K Team",
        is_active=quote_in.is_active,
        is_demo=False
    )
    db.add(new_quote)
    db.commit()
    db.refresh(new_quote)
    return new_quote

@router.put("/admin/{quote_id}", response_model=MotivationalQuoteOut)
def update_quote_admin(
    quote_id: int,
    quote_in: MotivationalQuoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    quote = db.query(MotivationalQuote).filter(MotivationalQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if quote_in.role is not None:
        quote.role = quote_in.role.upper()
    if quote_in.text is not None:
        quote.text = quote_in.text.strip()
    if quote_in.author is not None:
        quote.author = quote_in.author.strip()
    if quote_in.is_active is not None:
        quote.is_active = quote_in.is_active

    db.commit()
    db.refresh(quote)
    return quote

@router.delete("/admin/{quote_id}")
def delete_quote_admin(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    quote = db.query(MotivationalQuote).filter(MotivationalQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    db.delete(quote)
    db.commit()
    return {"message": "Quote deleted"}
