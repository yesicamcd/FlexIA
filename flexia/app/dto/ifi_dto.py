from dataclasses import dataclass
from typing import List
from app.dto.exercise_result_dto import ExerciseResultDTO

@dataclass
class IfiDTO:
    score: float
    label: str    # green | yellow | red
    results: List[ExerciseResultDTO]
