"""
app/use_cases/biomechanics/process_video_use_case.py

Caso de uso: lanzar el motor biomecanico para una sesion.

Es el punto de conexion entre el frontend (Streamlit) y el
motor biomecanico (MediaPipeBiomechanicsService).

El frontend llama este use case pasando el session_id ya creado
y la configuracion de la sesion. El use case construye el
BiomechanicsSessionRequest y lanza la sesion completa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class ProcessSessionRequest:
    """
    Request del frontend para lanzar una sesion biomecanica.

    Atributos:
        session_id: UUID de la sesion ya creada en Supabase.
        patient_id: UUID del paciente.
        professional_id: UUID del profesional.
        center_id: UUID del centro.
        patient_routine_id: UUID del registro en patient_routines.
        front_camera_index: indice de camara frontal (default 0).
        lateral_camera_index: indice de camara lateral (default 1).
        record_video: si True graba el video.
    """

    session_id: str
    patient_id: str
    professional_id: str
    center_id: str
    patient_routine_id: str
    front_camera_index: int = 0
    lateral_camera_index: int = 1
    record_video: bool = True


@dataclass
class ProcessSessionResult:
    """
    Resultado devuelto al frontend al terminar la sesion.
    """

    session_id: str
    was_completed: bool
    ifi_score: Optional[float]
    ifi_label: Optional[str]
    total_exercises: int
    abort_reason: Optional[str]


class ProcessVideoUseCase:
    """
    Lanza el motor biomecanico para una sesion completa.

    Uso desde Streamlit:
        use_case = ProcessVideoUseCase(supabase_client)
        result = use_case.execute(ProcessSessionRequest(
            session_id='uuid-sesion',
            patient_id='uuid-paciente',
            professional_id='uuid-profesional',
            center_id='uuid-centro',
            patient_routine_id='uuid-patient-routine',
        ))
        if result.was_completed:
            st.success(f'IFI: {result.ifi_score} ({result.ifi_label})')
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def execute(self, request: ProcessSessionRequest) -> ProcessSessionResult:
        """
        Carga los ejercicios de la rutina desde Supabase,
        construye el BiomechanicsSessionRequest y lanza la sesion.

        Args:
            request: datos de la sesion desde el frontend.

        Returns:
            ProcessSessionResult con el resumen para mostrar en UI.
        """
        from shared.container import get_biomechanics_service
        from infrastructure.biomechanics.mediapipe_service import (
            BiomechanicsSessionRequest,
        )
        from infrastructure.biomechanics.pipeline.session_runner import (
            ExerciseDefinition,
        )

        exercises, exercise_map = self._load_exercises(request.patient_routine_id)

        if not exercises:
            return ProcessSessionResult(
                session_id=request.session_id,
                was_completed=False,
                ifi_score=None,
                ifi_label=None,
                total_exercises=0,
                abort_reason="La rutina no tiene ejercicios configurados.",
            )

        bio_request = BiomechanicsSessionRequest(
            session_id=request.session_id,
            patient_id=request.patient_id,
            professional_id=request.professional_id,
            center_id=request.center_id,
            exercises=exercises,
            exercise_to_routine_exercise=exercise_map,
            front_camera_index=request.front_camera_index,
            lateral_camera_index=request.lateral_camera_index,
            record_video=request.record_video,
        )

        service = get_biomechanics_service()
        bio_result = service.run_session(bio_request)

        return ProcessSessionResult(
            session_id=bio_result.session_id,
            was_completed=bio_result.was_completed,
            ifi_score=bio_result.ifi_score,
            ifi_label=bio_result.ifi_label,
            total_exercises=bio_result.total_exercises,
            abort_reason=bio_result.abort_reason,
        )

    def _load_exercises(
        self,
        patient_routine_id: str,
    ) -> tuple[list[ExerciseDefinition], dict[str, str]]:
        """
        Carga los ejercicios de la rutina desde Supabase.

        Hace join de patient_routines -> routine_exercises -> exercises
        para obtener toda la informacion necesaria.

        Returns:
            Tupla de (lista de ExerciseDefinition, mapeo exercise_id -> routine_exercise_id).
        """
        from infrastructure.biomechanics.pipeline.session_runner import ExerciseDefinition

        response = (
            self._client.table("patient_routines")
            .select("routine_id")
            .eq("id", patient_routine_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            logger.warning("patient_routine_id %s no encontrado.", patient_routine_id)
            return [], {}

        routine_id = response.data[0]["routine_id"]

        re_response = (
            self._client.table("routine_exercises")
            .select(
                "id, exercise_id, target_rom, target_reps, side_to_train, "
                "order_index, exercises(name)"
            )
            .eq("routine_id", routine_id)
            .order("order_index")
            .execute()
        )

        exercises = []
        exercise_map = {}

        for row in re_response.data:
            exercise_name = (
                row["exercises"]["name"]
                if isinstance(row.get("exercises"), dict)
                else "Ejercicio"
            )
            joint_name = self._infer_joint(exercise_name)

            ex_def = ExerciseDefinition(
                exercise_id=row["exercise_id"],
                exercise_name=exercise_name,
                joint_name=joint_name,
                side=row.get("side_to_train") or "left",
                rom_max=float(row.get("target_rom") or 120.0),
                rom_min=0.0,
                reps_expected=int(row.get("target_reps") or 10),
                green_threshold=0.85,
                yellow_threshold=0.60,
                ifi_weight=1.0,
            )
            exercises.append(ex_def)
            exercise_map[row["exercise_id"]] = row["id"]

        logger.info(
            "Rutina cargada: %d ejercicios para patient_routine %s.",
            len(exercises),
            patient_routine_id[:8],
        )

        return exercises, exercise_map

    def _infer_joint(self, exercise_name: str) -> str:
        """
        Infiere la articulacion desde el nombre del ejercicio.
        Usado como fallback hasta que exercises tenga columna joint_name.
        """
        name_lower = exercise_name.lower()
        if "knee" in name_lower or "rodilla" in name_lower:
            return "knee"
        if "hip" in name_lower or "cadera" in name_lower:
            return "hip_flexion"
        if "shoulder" in name_lower or "hombro" in name_lower:
            return "shoulder_flexion"
        if "elbow" in name_lower or "codo" in name_lower:
            return "elbow_flexion"
        if "ankle" in name_lower or "tobillo" in name_lower:
            return "ankle_dorsiflexion"
        return "knee"