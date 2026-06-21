"""Implementacion del repositorio de pacientes usando Supabase."""
from uuid import UUID
from typing import List, Optional
from supabase import Client
from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from domain.models.patient import Patient

class SupabasePatientRepository(IPatientRepository):
    def __init__(self, client: Client):
        self._client = client

    def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        # TODO: implementar
        raise NotImplementedError

    def get_all_by_center(self, center_id: UUID) -> List[Patient]:
        # TODO: implementar
        raise NotImplementedError

    def save(self, patient: Patient) -> Patient:
        # TODO: implementar
        raise NotImplementedError

    def update(self, patient: Patient) -> Patient:
        # TODO: implementar
        raise NotImplementedError
