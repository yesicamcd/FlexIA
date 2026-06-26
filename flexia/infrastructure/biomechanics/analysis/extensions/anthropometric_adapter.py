"""
infrastructure/biomechanics/analysis/extensions/anthropometric_adapter.py

Resuelve los parametros de evaluacion biomecanica para un paciente
especifico consultando la tabla patient_exercise_config en Supabase.

Si existe una configuracion personalizada para el par (patient_id,
exercise_id), usa los overrides definidos por el kinesiologo.
Si no existe, devuelve los valores estandar del ejercicio sin
modificaciones.

Columnas de patient_exercise_config usadas:
    - rom_max_override          (numeric, nullable)
    - rom_min_override          (numeric, nullable)
    - movement_threshold_override (numeric, nullable)
    - notes                     (text, nullable)

Los umbrales verde/amarillo y reps_expected no tienen override
en la tabla actual — siempre vienen del ejercicio estandar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from supabase import Client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedExerciseParams:
    """
    Parametros de evaluacion resueltos para un paciente y ejercicio.

    Pueden ser los valores estandar del ejercicio o los valores
    personalizados definidos por el kinesiologo en Supabase.

    Atributos:
        rom_max: rango maximo esperado en grados para este paciente.
        rom_min: rango minimo de inicio del movimiento en grados.
        reps_expected: repeticiones esperadas. Siempre del estandar
                       porque la tabla no tiene override para este campo.
        movement_threshold: umbral de deteccion de inicio de movimiento
                            en grados.
        green_threshold: proporcion minima para clasificar como verde.
                         Siempre del estandar (no tiene override).
        yellow_threshold: proporcion minima para clasificar como amarillo.
                          Siempre del estandar (no tiene override).
        is_personalized: True si se aplicaron overrides del paciente.
        personalization_notes: notas clinicas del kinesiologo sobre
                               la adaptacion realizada.
    """

    rom_max: float
    rom_min: float
    reps_expected: int
    movement_threshold: float
    green_threshold: float
    yellow_threshold: float
    is_personalized: bool = False
    personalization_notes: Optional[str] = None

    def describe(self) -> str:
        """
        Descripcion textual de los parametros resueltos para logs.
        """
        source = "personalizado" if self.is_personalized else "estandar"
        lines = [
            f"Parametros ({source}):",
            f"  ROM: {self.rom_min} - {self.rom_max} grados",
            f"  Umbral movimiento: {self.movement_threshold} grados",
            f"  Umbral verde: {self.green_threshold * 100:.0f}%",
            f"  Umbral amarillo: {self.yellow_threshold * 100:.0f}%",
            f"  Repeticiones esperadas: {self.reps_expected}",
        ]
        if self.personalization_notes:
            lines.append(f"  Notas clinicas: {self.personalization_notes}")
        return "\n".join(lines)


class AnthropometricAdapter:
    """
    Resuelve los parametros correctos de evaluacion para cada paciente.

    Consulta Supabase en cada llamada a resolve(). El resultado no se
    cachea intencionalmente para que los cambios que el kinesiologo
    haga en Supabase entre sesiones se reflejen inmediatamente.

    Uso:
        adapter = AnthropometricAdapter(supabase_client)
        params = adapter.resolve(
            patient_id='uuid-paciente',
            exercise_id='uuid-ejercicio',
            default_rom_max=120.0,
            default_rom_min=0.0,
            default_reps=10,
            default_movement_threshold=15.0,
            default_green_threshold=0.85,
            default_yellow_threshold=0.60,
        )
        if params.is_personalized:
            logger.info('Usando configuracion personalizada para paciente')
        print(params.describe())
    """

    TABLE = "patient_exercise_config"

    def __init__(self, client: Client) -> None:
        self._client = client

    def resolve(
        self,
        patient_id: str,
        exercise_id: str,
        default_rom_max: float,
        default_rom_min: float,
        default_reps: int,
        default_movement_threshold: float,
        default_green_threshold: float,
        default_yellow_threshold: float,
    ) -> ResolvedExerciseParams:
        """
        Resuelve los parametros de evaluacion para un paciente y ejercicio.

        Consulta Supabase buscando un registro en patient_exercise_config
        para el par (patient_id, exercise_id). Si lo encuentra, aplica
        los overrides disponibles sobre los valores estandar. Si no lo
        encuentra, o si la consulta falla, devuelve los valores estandar
        sin interrumpir la sesion.

        La logica de fallback es intencional: un error de red no debe
        impedir que la sesion clinica continue. En ese caso se loguea
        la advertencia y se usan los valores estandar.

        Args:
            patient_id: UUID del paciente como string.
            exercise_id: UUID del ejercicio como string.
            default_rom_max: ROM maximo estandar del ejercicio en grados.
            default_rom_min: ROM minimo estandar del ejercicio en grados.
            default_reps: repeticiones estandar del ejercicio.
            default_movement_threshold: umbral estandar de movimiento
                                        en grados.
            default_green_threshold: proporcion minima para verde (0-1).
            default_yellow_threshold: proporcion minima para amarillo (0-1).

        Returns:
            ResolvedExerciseParams con los valores a usar en la sesion.
        """
        defaults = ResolvedExerciseParams(
            rom_max=default_rom_max,
            rom_min=default_rom_min,
            reps_expected=default_reps,
            movement_threshold=default_movement_threshold,
            green_threshold=default_green_threshold,
            yellow_threshold=default_yellow_threshold,
            is_personalized=False,
            personalization_notes=None,
        )

        try:
            config = self._fetch_config(patient_id, exercise_id)
        except Exception as e:
            logger.warning(
                "No se pudo consultar patient_exercise_config. "
                "Usando parametros estandar. Error: %s",
                str(e),
            )
            return defaults

        if config is None:
            logger.debug(
                "Sin configuracion personalizada para paciente %s "
                "y ejercicio %s. Usando estandar.",
                patient_id,
                exercise_id,
            )
            return defaults

        return self._apply_overrides(config, defaults)

    def _fetch_config(
        self,
        patient_id: str,
        exercise_id: str,
    ) -> Optional[dict]:
        """
        Consulta Supabase buscando la configuracion personalizada.

        Usa eq() en ambas columnas para filtrar el registro exacto.
        Devuelve None si no existe registro para ese par.

        Returns:
            Diccionario con los datos del registro,
            o None si no existe configuracion para ese paciente y ejercicio.
        """
        response = (
            self._client
            .table(self.TABLE)
            .select(
                "rom_max_override,"
                "rom_min_override,"
                "movement_threshold_override,"
                "notes"
            )
            .eq("patient_id", patient_id)
            .eq("exercise_id", exercise_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]

    def _apply_overrides(
        self,
        config: dict,
        defaults: ResolvedExerciseParams,
    ) -> ResolvedExerciseParams:
        """
        Aplica los overrides encontrados sobre los valores estandar.

        Solo sobreescribe los campos que tienen valor en Supabase.
        Si un campo es NULL en la tabla, se mantiene el valor estandar
        del ejercicio para ese parametro especifico.

        Esto permite configuraciones parciales: por ejemplo, solo
        ajustar el ROM maximo sin cambiar el umbral de movimiento.

        Args:
            config: diccionario con los datos de patient_exercise_config.
            defaults: parametros estandar del ejercicio como fallback.

        Returns:
            ResolvedExerciseParams con los overrides aplicados.
        """
        rom_max = self._resolve_value(
            config.get("rom_max_override"),
            defaults.rom_max,
        )
        rom_min = self._resolve_value(
            config.get("rom_min_override"),
            defaults.rom_min,
        )
        movement_threshold = self._resolve_value(
            config.get("movement_threshold_override"),
            defaults.movement_threshold,
        )
        notes = config.get("notes")

        resolved = ResolvedExerciseParams(
            rom_max=rom_max,
            rom_min=rom_min,
            reps_expected=defaults.reps_expected,
            movement_threshold=movement_threshold,
            green_threshold=defaults.green_threshold,
            yellow_threshold=defaults.yellow_threshold,
            is_personalized=True,
            personalization_notes=notes,
        )

        logger.info(
            "Configuracion personalizada aplicada para paciente. "
            "ROM max: %.1f (estandar: %.1f). "
            "ROM min: %.1f (estandar: %.1f). "
            "Umbral movimiento: %.1f (estandar: %.1f).",
            rom_max, defaults.rom_max,
            rom_min, defaults.rom_min,
            movement_threshold, defaults.movement_threshold,
        )

        return resolved

    def _resolve_value(
        self,
        override: Optional[float],
        default: float,
    ) -> float:
        """
        Devuelve el override si tiene valor, o el default si es None.
        Centraliza la logica de fallback por campo individual.
        """
        return float(override) if override is not None else default