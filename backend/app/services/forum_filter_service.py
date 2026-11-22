import re
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.phase12_models import ForumFilterAuditLog

PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?|\d{3}[-.\s]?)\d{3}[-.\s]?\d{4}\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
TOKEN_REGEX = re.compile(r'(?:sk-[a-zA-Z0-9]{15,}|rpt_[a-zA-Z0-9_-]{15,}|bearer\s+[a-zA-Z0-9_\-\.]{15,})', re.IGNORECASE)

PROFANITY_TERMS = {
    "bastard", "bitch", "damn", "shit", "fuck", "asshole", "crap", "idiot", "moron", "stupid"
}

def analyze_content_safety(text: str) -> Dict[str, Any]:
    """
    Scans text for PII patterns and prohibited language.
    Returns whether the content is clean, detected categories, and user-facing warning.
    """
    if not text:
        return {"is_clean": True, "flagged_categories": [], "warning": None, "flagged_samples": []}
    
    flagged_categories = []
    flagged_samples = []

    # 1. Phone number detection
    phone_matches = PHONE_REGEX.findall(text)
    if phone_matches:
        flagged_categories.append("PHONE_PATTERN")
        flagged_samples.append("[Phone Number Detected]")

    # 2. Email detection
    email_matches = EMAIL_REGEX.findall(text)
    if email_matches:
        flagged_categories.append("EMAIL_PATTERN")
        flagged_samples.append("[Email Address Detected]")

    # 3. Secret Token / Credential detection
    token_matches = TOKEN_REGEX.findall(text)
    if token_matches:
        flagged_categories.append("CREDENTIAL_PATTERN")
        flagged_samples.append("[API Token / Key Detected]")

    # 4. Profanity check
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    found_profanity = set(words).intersection(PROFANITY_TERMS)
    if found_profanity:
        flagged_categories.append("PROFANITY")
        flagged_samples.extend([f"Term: '{w[0]}***'" for w in found_profanity])

    if flagged_categories:
        warning_msg = (
            f"Content blocked: Sensitive personal information (PII) or prohibited language detected "
            f"({', '.join(flagged_categories)}). Please remove personal contact details or sensitive tokens "
            f"before submitting."
        )
        return {
            "is_clean": False,
            "flagged_categories": flagged_categories,
            "warning": warning_msg,
            "flagged_samples": flagged_samples
        }

    return {"is_clean": True, "flagged_categories": [], "warning": None, "flagged_samples": []}


def log_filter_hit(db: Session, user_id: int, target_type: str, detected_category: str):
    """
    Logs filter detection to audit log without storing any matched PII.
    """
    audit = ForumFilterAuditLog(
        user_id=user_id,
        target_type=target_type,
        detected_category=detected_category,
        action="BLOCKED_PRE_SUBMISSION"
    )
    db.add(audit)
    db.commit()
