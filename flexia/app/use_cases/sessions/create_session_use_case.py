"""
app/use_cases/sessions/create_session_use_case.py

Caso de uso: crear una sesion de evaluacion en Supabase
antes de lanzar el motor biomecanico.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class CreateSessionRequest:
    """
    Datos necesarios para crear una sesion.

    Atributos:
        patient_routine_id: UUID del registro en patient_routines
                            que vincula el paciente con la rutina.
        professional_id: UUID del profesional que conduce la sesion.
        notes: notas opcionales del profesional.
    """

    patient_routine_id: UUID
    professional_id: UUID
    notes: Optional[str] = None


@dataclass
class CreatedSession:
    """
    Datos de la sesion creada, listos para pasarle al motor biomecanico.
    """

    session_id: str
    patient_routine_id: str
    professional_id: str
    status: str


class CreateSessionUseCase:
    """
    Crea una sesion en Supabase y devuelve el session_id
    para que el motor biomecanico pueda arrancar.

    Accede directamente al cliente Supabase porque la sesion
    es un registro simple sin logica de negocio compleja.

    Uso desde Streamlit:
        use_case = CreateSessionUseCase(supabase_client)
        session = use_case.execute(CreateSessionRequest(
            patient_routine_id=UUID('...'),
            professional_id=UUID('...'),
        ))
        # session.session_id -> pasarlo a BiomechanicsSessionRequest
    """

    TABLE = "sessions"

    def __init__(self, client: Client) -> None:
        self._client = client

    def execute(self, request: CreateSessionRequest) -> CreatedSession:
        """
        Inserta la sesion en Supabase con status 'created'.

        Returns:
            CreatedSession con el session_id generado por Supabase.

        Raises:
            Exception: si el insert falla en Supabase.
        """
        row = {
            "patient_routine_id": str(request.patient_routine_id),
            "professional_id":    str(request.professional_id),
            "status":             "created",
            "session_date":       datetime.now().isoformat(),
        }

        if request.notes:
            row["notes"] = request.notes

        response = self._client.table(self.TABLE).insert(row).execute()

        if not response.data:
            raise Exception("Supabase no devolvio datos al crear la sesion.")

        created = response.data[0]

        logger.info(
            "Sesion creada: %s para patient_routine %s.",
            created["id"][:8],
            str(request.patient_routine_id)[:8],
        )

        return CreatedSession(
            session_id=created["id"],
            patient_routine_id=created["patient_routine_id"],
            professional_id=created["professional_id"],
            status=created["status"],
        )