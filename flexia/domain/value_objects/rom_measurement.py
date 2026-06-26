"""
domain/value_objects/rom_measurement.py

Representa una medicion de rango de movimiento (ROM) para un ejercicio dado.
Es inmutable: una vez calculado, no puede modificarse.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RomMeasurement:
    """
    Medicion de rango de movimiento obtenida durante una sesion.

    Atributos:
        achieved_degrees: angulo real alcanzado por el paciente en grados.
        expected_degrees: angulo funcional esperado para este ejercicio,
                          cargado desde la base de datos. Representa el
                          rango funcional clinico, no el anatomico completo.
        joint_name: nombre de la articulacion evaluada (ej: 'knee', 'hip').
        side: lado evaluado. Valores posibles: 'left', 'right', 'bilateral'.
    """

    achieved_degrees: float
    expected_degrees: float
    joint_name: str
    side: str

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.achieved_degrees < 0:
            raise ValueError(
                f"achieved_degrees no puede ser negativo. "
                f"Recibido: {self.achieved_degrees}"
            )
        if self.expected_degrees <= 0:
            raise ValueError(
                f"expected_degrees debe ser mayor que cero. "
                f"Recibido: {self.expected_degrees}"
            )
        if self.side not in ("left", "right", "bilateral"):
            raise ValueError(
                f"side debe ser 'left', 'right' o 'bilateral'. "
                f"Recibido: '{self.side}'"
            )

    @property
    def percentage(self) -> float:
        """
        Porcentaje del ROM esperado que alcanzo el paciente.
        Puede superar el 100% si el paciente supera el rango funcional esperado.
        """
        return round((self.achieved_degrees / self.expected_degrees) * 100, 2)

    @property
    def deficit_degrees(self) -> float:
        """
        Diferencia en grados entre lo esperado y lo alcanzado.
        Positivo indica deficit. Negativo indica superacion del rango.
        """
        return round(self.expected_degrees - self.achieved_degrees, 2)

    @property
    def is_within_expected(self) -> bool:
        """
        Indica si el paciente alcanzo o supero el rango funcional esperado.
        """
        return self.achieved_degrees >= self.expected_degrees

    def __str__(self) -> str:
        return (
            f"ROM {self.joint_name} ({self.side}): "
            f"{self.achieved_degrees:.1f} / {self.expected_degrees:.1f} grados "
            f"({self.percentage:.1f}%)"
        )