from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class RoutineExercise:
    id: UUID
    routine_id: UUID
    exercise_id: UUID
    order_index: int
    reps_override: Optional[int]
    notes: Optional[str]
    created_at: datetime
