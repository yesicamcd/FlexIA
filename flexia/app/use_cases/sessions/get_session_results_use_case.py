"""
app/use_cases/sessions/get_session_results_use_case.py

Caso de uso: obtener los resultados de una sesion completada.
Usado por el frontend para mostrar el dashboard post-sesion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class ExerciseResultData:
    """Resultado de un ejercicio para mostrar en el dashboard."""
    exercise_name: str
    rom_achieved: Optional[float]
    rom_expected: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    reps_expected: Optional[int]
    performance: Optional[str]
    frame_count: Optional[int]


@dataclass
class SessionResultData:
    """Resultado completo de una sesion para el dashboard."""
    session_id: str
    status: str
    ifi_score: Optional[float]
    session_date: str
    exercise_results: list[ExerciseResultData]


class GetSessionResultsUseCase:
    """
    Obtiene los resultados de una sesion desde Supabase.

    Uso desde Streamlit:
        use_case = GetSessionResultsUseCase(supabase_client)
        data = use_case.execute(session_id='uuid-sesion')
        st.metric('IFI', data.ifi_score)
        for result in data.exercise_results:
            st.write(result.exercise_name, result.rom_percentage)
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def execute(self, session_id: str) -> Optional[SessionResultData]:
        """
        Carga la sesion y sus resultados de ejercicios desde Supabase.

        Args:
            session_id: UUID de la sesion a consultar.

        Returns:
            SessionResultData con todos los datos para el dashboard,
            o None si la sesion no existe.
        """
        session_resp = (
            self._client.table("sessions")
            .select("id, status, ifi_score, session_date")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )

        if not session_resp.data:
            logger.warning("Sesion %s no encontrada.", session_id[:8])
            return None

        session = session_resp.data[0]

        results_resp = (
            self._client.table("exercise_results")
            .select(
                "rom_achieved, rom_expected, rom_percentage, "
                "reps_achieved, reps_expected, performance, frame_count, "
                "routine_exercises(exercises(name))"
            )
            .eq("session_id", session_id)
            .order("order_index")
            .execute()
        )

        exercise_results = []
        for row in results_resp.data:
            name = "Ejercicio"
            try:
                name = row["routine_exercises"]["exercises"]["name"]
            except (KeyError, TypeError):
                pass

            exercise_results.append(ExerciseResultData(
                exercise_name=name,
                rom_achieved=row.get("rom_achieved"),
                rom_expected=row.get("rom_expected"),
                rom_percentage=row.get("rom_percentage"),
                reps_achieved=row.get("reps_achieved"),
                reps_expected=row.get("reps_expected"),
                performance=row.get("performance"),
                frame_count=row.get("frame_count"),
            ))

        return SessionResultData(
            session_id=session["id"],
            status=session["status"],
            ifi_score=session.get("ifi_score"),
            session_date=session["session_date"],
            exercise_results=exercise_results,
        )