from datetime import datetime
from pydantic import BaseModel

class AssignRequest(BaseModel):
    mentor_id: int
    ase_id: int

class AssignmentOut(BaseModel):
    id: int
    mentor_id: int
    mentor_name: str
    mentor_email: str
    ase_id: int
    ase_name: str
    ase_email: str
    assigned_at: datetime

    class Config:
        from_attributes = True
