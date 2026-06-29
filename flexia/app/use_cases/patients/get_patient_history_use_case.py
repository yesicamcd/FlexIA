"""
app/use_cases/patients/get_patient_history_use_case.py

Caso de uso: obtener el historial clinico de un paciente.
Devuelve todas sus sesiones con resultados para el dashboard.

Uso desde Streamlit:
    use_case = GetPatientHistoryUseCase(supabase_client)
    history = use_case.execute(patient_id='uuid-paciente')
    for session in history:
        st.write(session['session_date'], session['ifi_score'])
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


class GetPatientHistoryUseCase:
    """
    Obtiene el historial completo de sesiones de un paciente.

    Accede directamente a Supabase con el join necesario
    entre sessions y patient_routines.

    Uso desde Streamlit:
        use_case = GetPatientHistoryUseCase(supabase_client)
        history = use_case.execute('uuid-paciente')
        for session in history:
            st.metric('IFI', session['ifi_score'])
            st.write('Estado:', session['status'])
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def execute(self, patient_id: str) -> list[dict]:
        """
        Devuelve el historial de sesiones del paciente ordenado
        por fecha descendente.

        Cada elemento del resultado contiene:
            session_id, session_date, status, ifi_score,
            routine_name, exercise_count.

        Args:
            patient_id: UUID del paciente como string.

        Returns:
            Lista de diccionarios con los datos de cada sesion.
            Lista vacia si el paciente no tiene sesiones.
        """
        pr_response = (
            self._client.table("patient_routines")
            .select("id, routine_id, routines(name)")
            .eq("patient_id", patient_id)
            .execute()
        )

        if not pr_response.data:
            return []

        pr_map = {
            row["id"]: {
                "routine_id":   row["routine_id"],
                "routine_name": row["routines"]["name"]
                if isinstance(row.get("routines"), dict)
                else "Rutina",
            }
            for row in pr_response.data
        }

        pr_ids = list(pr_map.keys())

        sessions_response = (
            self._client.table("sessions")
            .select("id, patient_routine_id, status, ifi_score, session_date, notes")
            .in_("patient_routine_id", pr_ids)
            .order("session_date", desc=True)
            .execute()
        )

        if not sessions_response.data:
            return []

        session_ids = [row["id"] for row in sessions_response.data]

        results_response = (
            self._client.table("exercise_results")
            .select("session_id, performance, rom_percentage")
            .in_("session_id", session_ids)
            .execute()
        )

        results_by_session: dict[str, list] = {}
        for row in results_response.data:
            sid = row["session_id"]
            if sid not in results_by_session:
                results_by_session[sid] = []
            results_by_session[sid].append(row)

        history = []
        for session in sessions_response.data:
            sid = session["id"]
            pr_info = pr_map.get(session["patient_routine_id"], {})
            exercise_results = results_by_session.get(sid, [])

            history.append({
                "session_id":     sid,
                "session_date":   session["session_date"],
                "status":         session["status"],
                "ifi_score":      session.get("ifi_score"),
                "routine_name":   pr_info.get("routine_name", "Rutina"),
                "exercise_count": len(exercise_results),
                "notes":          session.get("notes"),
                "results":        exercise_results,
            })

        return history