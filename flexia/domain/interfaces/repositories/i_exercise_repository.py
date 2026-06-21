from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.exercise import Exercise

class IExerciseRepository(ABC):
    @abstractmethod
    def get_by_id(self, exercise_id: UUID) -> Optional[Exercise]: ...

    @abstractmethod
    def get_all_available(self, center_id: UUID) -> List[Exercise]: ...
    # Devuelve globales + los del centro
