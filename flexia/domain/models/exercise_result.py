from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class ExerciseResult:
    id: UUID
    session_id: UUID
    exercise_id: UUID
    order_index: int
    rom_achieved: Optional[float]
    rom_expected: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    reps_expected: Optional[int]
    performance: Optional[str]    # green | yellow | red
    ifi_contribution: Optional[float]
    landmarks_json: Optional[dict]
    frame_count: Optional[int]
    created_at: datetime
