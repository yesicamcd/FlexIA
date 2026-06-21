from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.patient import Patient

class IPatientRepository(ABC):
    @abstractmethod
    def get_by_id(self, patient_id: UUID) -> Optional[Patient]: ...

    @abstractmethod
    def get_all_by_center(self, center_id: UUID) -> List[Patient]: ...

    @abstractmethod
    def save(self, patient: Patient) -> Patient: ...

    @abstractmethod
    def update(self, patient: Patient) -> Patient: ...
