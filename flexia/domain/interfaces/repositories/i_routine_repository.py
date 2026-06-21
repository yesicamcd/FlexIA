from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.routine import Routine

class IRoutineRepository(ABC):
    @abstractmethod
    def get_by_id(self, routine_id: UUID) -> Optional[Routine]: ...

    @abstractmethod
    def get_all_by_center(self, center_id: UUID) -> List[Routine]: ...

    @abstractmethod
    def save(self, routine: Routine) -> Routine: ...
