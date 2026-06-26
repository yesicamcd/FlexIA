"""
domain/value_objects/ifi_score.py

Representa el Indice Funcional Integrado (IFI) de una sesion.
Es un indicador clinico compuesto que resume el desempeno global
del paciente en todos los ejercicios de la sesion.
Es inmutable: una vez calculado, no puede modificarse.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.constants import GREEN_THRESHOLD, YELLOW_THRESHOLD


@dataclass(frozen=True)
class IfiScore:
    """
    Indice Funcional Integrado para una sesion completa.

    Atributos:
        value: puntaje entre 0.0 y 100.0 que representa el desempeno
               global ponderado del paciente en todos los ejercicios.
    """

    value: float

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(
                f"IfiScore debe estar entre 0.0 y 100.0. "
                f"Recibido: {self.value}"
            )

    @property
    def label(self) -> str:
        """
        Clasificacion clinica del puntaje.
        Usa los mismos umbrales que la evaluacion por ejercicio
        para mantener coherencia visual en toda la plataforma.

        Returns:
            'green'  si value >= GREEN_THRESHOLD * 100
            'yellow' si value >= YELLOW_THRESHOLD * 100
            'red'    en caso contrario
        """
        if self.value >= GREEN_THRESHOLD * 100:
            return "green"
        if self.value >= YELLOW_THRESHOLD * 100:
            return "yellow"
        return "red"

    @property
    def is_satisfactory(self) -> bool:
        """
        Indica si el desempeno global de la sesion es clinicamente
        satisfactorio (label verde).
        """
        return self.label == "green"

    @classmethod
    def from_percentage(cls, percentage: float) -> IfiScore:
        """
        Constructor alternativo para cuando el valor ya viene
        expresado como porcentaje entre 0 y 100.
        Redondea a dos decimales antes de crear el objeto.
        """
        return cls(value=round(percentage, 2))

    def __str__(self) -> str:
        return f"IFI: {self.value:.1f} / 100 ({self.label})"