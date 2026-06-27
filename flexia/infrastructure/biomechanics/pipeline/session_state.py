"""
infrastructure/biomechanics/pipeline/session_state.py

Estado mutable completo de una sesion biomecanica en curso.

Es el unico objeto con estado en el pipeline de procesamiento.
Todo lo demas es stateless — recibe este objeto, lo lee o modifica,
y lo devuelve.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from domain.value_objects.performance_label import PerformanceLabel
from domain.value_objects.rom_measurement import RomMeasurement
from infrastructure.biomechanics.analysis.rep_counter import RepCounter, RepDetail

logger = logging.getLogger(__name__)


class SessionPhase(Enum):
    """
    Fase actual de la sesion biomecanica.

    VALIDATING:  ejecutando pre-checks antes de iniciar.
    COUNTDOWN:   cuenta regresiva antes del primer ejercicio.
    EXERCISING:  ejercicio en curso, procesando frames.
    RESTING:     descanso entre ejercicios.
    COMPLETED:   todos los ejercicios finalizados.
    ABORTED:     sesion interrumpida antes de completarse.
    """

    VALIDATING = auto()
    COUNTDOWN  = auto()
    EXERCISING = auto()
    RESTING    = auto()
    COMPLETED  = auto()
    ABORTED    = auto()


@dataclass
class ExerciseState:
    """
    Estado de un ejercicio individual dentro de la sesion.

    Se crea uno por ejercicio al iniciar su ejecucion.
    Se completa cuando el ejercicio termina.

    Atributos:
        exercise_id: UUID del ejercicio.
        exercise_name: nombre del ejercicio para logs y reportes.
        joint_name: articulacion evaluada.
        side: lado evaluado ('left', 'right', 'bilateral').
        rep_counter: maquina de estados para conteo de repeticiones.
        rom_history: lista de RomMeasurement, uno por frame con deteccion.
        performance_history: lista de labels por frame.
        started_at: timestamp de inicio del ejercicio.
        completed_at: timestamp de finalizacion. None si no termino.
    """

    exercise_id: str
    exercise_name: str
    joint_name: str
    side: str
    rep_counter: RepCounter
    rom_history: list[RomMeasurement] = field(default_factory=list)
    performance_history: list[PerformanceLabel] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duracion del ejercicio en segundos. None si no termino."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def average_rom_percentage(self) -> Optional[float]:
        """
        Promedio del porcentaje de ROM alcanzado en todos los frames
        donde hubo deteccion. None si no hay mediciones.
        """
        if not self.rom_history:
            return None
        return round(
            sum(r.percentage for r in self.rom_history) / len(self.rom_history),
            2,
        )

    @property
    def dominant_performance(self) -> Optional[PerformanceLabel]:
        """
        Label de performance mas frecuente durante el ejercicio.
        Representa el desempeno global del ejercicio.
        None si no hay historial.
        """
        if not self.performance_history:
            return None
        return max(
            set(self.performance_history),
            key=self.performance_history.count,
        )

    def record_frame(
        self,
        rom: RomMeasurement,
        performance: PerformanceLabel,
    ) -> None:
        """
        Registra los resultados de un frame en el historial.
        Actualiza el rep_counter con el angulo actual.
        """
        self.rom_history.append(rom)
        self.performance_history.append(performance)
        self.rep_counter.update(rom.achieved_degrees)

    def complete(self) -> None:
        """Marca el ejercicio como completado registrando el timestamp."""
        self.completed_at = datetime.now()
        logger.info(
            "Ejercicio '%s' completado: %d reps validas de %d esperadas, "
            "ROM promedio %.1f%%.",
            self.exercise_name,
            self.rep_counter.valid_reps,
            self.rep_counter.reps_expected,
            self.average_rom_percentage or 0.0,
        )


@dataclass
class SessionState:
    """
    Estado completo de una sesion biomecanica en curso.

    Creado al inicio de la sesion por session_runner.py.
    Modificado frame a frame por frame_processor.py.
    Leido al finalizar por result_mapper.py.

    Atributos:
        session_id: UUID de la sesion en Supabase.
        patient_id: UUID del paciente.
        professional_id: UUID del profesional que conduce la sesion.
        phase: fase actual de la sesion.
        exercises: lista de ExerciseState en orden de ejecucion.
        current_exercise_index: indice del ejercicio activo en exercises.
        total_frames_processed: frames procesados desde el inicio.
        started_at: timestamp de inicio de la sesion.
        ended_at: timestamp de fin. None si sigue en curso.
        abort_reason: motivo de abandono si phase == ABORTED.
    """

    session_id: str
    patient_id: str
    professional_id: str
    phase: SessionPhase = SessionPhase.VALIDATING
    exercises: list[ExerciseState] = field(default_factory=list)
    current_exercise_index: int = 0
    total_frames_processed: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    abort_reason: Optional[str] = None

    @property
    def current_exercise(self) -> Optional[ExerciseState]:
        """
        Ejercicio actualmente en ejecucion.
        None si no hay ejercicios o el indice esta fuera de rango.
        """
        if not self.exercises:
            return None
        if self.current_exercise_index >= len(self.exercises):
            return None
        return self.exercises[self.current_exercise_index]

    @property
    def is_active(self) -> bool:
        """
        True si la sesion esta en una fase activa que procesa frames.
        """
        return self.phase in (
            SessionPhase.COUNTDOWN,
            SessionPhase.EXERCISING,
            SessionPhase.RESTING,
        )

    @property
    def is_finished(self) -> bool:
        """True si la sesion termino, exitosa o abortada."""
        return self.phase in (
            SessionPhase.COMPLETED,
            SessionPhase.ABORTED,
        )

    @property
    def completed_exercises(self) -> list[ExerciseState]:
        """Lista de ejercicios que fueron completados."""
        return [e for e in self.exercises if e.is_completed]

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duracion total de la sesion en segundos."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()

    def advance_to_next_exercise(self) -> bool:
        """
        Completa el ejercicio actual y avanza al siguiente.

        Returns:
            True si hay un ejercicio siguiente.
            False si era el ultimo — la sesion debe completarse.
        """
        current = self.current_exercise
        if current is not None and not current.is_completed:
            current.complete()

        self.current_exercise_index += 1

        if self.current_exercise_index >= len(self.exercises):
            return False

        logger.info(
            "Avanzando al ejercicio %d/%d: '%s'.",
            self.current_exercise_index + 1,
            len(self.exercises),
            self.exercises[self.current_exercise_index].exercise_name,
        )
        return True

    def complete(self) -> None:
        """
        Marca la sesion como completada exitosamente.
        Completa el ejercicio actual si no fue completado.
        """
        current = self.current_exercise
        if current is not None and not current.is_completed:
            current.complete()

        self.phase = SessionPhase.COMPLETED
        self.ended_at = datetime.now()

        logger.info(
            "Sesion %s completada. Duracion: %.1f segundos. "
            "Ejercicios completados: %d/%d.",
            self.session_id[:8],
            self.duration_seconds or 0.0,
            len(self.completed_exercises),
            len(self.exercises),
        )

    def abort(self, reason: str) -> None:
        """
        Marca la sesion como abortada con el motivo indicado.

        Args:
            reason: descripcion del motivo de abandono.
        """
        self.phase = SessionPhase.ABORTED
        self.ended_at = datetime.now()
        self.abort_reason = reason

        logger.warning(
            "Sesion %s abortada: %s.",
            self.session_id[:8],
            reason,
        )