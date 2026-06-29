"""
infrastructure/supabase/repositories/supabase_patient_repository.py

Implementacion del repositorio de pacientes usando Supabase.
"""

from __future__ import annotations

import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from supabase import Client

from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from domain.models.patient import Patient

logger = logging.getLogger(__name__)


class SupabasePatientRepository(IPatientRepository):

    TABLE = "patients"

    def __init__(self, client: Client) -> None:
        self._client = client

    def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        response = (
            self._client.table(self.TABLE)
            .select("*")
            .eq("id", str(patient_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data[0])

    def get_all_by_center(self, center_id: UUID) -> List[Patient]:
        response = (
            self._client.table(self.TABLE)
            .select("*")
            .eq("center_id", str(center_id))
            .eq("is_active", True)
            .order("full_name")
            .execute()
        )
        return [self._to_model(row) for row in response.data]

    def save(self, patient: Patient) -> Patient:
        row = {
            "center_id":   str(patient.center_id),
            "created_by":  str(patient.created_by),
            "full_name":   patient.full_name,
            "birth_date":  patient.birth_date.isoformat() if patient.birth_date else None,
            "gender":      patient.gender,
            "diagnosis":   patient.diagnosis,
            "notes":       patient.notes,
            "is_active":   patient.is_active,
        }
        response = self._client.table(self.TABLE).insert(row).execute()
        return self._to_model(response.data[0])

    def update(self, patient: Patient) -> Patient:
        row = {
            "full_name":  patient.full_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
            "gender":     patient.gender,
            "diagnosis":  patient.diagnosis,
            "notes":      patient.notes,
            "is_active":  patient.is_active,
        }
        response = (
            self._client.table(self.TABLE)
            .update(row)
            .eq("id", str(patient.id))
            .execute()
        )
        return self._to_model(response.data[0])

    def _to_model(self, row: dict) -> Patient:
        from datetime import date
        birth = None
        if row.get("birth_date"):
            birth = date.fromisoformat(row["birth_date"])
        return Patient(
            id=UUID(row["id"]),
            center_id=UUID(row["center_id"]),
            created_by=UUID(row["created_by"]),
            full_name=row["full_name"],
            birth_date=birth,
            gender=row.get("gender"),
            diagnosis=row.get("diagnosis"),
            notes=row.get("notes"),
            is_active=row["is_active"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )