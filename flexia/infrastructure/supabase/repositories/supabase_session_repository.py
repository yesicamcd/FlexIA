"""
infrastructure/supabase/repositories/supabase_session_repository.py

Implementacion del repositorio de sesiones usando Supabase.
El join con patient_routines es necesario para filtrar por patient_id
ya que sessions referencia patient_routine_id, no patient_id directamente.
"""

from __future__ import annotations

import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from supabase import Client

from domain.interfaces.repositories.i_session_repository import ISessionRepository
from domain.models.session import Session

logger = logging.getLogger(__name__)


class SupabaseSessionRepository(ISessionRepository):

    TABLE = "sessions"

    def __init__(self, client: Client) -> None:
        self._client = client

    def get_by_id(self, session_id: UUID) -> Optional[Session]:
        response = (
            self._client.table(self.TABLE)
            .select("*")
            .eq("id", str(session_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data[0])

    def get_by_patient(self, patient_id: UUID) -> List[Session]:
        """
        Obtiene todas las sesiones de un paciente.
        Requiere join con patient_routines porque sessions
        no tiene patient_id directamente.
        """
        pr_response = (
            self._client.table("patient_routines")
            .select("id")
            .eq("patient_id", str(patient_id))
            .execute()
        )

        if not pr_response.data:
            return []

        pr_ids = [row["id"] for row in pr_response.data]

        response = (
            self._client.table(self.TABLE)
            .select("*")
            .in_("patient_routine_id", pr_ids)
            .order("session_date", desc=True)
            .execute()
        )

        return [self._to_model(row) for row in response.data]

    def save(self, session: Session) -> Session:
        row = {
            "patient_routine_id": str(session.routine_id),
            "professional_id":    str(session.professional_id),
            "status":             session.status,
            "session_date":       session.session_date.isoformat(),
            "notes":              session.notes,
        }
        response = self._client.table(self.TABLE).insert(row).execute()
        return self._to_model(response.data[0])

    def update_status(self, session_id: UUID, status: str) -> None:
        self._client.table(self.TABLE).update(
            {"status": status}
        ).eq("id", str(session_id)).execute()

    def update_ifi(self, session_id: UUID, ifi_score: float) -> None:
        self._client.table(self.TABLE).update(
            {"ifi_score": ifi_score, "status": "completed"}
        ).eq("id", str(session_id)).execute()

    def _to_model(self, row: dict) -> Session:
        return Session(
            id=UUID(row["id"]),
            patient_id=UUID(row["patient_routine_id"]),
            routine_id=UUID(row["patient_routine_id"]),
            professional_id=UUID(row["professional_id"]),
            status=row["status"],
            ifi_score=row.get("ifi_score"),
            session_date=datetime.fromisoformat(row["session_date"]),
            notes=row.get("notes"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )