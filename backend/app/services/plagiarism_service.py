import re
import difflib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.coding import CodingSubmission, CodingPlagiarismFlag
from app.models.user import User, UserRole

def normalize_code_for_comparison(code: str) -> str:
    """Removes comments and extraneous whitespace for robust code similarity analysis."""
    if not code:
        return ""
    # Remove single line comments (# or //)
    code = re.sub(r'(#|//).*', '', code)
    # Remove multi-line comments (/* ... */ or ''' ... ''')
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r"('''|\"\"\").*?('''|\"\"\")", '', code, flags=re.DOTALL)
    # Collapse whitespace
    tokens = code.split()
    return "".join(tokens)

def compute_similarity(code1: str, code2: str) -> float:
    """Calculates normalized sequence similarity ratio between two source code strings (0 - 100%)."""
    norm1 = normalize_code_for_comparison(code1)
    norm2 = normalize_code_for_comparison(code2)
    if not norm1 or not norm2:
        return 0.0
    matcher = difflib.SequenceMatcher(None, norm1, norm2)
    return round(matcher.ratio() * 100.0, 1)

def scan_and_record_plagiarism(db: Session, current_sub: CodingSubmission) -> List[CodingPlagiarismFlag]:
    """
    Scans prior submissions for the same question by different ASEs.
    If similarity is >= 75.0%, logs a CodingPlagiarismFlag for mentor/admin review.
    """
    prior_subs = db.query(CodingSubmission).filter(
        CodingSubmission.question_id == current_sub.question_id,
        CodingSubmission.ase_id != current_sub.ase_id
    ).all()

    new_flags = []
    for other in prior_subs:
        score = compute_similarity(current_sub.source_code, other.source_code)
        if score >= 75.0:
            # Check if already flagged
            exists = db.query(CodingPlagiarismFlag).filter(
                CodingPlagiarismFlag.question_id == current_sub.question_id,
                ((CodingPlagiarismFlag.ase1_id == current_sub.ase_id) & (CodingPlagiarismFlag.ase2_id == other.ase_id)) |
                ((CodingPlagiarismFlag.ase1_id == other.ase_id) & (CodingPlagiarismFlag.ase2_id == current_sub.ase_id))
            ).first()

            if not exists:
                flag = CodingPlagiarismFlag(
                    question_id=current_sub.question_id,
                    ase1_id=min(current_sub.ase_id, other.ase_id),
                    ase2_id=max(current_sub.ase_id, other.ase_id),
                    attempt1_id=current_sub.attempt_id if current_sub.ase_id < other.ase_id else other.attempt_id,
                    attempt2_id=other.attempt_id if current_sub.ase_id < other.ase_id else current_sub.attempt_id,
                    similarity_score=score,
                    status="FLAGGED_FOR_REVIEW"
                )
                db.add(flag)
                new_flags.append(flag)

    if new_flags:
        db.commit()
    return new_flags
