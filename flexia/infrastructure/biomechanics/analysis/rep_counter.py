"""
infrastructure/biomechanics/analysis/rep_counter.py

Cuenta repeticiones validas de un ejercicio usando una maquina de estados.
Una repeticion es valida cuando el paciente alcanza el rango objetivo
y regresa a la posicion inicial dentro de los parametros configurados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from shared.constants import REP_COMPLETION_THRESHOLD, REP_MOVEMENT_THRESHOLD_DEGREES


class RepState(Enum):
    """
    Estados posibles del ciclo de una repeticion.

    WAITING:   posicion inicial o de descanso. Esperando que comience
               el movimiento hacia el rango objetivo.
    GOING:     movimiento en progreso hacia el rango objetivo.
               El angulo esta aumentando (o disminuyendo segun el ejercicio).
    RETURNING: el paciente alcanzo el rango objetivo y esta regresando
               a la posicion inicial para completar la repeticion.
    """

    WAITING = auto()
    GOING = auto()
    RETURNING = auto()


@dataclass
class RepDetail:
    """
    Registro de una repeticion completada.

    Atributos:
        rep_number: numero de la repeticion dentro del ejercicio.
        peak_degrees: angulo maximo alcanzado durante la repeticion.
        target_degrees: angulo objetivo definido para el ejercicio.
        completion_ratio: porcentaje del objetivo alcanzado (0.0 a 1.0+).
        is_valid: indica si la repeticion supero el umbral de completitud.
    """

    rep_number: int
    peak_degrees: float
    target_degrees: float
    completion_ratio: float
    is_valid: bool

    @property
    def peak_percentage(self) -> float:
        """Porcentaje del objetivo alcanzado, expresado entre 0 y 100."""
        return round(self.completion_ratio * 100, 2)


@dataclass
class RepCounter:
    """
    Maquina de estados para conteo de repeticiones.

    Una instancia por ejercicio por sesion.
    El estado interno evoluciona frame a frame mediante update().

    Uso:
        counter = RepCounter(target_degrees=120.0, reps_expected=10)
        for frame_angle in angles_from_frames:
            counter.update(frame_angle)
        print(counter.completed_reps)
        print(counter.valid_reps)
    """

    target_degrees: float
    reps_expected: int
    movement_threshold: float = REP_MOVEMENT_THRESHOLD_DEGREES
    completion_threshold: float = REP_COMPLETION_THRESHOLD

    _state: RepState = field(default=RepState.WAITING, init=False, repr=False)
    _baseline_degrees: Optional[float] = field(default=None, init=False, repr=False)
    _peak_degrees: float = field(default=0.0, init=False, repr=False)
    _rep_details: list[RepDetail] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.target_degrees <= 0:
            raise ValueError(
                f"target_degrees debe ser mayor que cero. "
                f"Recibido: {self.target_degrees}"
            )
        if self.reps_expected <= 0:
            raise ValueError(
                f"reps_expected debe ser mayor que cero. "
                f"Recibido: {self.reps_expected}"
            )

    def update(self, current_degrees: float) -> None:
        """
        Actualiza el estado del contador con el angulo del frame actual.

        Debe llamarse en cada frame mientras el ejercicio esta activo.
        El orden de llamadas importa: la maquina de estados depende
        de la secuencia temporal de angulos.

        Args:
            current_degrees: angulo articular medido en el frame actual.
        """
        if self._baseline_degrees is None:
            self._baseline_degrees = current_degrees

        if self._state == RepState.WAITING:
            self._handle_waiting(current_degrees)

        elif self._state == RepState.GOING:
            self._handle_going(current_degrees)

        elif self._state == RepState.RETURNING:
            self._handle_returning(current_degrees)

    def reset(self) -> None:
        """
        Reinicia el contador al estado inicial.
        Util cuando el kinesiologo interrumpe y reinicia un ejercicio
        sin crear una nueva sesion.
        """
        self._state = RepState.WAITING
        self._baseline_degrees = None
        self._peak_degrees = 0.0
        self._rep_details.clear()

    @property
    def completed_reps(self) -> int:
        """Total de repeticiones completadas, validas e invalidas."""
        return len(self._rep_details)

    @property
    def valid_reps(self) -> int:
        """Repeticiones que superaron el umbral de completitud."""
        return sum(1 for r in self._rep_details if r.is_valid)

    @property
    def rep_details(self) -> list[RepDetail]:
        """Lista inmutable de detalles por repeticion completada."""
        return list(self._rep_details)

    @property
    def current_state(self) -> RepState:
        """Estado actual de la maquina."""
        return self._state

    @property
    def completion_ratio(self) -> float:
        """
        Porcentaje de repeticiones validas sobre las esperadas.
        Valor entre 0.0 y 1.0+. Usado por ifi_calculator.
        """
        if self.reps_expected == 0:
            return 0.0
        return round(self.valid_reps / self.reps_expected, 4)

    def _handle_waiting(self, current_degrees: float) -> None:
        """
        En estado WAITING: detecta si el paciente inicio el movimiento.
        El movimiento se considera iniciado cuando el angulo supera
        el umbral de movimiento desde la posicion de baseline.
        """
        if self._baseline_degrees is None:
            return

        delta = abs(current_degrees - self._baseline_degrees)

        if delta >= self.movement_threshold:
            self._state = RepState.GOING
            self._peak_degrees = current_degrees

    def _handle_going(self, current_degrees: float) -> None:
        """
        En estado GOING: registra el pico maximo y detecta si el
        paciente alcanzo el objetivo y comenzo a regresar.

        El pico se actualiza en cada frame mientras el angulo crece.
        Cuando el angulo cae mas de movement_threshold desde el pico,
        se asume que el paciente comenzo el retorno.
        """
        if current_degrees > self._peak_degrees:
            self._peak_degrees = current_degrees

        has_reached_target = (
            self._peak_degrees >= self.target_degrees * self.completion_threshold
        )
        is_returning = (
            self._peak_degrees - current_degrees >= self.movement_threshold
        )

        if has_reached_target and is_returning:
            self._state = RepState.RETURNING

    def _handle_returning(self, current_degrees: float) -> None:
        """
        En estado RETURNING: detecta cuando el paciente regreso
        a la posicion inicial y registra la repeticion como completada.

        La posicion inicial se considera alcanzada cuando el angulo
        vuelve a estar dentro del umbral de movimiento respecto al baseline.
        """
        if self._baseline_degrees is None:
            return

        delta_from_baseline = abs(current_degrees - self._baseline_degrees)

        if delta_from_baseline <= self.movement_threshold:
            self._register_rep()
            self._state = RepState.WAITING
            self._baseline_degrees = current_degrees
            self._peak_degrees = 0.0

    def _register_rep(self) -> None:
        """
        Registra una repeticion completada con todos sus detalles.
        Calcula si fue valida segun el umbral de completitud.
        """
        completion_ratio = (
            self._peak_degrees / self.target_degrees
            if self.target_degrees > 0
            else 0.0
        )

        detail = RepDetail(
            rep_number=len(self._rep_details) + 1,
            peak_degrees=round(self._peak_degrees, 2),
            target_degrees=self.target_degrees,
            completion_ratio=round(completion_ratio, 4),
            is_valid=completion_ratio >= self.completion_threshold,
        )

        self._rep_details.append(detail)