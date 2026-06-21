from dataclasses import dataclass
from typing import Optional

@dataclass
class ExerciseResultDTO:
    exercise_id: str
    exercise_name: str
    rom_achieved: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    performance: Optional[str]   # green | yellow | red
