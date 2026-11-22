from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict

class ResourceItem(BaseModel):
    name: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    type: str = "link" # link, file

class TrainingBase(BaseModel):
    title: str
    description: Optional[str] = None
    skill_category: str
    type: str = "Self-paced" # Self-paced, Live class, Workshop
    resources: List[ResourceItem] = []
    duration_hours: float = 1.0

class TrainingCreate(TrainingBase):
    pass

class TrainingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    skill_category: Optional[str] = None
    type: Optional[str] = None
    resources: Optional[List[ResourceItem]] = None
    duration_hours: Optional[float] = None

class TrainingOut(TrainingBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingAssignPayload(BaseModel):
    target: str = "SELECTED" # ALL, COHORT, SELECTED
    cohort_id: Optional[int] = None
    ase_ids: Optional[List[int]] = None
    due_date: datetime

class TrainingProgressUpdate(BaseModel):
    progress_percent: float # 0.0 to 100.0
    status: Optional[str] = None # NOT_STARTED, IN_PROGRESS, COMPLETED

class TrainingAssignmentOut(BaseModel):
    id: int
    training_id: int
    training_title: str
    training_description: Optional[str] = None
    skill_category: str
    training_type: str
    duration_hours: float
    resources: List[ResourceItem] = []
    ase_id: int
    ase_name: str
    ase_email: str
    cohort_id: Optional[int] = None
    cohort_name: Optional[str] = None
    due_date: datetime
    status: str
    progress_percent: float
    completed_at: Optional[datetime] = None
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)

class SuggestedAseItem(BaseModel):
    ase_id: int
    ase_name: str
    ase_email: str
    cohort_id: Optional[int] = None
    cohort_name: Optional[str] = None
    skill_category: str
    score_percentage: float
    reason: str
