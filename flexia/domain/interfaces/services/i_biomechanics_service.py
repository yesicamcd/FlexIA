from abc import ABC, abstractmethod
from domain.models.exercise_result import ExerciseResult
from typing import List

class IBiomechanicsService(ABC):
    @abstractmethod
    def process_video(self, video_path: str, exercises: list) -> List[ExerciseResult]: ...
