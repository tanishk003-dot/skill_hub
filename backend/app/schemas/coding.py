from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator

class TestCaseResultOut(BaseModel):
    test_case_id: int
    status: str
    is_sample: bool
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    execution_time_ms: float = 0.0
    memory_kb: float = 0.0
    error_message: Optional[str] = None
    marks_awarded: float = 0.0

    @field_validator("input", "expected_output", "actual_output", mode="after")
    @classmethod
    def strip_hidden(cls, v, info):
        # Enforce that if is_sample is False, input, expected_output, actual_output MUST be None
        # Pydantic v2 validator
        data = info.data
        if not data.get("is_sample", False):
            return None
        return v

class CodingRunRequest(BaseModel):
    attempt_id: int
    question_id: int
    language: str
    source_code: str
    custom_input: Optional[str] = None

class CodingRunResponse(BaseModel):
    status: str
    passed: bool
    results: List[TestCaseResultOut]
    stdout: Optional[str] = None
    error: Optional[str] = None
    runs_remaining: Optional[int] = None

class CodingSubmitRequest(BaseModel):
    attempt_id: int
    question_id: int
    language: str
    source_code: str

class CodingSubmitResponse(BaseModel):
    submission_id: int
    status: str
    passed_sample_cases: int
    total_sample_cases: int
    passed_hidden_cases: int
    total_hidden_cases: int
    total_passed: int
    total_cases: int
    score: float
    results: List[TestCaseResultOut]  # hidden cases have input/output stripped
    error: Optional[str] = None

class CodingSubmissionOut(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    ase_id: int
    language: str
    status: str
    score: float
    total_passed: int
    total_cases: int
    execution_time_ms: float
    memory_used_kb: float
    ai_review: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PlagiarismFlagOut(BaseModel):
    id: int
    question_id: int
    attempt1_id: int
    attempt2_id: int
    ase1_id: int
    ase1_name: str
    ase2_id: int
    ase2_name: str
    similarity_score: float
    status: str
    flagged_at: datetime
    # Absolutely NO source code field returned

class CodeReviewOut(BaseModel):
    submission_id: int
    review: str
