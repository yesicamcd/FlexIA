from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.session import Session

class ISessionRepository(ABC):
    @abstractmethod
    def get_by_id(self, session_id: UUID) -> Optional[Session]: ...

    @abstractmethod
    def get_by_patient(self, patient_id: UUID) -> List[Session]: ...

    @abstractmethod
    def save(self, session: Session) -> Session: ...

    @abstractmethod
    def update_status(self, session_id: UUID, status: str) -> None: ...

    @abstractmethod
    def update_ifi(self, session_id: UUID, ifi_score: float) -> None: ...
