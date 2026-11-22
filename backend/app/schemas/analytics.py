from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ASEDashboardResponse(BaseModel):
    summary: Dict[str, Any]
    radar_skills: Dict[str, Any]
    section_scores: Dict[str, Any]
    progress_history: List[Dict[str, Any]]
    strong_areas: List[str]
    weak_areas: List[str]
    what_to_improve: List[Dict[str, Any]]
    latest_attempt_id: Optional[int] = None
    ai_insights: Optional[Dict[str, Any]] = None

class AIInsightsResponse(BaseModel):
    ase_id: int
    ase_name: str
    is_ai: bool
    provider: str
    demo_mode: bool
    study_plan: str
    priority_skills: List[str]
    suggested_trainings: List[Dict[str, Any]] = []
    cached: bool = False

class MentorDashboardResponse(BaseModel):
    cohort_options: List[Dict[str, Any]]
    selected_cohort_id: Optional[int] = None
    cohort_radar: Dict[str, Any]
    heatmap: Dict[str, Any]
    ranking_table: List[Dict[str, Any]]
    needs_attention: List[Dict[str, Any]]
    training_metrics: Optional[Dict[str, Any]] = None
    attendance_metrics: Optional[Dict[str, Any]] = None
    overdue_trainings: Optional[List[Dict[str, Any]]] = None

class AdminDashboardResponse(BaseModel):
    cohort_comparison: List[Dict[str, Any]]
    completion_rate: Dict[str, Any]
    org_skill_gaps: List[Dict[str, Any]]
    users_summary: Dict[str, Any]
    training_metrics: Optional[Dict[str, Any]] = None
    attendance_metrics: Optional[Dict[str, Any]] = None
    overdue_trainings: Optional[List[Dict[str, Any]]] = None
