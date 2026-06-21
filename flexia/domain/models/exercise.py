from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Exercise:
    id: UUID
    center_id: Optional[UUID]  # None = ejercicio global del sistema
    name: str
    description: Optional[str]
    target_joint: Optional[str]
    video_ref_url: Optional[str]
    rom_min: Optional[float]
    rom_max: Optional[float]
    reps_expected: Optional[int]
    green_threshold: float
    yellow_threshold: float
    is_active: bool
    created_at: datetime
