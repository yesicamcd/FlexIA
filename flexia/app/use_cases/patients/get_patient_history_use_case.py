"""Caso de uso: obtener historial clinico de un paciente."""
from uuid import UUID
from typing import List
from domain.interfaces.repositories.i_session_repository import ISessionRepository
from app.dto.session_dto import SessionDTO

class GetPatientHistoryUseCase:
    def __init__(self, session_repo: ISessionRepository):
        self._session_repo = session_repo

    def execute(self, patient_id: UUID) -> List[SessionDTO]:
        # TODO: implementar
        raise NotImplementedError
