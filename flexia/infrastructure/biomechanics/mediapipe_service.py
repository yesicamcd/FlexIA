from __future__ import annotations

"""
infrastructure/biomechanics/mediapipe_service.py

Implementa IBiomechanicsService usando MediaPipe como motor
de vision computacional.

Es el punto de entrada unico al sistema biomecanico.
El resto del sistema (app/use_cases/) solo conoce este archivo
y la interfaz IBiomechanicsService que implementa.

Instancia y coordina todos los componentes internos:
    - PoseEstimator (MediaPipe)
    - RomCalculator, RepCounter, PerformanceEvaluator, IfiCalculator
    - AnthropometricAdapter (Supabase)
    - AudioAlert, VisualRenderer
    - SessionRunner
    - ResultMapper, VideoUploader
"""

import logging
from dataclasses import dataclass
from typing import Optional

from supabase import Client

from domain.interfaces.services.i_biomechanics_service import IBiomechanicsService
from infrastructure.biomechanics.analysis.extensions.anthropometric_adapter import (
    AnthropometricAdapter,
)
from infrastructure.biomechanics.analysis.ifi_calculator import IfiCalculator
from infrastructure.biomechanics.analysis.performance_evaluator import (
    PerformanceEvaluator,
)
from infrastructure.biomechanics.analysis.pose_estimator import PoseEstimator
from infrastructure.biomechanics.analysis.rom_calculator import RomCalculator
from infrastructure.biomechanics.feedback.audio_alert import AudioAlert
from infrastructure.biomechanics.feedback.feedback_config import FeedbackConfig
from infrastructure.biomechanics.feedback.visual_renderer import VisualRenderer
from infrastructure.biomechanics.pipeline.session_runner import (
    ExerciseDefinition,
    SessionRunner,
    SessionRunnerConfig,
)
from infrastructure.biomechanics.storage.result_mapper import ResultMapper
from infrastructure.biomechanics.storage.video_uploader import VideoUploader

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BiomechanicsSessionRequest:
    """
    Solicitud de sesion biomecanica desde la capa de aplicacion.

    Contiene todo lo necesario para ejecutar una sesion completa.
    Construida por app/use_cases/biomechanics/process_video_use_case.py

    Atributos:
        session_id: UUID de la sesion ya creada en Supabase.
        patient_id: UUID del paciente.
        professional_id: UUID del profesional que conduce la sesion.
        center_id: UUID del centro para rutas de Storage.
        exercises: lista de ejercicios en orden de ejecucion.
        exercise_to_routine_exercise: mapeo exercise_id -> routine_exercise_id
                                      necesario para persistir en exercise_results.
        feedback_config: configuracion de audio y visual para la sesion.
        front_camera_index: indice OpenCV de la camara frontal.
        lateral_camera_index: indice OpenCV de la camara lateral.
        record_video: si True graba ambas camaras.
    """

    session_id: str
    patient_id: str
    professional_id: str
    center_id: str
    exercises: list[ExerciseDefinition]
    exercise_to_routine_exercise: dict[str, str]
    feedback_config: Optional[FeedbackConfig] = None
    front_camera_index: int = 0
    lateral_camera_index: int = 1
    record_video: bool = True


@dataclass(frozen=True)
class BiomechanicsSessionResult:
    """
    Resultado de una sesion biomecanica devuelto a la capa de aplicacion.

    Atributos:
        session_id: UUID de la sesion.
        was_completed: True si la sesion se completo exitosamente.
        ifi_score: valor del IFI. None si no se pudo calcular.
        ifi_label: clasificacion del IFI (green/yellow/red).
        total_exercises: cantidad de ejercicios completados.
        total_frames: frames procesados durante la sesion.
        abort_reason: motivo de abandono si was_completed es False.
    """

    session_id: str
    was_completed: bool
    ifi_score: Optional[float]
    ifi_label: Optional[str]
    total_exercises: int
    total_frames: int
    abort_reason: Optional[str]


