"""Caso de uso: crear paciente."""
from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from app.dto.patient_dto import CreatePatientDTO, PatientDTO

class CreatePatientUseCase:
    def __init__(self, repository: IPatientRepository):
        self._repo = repository

    def execute(self, data: CreatePatientDTO) -> PatientDTO:
        # TODO: implementar
        raise NotImplementedError
