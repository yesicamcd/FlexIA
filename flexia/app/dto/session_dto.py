from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from app.dto.exercise_result_dto import ExerciseResultDTO

@dataclass
class SessionDTO:
    id: str
    patient_id: str
    status: str
    ifi_score: Optional[float]
    session_date: datetime
    results: List[ExerciseResultDTO]