class MediaPipeBiomechanicsService(IBiomechanicsService):
    """
    Implementacion del servicio biomecanico usando MediaPipe.

    Instancia todos los componentes internos al crearse.
    Una instancia por aplicacion — se reutiliza entre sesiones.

    Uso:
        service = MediaPipeBiomechanicsService(
            supabase_client=client,
            feedback_config=FeedbackConfig.default(),
        )
        result = service.run_session(request)
    """

    def __init__(
        self,
        supabase_client: Client,
        feedback_config: Optional[FeedbackConfig] = None,
    ) -> None:
        self._client = supabase_client
        self._feedback_config = feedback_config or FeedbackConfig.default()

        self._pose_estimator = PoseEstimator()
        self._rom_calculator = RomCalculator()
        self._performance_evaluator = PerformanceEvaluator()
        self._ifi_calculator = IfiCalculator()
        self._anthropometric_adapter = AnthropometricAdapter(supabase_client)

        self._audio = AudioAlert(self._feedback_config)
        self._audio.initialize()

        self._renderer = VisualRenderer(self._feedback_config)
        self._result_mapper = ResultMapper()
        self._video_uploader = VideoUploader(supabase_client)

        logger.info("MediaPipeBiomechanicsService inicializado.")

    def run_session(
        self,
        request: BiomechanicsSessionRequest,
    ) -> BiomechanicsSessionResult:
        """
        Ejecuta una sesion biomecanica completa.

        Coordina el runner, el mapper y el uploader en secuencia.
        Siempre devuelve un resultado aunque la sesion sea abortada.

        Args:
            request: solicitud con todos los datos de la sesion.

        Returns:
            BiomechanicsSessionResult con el resumen de la sesion.
        """
        config = feedback_config = request.feedback_config or self._feedback_config

        runner = SessionRunner(
            pose_estimator=self._pose_estimator,
            rom_calculator=self._rom_calculator,
            performance_evaluator=self._performance_evaluator,
            ifi_calculator=self._ifi_calculator,
            anthropometric_adapter=self._anthropometric_adapter,
            audio_alert=self._audio,
            visual_renderer=self._renderer,
        )

        runner_config = SessionRunnerConfig(
            session_id=request.session_id,
            patient_id=request.patient_id,
            professional_id=request.professional_id,
            exercises=request.exercises,
            front_camera_index=request.front_camera_index,
            lateral_camera_index=request.lateral_camera_index,
            record_video=request.record_video,
        )

        logger.info(
            "Iniciando sesion biomecanica %s — %d ejercicios.",
            request.session_id[:8],
            len(request.exercises),
        )

        session_state = runner.run(runner_config)

        ifi_result = self._calculate_ifi(session_state, request)

        mapped = self._result_mapper.map(
            session_state=session_state,
            exercise_to_routine_exercise=request.exercise_to_routine_exercise,
            ifi_result=ifi_result,
        )

        self._video_uploader.upload_and_persist(
            mapped_result=mapped,
            center_id=request.center_id,
        )

        return BiomechanicsSessionResult(
            session_id=request.session_id,
            was_completed=session_state.phase.name == "COMPLETED",
            ifi_score=mapped.ifi_score.value if mapped.ifi_score else None,
            ifi_label=mapped.ifi_score.label if mapped.ifi_score else None,
            total_exercises=len(session_state.completed_exercises),
            total_frames=session_state.total_frames_processed,
            abort_reason=session_state.abort_reason,
        )

    def _calculate_ifi(self, session_state, request):
        """
        Calcula el IFI al finalizar la sesion.
        Devuelve None si no hay datos suficientes.
        """
        from infrastructure.biomechanics.analysis.ifi_calculator import (
            ExerciseIfiInput,
        )

        inputs = []
        for exercise_state in session_state.completed_exercises:
            if exercise_state.average_rom_percentage is None:
                continue

            matching_def = next(
                (e for e in request.exercises
                 if e.exercise_id == exercise_state.exercise_id),
                None,
            )
            weight = matching_def.ifi_weight if matching_def else 1.0

            inputs.append(
                ExerciseIfiInput(
                    exercise_id=exercise_state.exercise_id,
                    exercise_name=exercise_state.exercise_name,
                    rom_percentage=exercise_state.average_rom_percentage,
                    rep_completion_ratio=exercise_state.rep_counter.completion_ratio,
                    weight=weight,
                )
            )

        if not inputs:
            return None

        try:
            return self._ifi_calculator.calculate(inputs)
        except Exception as e:
            logger.error("Error al calcular IFI: %s", str(e))
            return None

    def process_video(self, video_path: str, exercises: list) -> list:
        """
        Implementacion del metodo abstracto de IBiomechanicsService.
        En V1 no se usa — el procesamiento es en tiempo real via run_session().
        Se mantiene para cumplir el contrato de la interfaz.
        """
        raise NotImplementedError(
            "process_video() no esta implementado en V1. "
            "Usar run_session() para procesamiento en tiempo real."
        )

    def shutdown(self) -> None:
        """
        Libera todos los recursos del servicio.
        Llamar al cerrar la aplicacion.
        """
        self._pose_estimator.release()
        self._audio.shutdown()
        logger.info("MediaPipeBiomechanicsService cerrado.")