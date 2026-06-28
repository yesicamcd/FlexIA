"""
infrastructure/biomechanics/pipeline/session_runner.py

Dirige el flujo completo de una sesion biomecanica.

Secuencia:
    1. Validacion pre-sesion (camaras, iluminacion, encuadre)
    2. Cuenta regresiva antes del primer ejercicio
    3. Loop de ejercicios:
        a. Configurar FrameProcessor para el ejercicio actual
        b. Procesar frames hasta que el ejercicio termine
        c. Descanso entre ejercicios
        d. Cuenta regresiva para el siguiente
    4. Cierre de camaras y grabacion
    5. Devolver SessionState completo para persistencia

Es el unico modulo que conoce la secuencia completa de una sesion.
No implementa ninguna logica biomecanica — solo orquesta.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2

from infrastructure.biomechanics.analysis.extensions.anthropometric_adapter import (
    AnthropometricAdapter,
    ResolvedExerciseParams,
)
from infrastructure.biomechanics.analysis.ifi_calculator import (
    ExerciseIfiInput,
    IfiCalculator,
    IfiResult,
)
from infrastructure.biomechanics.analysis.performance_evaluator import (
    PerformanceEvaluator,
)
from infrastructure.biomechanics.analysis.pose_estimator import PoseEstimator
from infrastructure.biomechanics.analysis.rep_counter import RepCounter
from infrastructure.biomechanics.analysis.rom_calculator import RomCalculator
from infrastructure.biomechanics.capture.dual_capture import DualCapture
from infrastructure.biomechanics.capture.session_validator import SessionValidator
from infrastructure.biomechanics.capture.video_recorder import VideoRecorder
from infrastructure.biomechanics.feedback.audio_alert import AudioAlert
from infrastructure.biomechanics.feedback.visual_renderer import VisualRenderer
from infrastructure.biomechanics.pipeline.countdown import (
    Countdown,
    CountdownCancelled,
)
from infrastructure.biomechanics.pipeline.frame_processor import (
    ExerciseConfig,
    FrameProcessor,
)
from infrastructure.biomechanics.pipeline.session_state import (
    ExerciseState,
    SessionPhase,
    SessionState,
)
from shared.constants import CAPTURE_FPS

logger = logging.getLogger(__name__)

# Tecla para finalizar el ejercicio actual manualmente
_NEXT_KEY: int = ord("n")

# Tecla para abortar la sesion completa
_ABORT_KEY: int = ord("q")

# Segundos de descanso entre ejercicios
_REST_SECONDS: int = 10

# Nombre de la ventana principal de OpenCV
_WINDOW_NAME: str = "FlexIA"


@dataclass(frozen=True)
class ExerciseDefinition:
    """
    Definicion de un ejercicio para ejecutar en la sesion.

    Construida por mediapipe_service.py a partir de los datos
    cargados de Supabase antes de iniciar la sesion.

    Atributos:
        exercise_id: UUID del ejercicio en Supabase.
        exercise_name: nombre del ejercicio.
        joint_name: articulacion a evaluar.
        side: lado ('left', 'right', 'bilateral').
        rom_max: rango maximo esperado en grados.
        rom_min: rango minimo en grados.
        reps_expected: repeticiones esperadas.
        green_threshold: proporcion minima para verde.
        yellow_threshold: proporcion minima para amarillo.
        ifi_weight: peso del ejercicio en el calculo del IFI.
    """

    exercise_id: str
    exercise_name: str
    joint_name: str
    side: str
    rom_max: float
    rom_min: float
    reps_expected: int
    green_threshold: float
    yellow_threshold: float
    ifi_weight: float = 1.0


@dataclass
class SessionRunnerConfig:
    """
    Configuracion del runner para una sesion especifica.

    Atributos:
        session_id: UUID de la sesion en Supabase.
        patient_id: UUID del paciente.
        professional_id: UUID del profesional.
        exercises: lista de ejercicios en orden de ejecucion.
        rest_seconds: segundos de descanso entre ejercicios.
        front_camera_index: indice OpenCV de la camara frontal.
        lateral_camera_index: indice OpenCV de la camara lateral.
        record_video: si True graba ambas camaras a disco.
    """

    session_id: str
    patient_id: str
    professional_id: str
    exercises: list[ExerciseDefinition]
    rest_seconds: int = _REST_SECONDS
    front_camera_index: int = 0
    lateral_camera_index: int = 1
    record_video: bool = True


class SessionRunner:
    """
    Dirige el flujo completo de una sesion biomecanica.

    Una instancia por sesion. No es reutilizable — crear una
    instancia nueva para cada sesion.

    Uso:
        runner = SessionRunner(
            pose_estimator=estimator,
            rom_calculator=calculator,
            performance_evaluator=evaluator,
            ifi_calculator=ifi_calc,
            anthropometric_adapter=adapter,
            audio_alert=audio,
            visual_renderer=renderer,
        )
        state = runner.run(config)
        # state contiene todos los resultados para persistir
    """

    def __init__(
        self,
        pose_estimator: PoseEstimator,
        rom_calculator: RomCalculator,
        performance_evaluator: PerformanceEvaluator,
        ifi_calculator: IfiCalculator,
        anthropometric_adapter: AnthropometricAdapter,
        audio_alert: AudioAlert,
        visual_renderer: VisualRenderer,
    ) -> None:
        self._estimator = pose_estimator
        self._rom_calculator = rom_calculator
        self._evaluator = performance_evaluator
        self._ifi_calculator = ifi_calculator
        self._adapter = anthropometric_adapter
        self._audio = audio_alert
        self._renderer = visual_renderer

    def run(self, config: SessionRunnerConfig) -> SessionState:
        """
        Ejecuta la sesion completa y devuelve el estado final.

        Este metodo es bloqueante — retorna cuando la sesion
        termina, ya sea por completarse todos los ejercicios,
        por cancelacion del usuario, o por error de hardware.

        Args:
            config: configuracion completa de la sesion.

        Returns:
            SessionState con todos los resultados de la sesion.
            Siempre devuelve un estado, incluso si la sesion
            fue abortada — el caller decide que persistir.
        """
        state = SessionState(
            session_id=config.session_id,
            patient_id=config.patient_id,
            professional_id=config.professional_id,
        )

        capture = DualCapture(
            front_index=config.front_camera_index,
            lateral_index=config.lateral_camera_index,
        )

        try:
            capture.open()
        except Exception as e:
            state.abort(f"No se pudieron abrir las camaras: {e}")
            return state

        recorders = self._build_recorders(config) if config.record_video else []

        try:
            self._run_session(state, config, capture, recorders)
        except Exception as e:
            logger.error("Error inesperado en la sesion: %s", str(e), exc_info=True)
            state.abort(f"Error inesperado: {e}")
        finally:
            self._cleanup(capture, recorders)

        return state

    def _run_session(
        self,
        state: SessionState,
        config: SessionRunnerConfig,
        capture: DualCapture,
        recorders: list[VideoRecorder],
    ) -> None:
        """
        Logica interna de la sesion despues de abrir las camaras.
        Separada de run() para que el finally de cleanup
        siempre se ejecute independientemente del resultado.
        """
        validator = SessionValidator(self._estimator)
        state.phase = SessionPhase.VALIDATING

        if not self._run_validation(state, config, capture, validator):
            return

        processor = FrameProcessor(
            pose_estimator=self._estimator,
            rom_calculator=self._rom_calculator,
            performance_evaluator=self._evaluator,
            audio_alert=self._audio,
            visual_renderer=self._renderer,
        )

        countdown = Countdown(
            capture=capture,
            audio=self._audio,
            renderer=self._renderer,
            window_name=_WINDOW_NAME,
        )

        self._build_exercise_states(state, config)

        for recorder in recorders:
            recorder.start()

        cv2.namedWindow(_WINDOW_NAME, cv2.WINDOW_NORMAL)

        for i, exercise_def in enumerate(config.exercises):
            if state.is_finished:
                break

            current_exercise = state.exercises[i]
            state.phase = SessionPhase.COUNTDOWN

            params = self._resolve_params(
                exercise_def=exercise_def,
                patient_id=config.patient_id,
            )

            exercise_config = ExerciseConfig(
                exercise_id=exercise_def.exercise_id,
                exercise_name=exercise_def.exercise_name,
                joint_name=exercise_def.joint_name,
                side=exercise_def.side,
                params=params,
            )
            processor.set_exercise_config(exercise_config)

            try:
                countdown.run(exercise_name=exercise_def.exercise_name)
            except CountdownCancelled:
                state.abort("Sesion cancelada durante la cuenta regresiva.")
                return

            state.phase = SessionPhase.EXERCISING
            aborted = self._run_exercise_loop(
                state=state,
                exercise_def=exercise_def,
                processor=processor,
                capture=capture,
                recorders=recorders,
            )

            if aborted:
                return

            has_next = state.advance_to_next_exercise()

            if has_next:
                state.phase = SessionPhase.RESTING
                self._run_rest(
                    capture=capture,
                    seconds=config.rest_seconds,
                    next_exercise_name=config.exercises[i + 1].exercise_name,
                )

        if not state.is_finished:
            state.complete()
            self._calculate_and_log_ifi(state, config)

        cv2.destroyAllWindows()

    def _run_validation(
        self,
        state: SessionState,
        config: SessionRunnerConfig,
        capture: DualCapture,
        validator: SessionValidator,
    ) -> bool:
        """
        Muestra el estado de validacion en pantalla hasta que
        todos los checks pasen o el usuario cancele.

        Returns:
            True si la validacion paso.
            False si el usuario cancelo.
        """
        logger.info("Iniciando validacion pre-sesion.")
        cv2.namedWindow(_WINDOW_NAME, cv2.WINDOW_NORMAL)

        while True:
            pair = capture.read_frames()

            if pair.front is None:
                continue

            validation = validator.validate(
                front_camera=capture.front_camera,
                lateral_camera=capture.lateral_camera,
            )

            annotated = self._renderer.render_validation_status(
                frame=pair.front,
                checks=validation.as_display_dict,
            )
            cv2.imshow(_WINDOW_NAME, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == _ABORT_KEY:
                state.abort("Validacion cancelada por el usuario.")
                cv2.destroyAllWindows()
                return False

            if validation.all_passed:
                logger.info("Validacion completada. Todos los checks OK.")
                return True

    def _run_exercise_loop(
        self,
        state: SessionState,
        exercise_def: ExerciseDefinition,
        processor: FrameProcessor,
        capture: DualCapture,
        recorders: list[VideoRecorder],
    ) -> bool:
        """
        Loop principal de procesamiento de frames para un ejercicio.

        Procesa frames hasta que:
            - El usuario presiona 'n' para pasar al siguiente
            - El usuario presiona 'q' para abortar la sesion
            - Se completan las repeticiones esperadas

        Returns:
            True si la sesion fue abortada.
            False si el ejercicio termino normalmente.
        """
        reps_expected = exercise_def.reps_expected
        logger.info("Iniciando ejercicio: '%s'.", exercise_def.exercise_name)

        while True:
            pair = capture.read_frames()

            if pair.front is None:
                continue

            for recorder in recorders:
                if recorder.role.name == "FRONT" and pair.front is not None:
                    recorder.write_frame_safe(pair.front)
                elif recorder.role.name == "LATERAL" and pair.lateral is not None:
                    recorder.write_frame_safe(pair.lateral)

            result = processor.process_frame(pair.front, state)

            cv2.imshow(_WINDOW_NAME, result.annotated_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == _ABORT_KEY:
                state.abort("Sesion abortada por el usuario.")
                return True

            if key == _NEXT_KEY:
                logger.info(
                    "Ejercicio '%s' finalizado manualmente por el profesional.",
                    exercise_def.exercise_name,
                )
                return False

            current = state.current_exercise
            if current and current.rep_counter.valid_reps >= reps_expected:
                logger.info(
                    "Ejercicio '%s' completado: %d repeticiones validas.",
                    exercise_def.exercise_name,
                    current.rep_counter.valid_reps,
                )
                return False

        return False

    def _run_rest(
        self,
        capture: DualCapture,
        seconds: int,
        next_exercise_name: str,
    ) -> None:
        """
        Muestra una pantalla de descanso entre ejercicios
        con el video en vivo y el tiempo restante.
        """
        logger.info(
            "Descanso de %d segundos antes de '%s'.",
            seconds,
            next_exercise_name,
        )
        start = time.monotonic()

        while time.monotonic() - start < seconds:
            pair = capture.read_frames()
            if pair.front is None:
                continue

            remaining = int(seconds - (time.monotonic() - start))
            frame = pair.front.copy()

            cv2.putText(
                frame,
                f"Descanso — proximo: {next_exercise_name}",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (255, 255, 255), 2, cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                f"{remaining}s",
                (30, 130),
                cv2.FONT_HERSHEY_DUPLEX,
                3.0, (0, 200, 255), 4, cv2.LINE_AA,
            )

            cv2.imshow(_WINDOW_NAME, frame)
            cv2.waitKey(1)

    def _build_exercise_states(
        self,
        state: SessionState,
        config: SessionRunnerConfig,
    ) -> None:
        """
        Construye el ExerciseState para cada ejercicio definido
        y los agrega al SessionState antes de iniciar el loop.
        """
        for exercise_def in config.exercises:
            exercise_state = ExerciseState(
                exercise_id=exercise_def.exercise_id,
                exercise_name=exercise_def.exercise_name,
                joint_name=exercise_def.joint_name,
                side=exercise_def.side,
                rep_counter=RepCounter(
                    target_degrees=exercise_def.rom_max,
                    reps_expected=exercise_def.reps_expected,
                ),
            )
            state.exercises.append(exercise_state)

    def _resolve_params(
        self,
        exercise_def: ExerciseDefinition,
        patient_id: str,
    ) -> ResolvedExerciseParams:
        """
        Resuelve los parametros del ejercicio para el paciente
        usando el AnthropometricAdapter.

        Si existe configuracion personalizada en Supabase la usa.
        Si no, devuelve los valores estandar del ejercicio.
        """
        return self._adapter.resolve(
            patient_id=patient_id,
            exercise_id=exercise_def.exercise_id,
            default_rom_max=exercise_def.rom_max,
            default_rom_min=exercise_def.rom_min,
            default_reps=exercise_def.reps_expected,
            default_movement_threshold=15.0,
            default_green_threshold=exercise_def.green_threshold,
            default_yellow_threshold=exercise_def.yellow_threshold,
        )

    def _calculate_and_log_ifi(
        self,
        state: SessionState,
        config: SessionRunnerConfig,
    ) -> Optional[IfiResult]:
        """
        Calcula el IFI al finalizar la sesion y lo loguea.
        El resultado se usa en result_mapper.py para persistir.
        """
        inputs = []

        for exercise_state, exercise_def in zip(
            state.completed_exercises, config.exercises
        ):
            if exercise_state.average_rom_percentage is None:
                continue

            inputs.append(
                ExerciseIfiInput(
                    exercise_id=exercise_state.exercise_id,
                    exercise_name=exercise_state.exercise_name,
                    rom_percentage=exercise_state.average_rom_percentage,
                    rep_completion_ratio=exercise_state.rep_counter.completion_ratio,
                    weight=exercise_def.ifi_weight,
                )
            )

        if not inputs:
            logger.warning("No hay ejercicios con datos suficientes para calcular IFI.")
            return None

        try:
            result = self._ifi_calculator.calculate(inputs)
            logger.info("IFI calculado: %s", result.summary())
            return result
        except Exception as e:
            logger.error("Error al calcular IFI: %s", str(e))
            return None

    def _build_recorders(
        self,
        config: SessionRunnerConfig,
    ) -> list[VideoRecorder]:
        """
        Construye los grabadores de video para ambas camaras.
        """
        from infrastructure.biomechanics.capture.camera_manager import CameraRole

        return [
            VideoRecorder(
                session_id=config.session_id,
                role=CameraRole.FRONT,
            ),
            VideoRecorder(
                session_id=config.session_id,
                role=CameraRole.LATERAL,
            ),
        ]

    def _cleanup(
        self,
        capture: DualCapture,
        recorders: list[VideoRecorder],
    ) -> None:
        """
        Libera todos los recursos al finalizar la sesion.
        Se ejecuta siempre, incluso si la sesion fue abortada.
        """
        for recorder in recorders:
            recorder.stop()

        capture.close()
        logger.info("Recursos de sesion liberados.")