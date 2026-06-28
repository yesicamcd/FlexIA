"""
infrastructure/biomechanics/pipeline/frame_processor.py

Procesa un frame de video en tiempo real durante una sesion biomecanica.

Por cada frame:
    1. Estima la pose con MediaPipe
    2. Calcula el ROM articular
    3. Evalua el desempeno (verde/amarillo/rojo)
    4. Actualiza el estado del ejercicio
    5. Emite feedback auditivo si corresponde
    6. Renderiza el feedback visual sobre el frame

Es el nucleo del loop en tiempo real. Debe completarse
en menos de 33ms para mantener 30fps.
No implementa logica biomecanica — solo orquesta.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from domain.value_objects.performance_label import PerformanceLabel
from domain.value_objects.rom_measurement import RomMeasurement
from infrastructure.biomechanics.analysis.extensions.anthropometric_adapter import (
    AnthropometricAdapter,
    ResolvedExerciseParams,
)
from infrastructure.biomechanics.analysis.extensions.postural_analyzer import (
    PosturalAnalyzer,
)
from infrastructure.biomechanics.analysis.performance_evaluator import (
    PerformanceEvaluator,
)
from infrastructure.biomechanics.analysis.pose_estimator import (
    PoseEstimator,
    PoseLandmarks,
)
from infrastructure.biomechanics.analysis.rep_counter import RepCounter
from infrastructure.biomechanics.analysis.rom_calculator import RomCalculator
from infrastructure.biomechanics.feedback.audio_alert import AudioAlert
from infrastructure.biomechanics.feedback.visual_renderer import (
    RenderData,
    VisualRenderer,
)
from infrastructure.biomechanics.pipeline.session_state import (
    ExerciseState,
    SessionState,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExerciseConfig:
    """
    Configuracion de un ejercicio para el procesador de frames.

    Contiene todo lo necesario para procesar un ejercicio especifico.
    Se construye una vez al inicio del ejercicio y se reutiliza
    en cada frame durante toda su duracion.

    Atributos:
        exercise_id: UUID del ejercicio en Supabase.
        exercise_name: nombre para mostrar en pantalla y logs.
        joint_name: articulacion a evaluar (ej: 'knee', 'hip_flexion').
        side: lado a evaluar ('left', 'right', 'bilateral').
        params: parametros resueltos por AnthropometricAdapter.
                Puede ser el estandar del ejercicio o personalizado
                para el paciente especifico.
    """

    exercise_id: str
    exercise_name: str
    joint_name: str
    side: str
    params: ResolvedExerciseParams


@dataclass
class FrameResult:
    """
    Resultado del procesamiento de un frame.

    Atributos:
        annotated_frame: frame con el feedback visual dibujado.
        landmarks: landmarks detectados. None si no hubo deteccion.
        rom: medicion de ROM del frame. None si no hubo deteccion.
        performance: label de performance. None si no hubo deteccion.
        pose_detected: True si MediaPipe detecto una pose en el frame.
    """

    annotated_frame: np.ndarray
    landmarks: Optional[PoseLandmarks]
    rom: Optional[RomMeasurement]
    performance: Optional[PerformanceLabel]
    pose_detected: bool


class FrameProcessor:
    """
    Procesa frames de video en tiempo real durante un ejercicio.

    Una instancia por sesion. Se reconfigura para cada ejercicio
    mediante set_exercise_config() sin necesidad de reinstanciar.

    Uso:
        processor = FrameProcessor(
            pose_estimator=estimator,
            rom_calculator=calculator,
            performance_evaluator=evaluator,
            audio_alert=audio,
            visual_renderer=renderer,
        )

        processor.set_exercise_config(config)

        while exercising:
            result = processor.process_frame(frame, session_state)
            cv2.imshow('FlexIA', result.annotated_frame)
    """

    def __init__(
        self,
        pose_estimator: PoseEstimator,
        rom_calculator: RomCalculator,
        performance_evaluator: PerformanceEvaluator,
        audio_alert: AudioAlert,
        visual_renderer: VisualRenderer,
        postural_analyzer: Optional[PosturalAnalyzer] = None,
    ) -> None:
        self._estimator = pose_estimator
        self._rom_calculator = rom_calculator
        self._evaluator = performance_evaluator
        self._audio = audio_alert
        self._renderer = visual_renderer
        self._postural = postural_analyzer
        self._exercise_config: Optional[ExerciseConfig] = None

    def set_exercise_config(self, config: ExerciseConfig) -> None:
        """
        Configura el procesador para un ejercicio especifico.

        Debe llamarse antes de process_frame() y cada vez que
        se avanza al siguiente ejercicio en la sesion.

        Args:
            config: configuracion del ejercicio a procesar.
        """
        self._exercise_config = config
        logger.info(
            "FrameProcessor configurado para '%s' — articulacion: %s (%s).",
            config.exercise_name,
            config.joint_name,
            config.side,
        )

    def process_frame(
        self,
        frame: np.ndarray,
        session_state: SessionState,
    ) -> FrameResult:
        """
        Procesa un frame completo del loop de sesion.

        Flujo interno:
            1. Estimar pose (MediaPipe)
            2. Si hay pose: calcular ROM
            3. Si hay ROM: evaluar performance
            4. Actualizar estado del ejercicio activo
            5. Emitir alerta sonora si corresponde
            6. Renderizar feedback visual
            7. Analisis postural opcional

        Si no hay pose detectada, devuelve el frame con solo
        el nombre del ejercicio y el contador de reps — sin
        modificar el estado del ejercicio.

        Args:
            frame: frame en formato BGR del frame frontal.
            session_state: estado mutable de la sesion actual.

        Returns:
            FrameResult con el frame anotado y los datos calculados.

        Raises:
            RuntimeError: si se llama sin haber configurado el ejercicio
                          con set_exercise_config().
        """
        if self._exercise_config is None:
            raise RuntimeError(
                "set_exercise_config() debe llamarse antes de process_frame()."
            )

        session_state.total_frames_processed += 1
        current_frame = session_state.total_frames_processed

        landmarks = self._estimator.estimate(frame)

        if landmarks is None:
            return self._build_result_no_pose(frame, session_state)

        rom = self._calculate_rom(landmarks)

        if rom is None:
            return self._build_result_no_pose(frame, session_state)

        performance_result = self._evaluator.evaluate(
            rom=rom,
            green_threshold=self._exercise_config.params.green_threshold,
            yellow_threshold=self._exercise_config.params.yellow_threshold,
        )

        self._update_exercise_state(session_state, rom, performance_result.label)

        if performance_result.requires_alert:
            self._audio.emit_performance(performance_result.label, current_frame)

        if self._postural is not None and self._postural.is_active:
            self._run_postural_analysis(landmarks)

        annotated = self._render(frame, session_state, landmarks, rom, performance_result.label)

        return FrameResult(
            annotated_frame=annotated,
            landmarks=landmarks,
            rom=rom,
            performance=performance_result.label,
            pose_detected=True,
        )

    def _calculate_rom(
        self,
        landmarks: PoseLandmarks,
    ) -> Optional[RomMeasurement]:
        """
        Calcula el ROM para la articulacion configurada.

        Usa calculate_bilateral() si el lado es 'bilateral',
        calculate() para lado izquierdo o derecho especifico.

        Returns:
            RomMeasurement o None si la visibilidad es insuficiente.
        """
        config = self._exercise_config
        params = config.params

        if config.side == "bilateral":
            return self._rom_calculator.calculate_bilateral(
                landmarks=landmarks,
                joint_name=config.joint_name,
                expected_degrees=params.rom_max,
            )

        return self._rom_calculator.calculate(
            landmarks=landmarks,
            joint_name=config.joint_name,
            side=config.side,
            expected_degrees=params.rom_max,
        )

    def _update_exercise_state(
        self,
        session_state: SessionState,
        rom: RomMeasurement,
        performance: PerformanceLabel,
    ) -> None:
        """
        Registra el ROM y la performance del frame en el
        estado del ejercicio activo.

        No hace nada si no hay ejercicio activo — la sesion
        puede estar en fase de descanso o transicion.
        """
        current = session_state.current_exercise
        if current is None:
            return
        current.record_frame(rom, performance)

    def _run_postural_analysis(self, landmarks: PoseLandmarks) -> None:
        """
        Ejecuta el analisis postural opcional si esta activo.
        Los resultados se loguean pero no afectan el IFI en V1.
        """
        try:
            metrics = self._postural.analyze(landmarks)
            if metrics is not None:
                logger.debug("Metricas posturales: %s", metrics)
        except NotImplementedError:
            pass
        except Exception as e:
            logger.warning("Error en analisis postural: %s", str(e))

    def _render(
        self,
        frame: np.ndarray,
        session_state: SessionState,
        landmarks: PoseLandmarks,
        rom: RomMeasurement,
        performance: PerformanceLabel,
    ) -> np.ndarray:
        """
        Construye el RenderData y delega el dibujado al VisualRenderer.
        """
        current = session_state.current_exercise
        config = self._exercise_config

        render_data = RenderData(
            landmarks=landmarks,
            rom=rom,
            rep_count=current.rep_counter.completed_reps if current else 0,
            valid_rep_count=current.rep_counter.valid_reps if current else 0,
            reps_expected=config.params.reps_expected,
            performance=performance,
            exercise_name=config.exercise_name,
            joint_name=config.joint_name,
        )

        return self._renderer.render(frame, render_data)

    def _build_result_no_pose(
        self,
        frame: np.ndarray,
        session_state: SessionState,
    ) -> FrameResult:
        """
        Construye el resultado cuando no hay pose detectada.

        Renderiza el frame con el nombre del ejercicio y el contador
        de reps pero sin landmarks ni ROM — el paciente no esta
        en cuadro o la iluminacion es insuficiente.
        """
        config = self._exercise_config
        current = session_state.current_exercise

        render_data = RenderData(
            landmarks=None,
            rom=None,
            rep_count=current.rep_counter.completed_reps if current else 0,
            valid_rep_count=current.rep_counter.valid_reps if current else 0,
            reps_expected=config.params.reps_expected if config else 0,
            performance=None,
            exercise_name=config.exercise_name if config else "",
            joint_name=config.joint_name if config else "",
        )

        annotated = self._renderer.render(frame, render_data)
        return FrameResult(
            annotated_frame=annotated,
            landmarks=None,
            rom=None,
            performance=None,
            pose_detected=False,
        )