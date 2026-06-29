"""
app/use_cases/patients/create_patient_use_case.py

Caso de uso: dar de alta un paciente en el sistema.
"""

from __future__ import annotations

import logging
from uuid import uuid4, UUID
from datetime import datetime

from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from domain.models.patient import Patient
from app.dto.patient_dto import CreatePatientDTO, PatientDTO

logger = logging.getLogger(__name__)


class CreatePatientUseCase:

    def __init__(self, repository: IPatientRepository) -> None:
        self._repo = repository

    def execute(
        self,
        data: CreatePatientDTO,
        center_id: UUID,
        created_by: UUID,
    ) -> PatientDTO:
        """
        Crea un nuevo paciente en el centro indicado.

        Args:
            data: datos del formulario de alta.
            center_id: UUID del centro del profesional logueado.
            created_by: UUID del profesional que da de alta.

        Returns:
            PatientDTO con los datos del paciente creado.
        """
        patient = Patient(
            id=uuid4(),
            center_id=center_id,
            created_by=created_by,
            full_name=data.full_name,
            birth_date=data.birth_date,
            gender=data.gender,
            diagnosis=data.diagnosis,
            notes=data.notes,
            is_active=True,
            created_at=datetime.now(),
        )

        saved = self._repo.save(patient)

        logger.info(
            "Paciente '%s' creado en centro %s.",
            saved.full_name,
            str(center_id)[:8],
        )

        return PatientDTO(
            id=str(saved.id),
            full_name=saved.full_name,
            birth_date=saved.birth_date,
            gender=saved.gender,
            diagnosis=saved.diagnosis,
            is_active=saved.is_active,
        )