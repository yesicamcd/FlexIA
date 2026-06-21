from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Session:
    id: UUID
    patient_id: UUID
    routine_id: Optional[UUID]
    professional_id: UUID
    status: str           # created | recording | processing | completed | error
    ifi_score: Optional[float]
    session_date: datetime
    notes: Optional[str]
    created_at: datetime
