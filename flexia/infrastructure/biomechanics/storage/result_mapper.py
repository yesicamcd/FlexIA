"""
infrastructure/biomechanics/storage/result_mapper.py

Convierte el SessionState interno del motor biomecanico
en los tipos del dominio para persistir en Supabase.

Estructura real de Supabase:
    sessions.patient_routine_id  -> FK a patient_routines
    exercise_results.routine_exercise_id -> FK a routine_exercises
    sessions no tiene updated_at
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from domain.models.exercise_result import ExerciseResult
from domain.value_objects.ifi_score import IfiScore
from infrastructure.biomechanics.analysis.ifi_calculator import IfiResult
from infrastructure.biomechanics.pipeline.session_state import (
    ExerciseState,
    SessionState,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MappedSessionResult:
    """
    Resultado completo de una sesion listo para persistir en Supabase.

    Atributos:
        session_id: UUID de la sesion.
        exercise_results: lista de ExerciseResult del dominio.
        ifi_score: IFI calculado. None si no hubo datos suficientes.
        session_fields: campos a actualizar en la tabla sessions.
        duration_seconds: duracion total de la sesion.
        total_frames: frames procesados durante la sesion.
    """

    session_id: str
    exercise_results: list[ExerciseResult]
    ifi_score: Optional[IfiScore]
    session_fields: dict
    duration_seconds: Optional[float]
    total_frames: int

    @property
    def was_successful(self) -> bool:
        return len(self.exercise_results) > 0


class ResultMapper:
    """
    Convierte SessionState en tipos del dominio para persistencia.

    Requiere el mapeo de exercise_id -> routine_exercise_id porque
    exercise_results referencia routine_exercises, no exercises directamente.

    Uso:
        mapper = ResultMapper()
        mapped = mapper.map(
            session_state=state,
            ifi_result=ifi_result,
            exercise_to_routine_exercise={
                'uuid-exercise': 'uuid-routine-exercise',
            },
        )
    """

    def map(
        self,
        session_state: SessionState,
        exercise_to_routine_exercise: dict[str, str],
        ifi_result: Optional[IfiResult] = None,
    ) -> MappedSessionResult:
        """
        Convierte el estado completo de la sesion en el resultado
        listo para persistir.

        Args:
            session_state: estado final de la sesion biomecanica.
            exercise_to_routine_exercise: diccionario que mapea
                exercise_id -> routine_exercise_id. Necesario porque
                exercise_results usa routine_exercise_id como FK.
            ifi_result: resultado del calculo del IFI.

        Returns:
            MappedSessionResult con todos los datos para Supabase.
        """
        exercise_results = self._map_exercise_results(
            session_state=session_state,
            exercise_to_routine_exercise=exercise_to_routine_exercise,
        )
        ifi_score = ifi_result.score if ifi_result is not None else None
        session_fields = self._build_session_fields(ifi_score=ifi_score)

        logger.info(
            "Sesion %s mapeada: %d ejercicios, IFI=%s.",
            session_state.session_id[:8],
            len(exercise_results),
            f"{ifi_score.value:.1f}" if ifi_score else "N/A",
        )

        return MappedSessionResult(
            session_id=session_state.session_id,
            exercise_results=exercise_results,
            ifi_score=ifi_score,
            session_fields=session_fields,
            duration_seconds=session_state.duration_seconds,
            total_frames=session_state.total_frames_processed,
        )

    def _map_exercise_results(
        self,
        session_state: SessionState,
        exercise_to_routine_exercise: dict[str, str],
    ) -> list[ExerciseResult]:
        results = []
        for index, exercise_state in enumerate(session_state.completed_exercises):
            result = self._map_single_exercise(
                exercise_state=exercise_state,
                session_id=session_state.session_id,
                order_index=index,
                exercise_to_routine_exercise=exercise_to_routine_exercise,
            )
            if result is not None:
                results.append(result)
        return results

    def _map_single_exercise(
        self,
        exercise_state: ExerciseState,
        session_id: str,
        order_index: int,
        exercise_to_routine_exercise: dict[str, str],
    ) -> Optional[ExerciseResult]:
        if not exercise_state.rom_history:
            logger.warning(
                "Ejercicio '%s' sin mediciones de ROM. No se persistira.",
                exercise_state.exercise_name,
            )
            return None

        routine_exercise_id = exercise_to_routine_exercise.get(
            exercise_state.exercise_id
        )
        if routine_exercise_id is None:
            logger.warning(
                "No se encontro routine_exercise_id para exercise '%s'. "
                "No se persistira.",
                exercise_state.exercise_id,
            )
            return None

        avg_rom_percentage = exercise_state.average_rom_percentage or 0.0
        rep_counter = exercise_state.rep_counter
        performance = exercise_state.dominant_performance
        rom_achieved = self._calculate_average_rom_achieved(exercise_state)
        rom_expected = exercise_state.rom_history[0].expected_degrees

        return ExerciseResult(
            id=uuid4(),
            session_id=session_id,
            routine_exercise_id=routine_exercise_id,
            order_index=order_index,
            rom_achieved=round(rom_achieved, 2),
            rom_expected=round(rom_expected, 2),
            rom_percentage=round(avg_rom_percentage, 2),
            reps_achieved=rep_counter.valid_reps,
            reps_expected=rep_counter.reps_expected,
            performance=performance.value if performance else None,
            ifi_contribution=None,
            landmarks_json=None,
            frame_count=len(exercise_state.rom_history),
            created_at=datetime.now(),
        )

    def _calculate_average_rom_achieved(
        self,
        exercise_state: ExerciseState,
    ) -> float:
        if not exercise_state.rom_history:
            return 0.0
        return sum(r.achieved_degrees for r in exercise_state.rom_history) / len(
            exercise_state.rom_history
        )

    def _build_session_fields(
        self,
        ifi_score: Optional[IfiScore],
    ) -> dict:
        """
        Construye los campos a actualizar en sessions.
        Solo incluye columnas que existen en la tabla real.
        sessions no tiene updated_at.
        """
        from shared.constants import SESSION_COMPLETED

        fields = {"status": SESSION_COMPLETED}

        if ifi_score is not None:
            fields["ifi_score"] = round(ifi_score.value, 2)

        return fields