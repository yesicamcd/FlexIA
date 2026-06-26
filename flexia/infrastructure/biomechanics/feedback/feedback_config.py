"""
infrastructure/biomechanics/feedback/feedback_config.py

Define la configuracion de feedback visual y auditivo para una sesion.
Configurada por el kinesiologo al iniciar la aplicacion.
Inmutable durante la sesion para garantizar consistencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AudioConfig:
    """
    Configuracion de alertas sonoras.

    Atributos:
        enabled: activa o desactiva todas las alertas sonoras.
        volume: volumen entre 0.0 (silencio) y 1.0 (maximo).
        yellow_frequency_hz: frecuencia del tono para alerta amarilla.
                             Tono mas suave, indica correccion leve.
        red_frequency_hz: frecuencia del tono para alerta roja.
                          Tono mas grave y prominente, indica error.
        duration_ms: duracion de cada beep en milisegundos.
        cooldown_frames: cantidad de frames entre alertas consecutivas
                         del mismo tipo. Evita alertas repetitivas
                         que distraigan al paciente durante el ejercicio.
    """

    enabled: bool = True
    volume: float = 0.7
    yellow_frequency_hz: int = 880
    red_frequency_hz: int = 440
    duration_ms: int = 200
    cooldown_frames: int = 30

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not (0.0 <= self.volume <= 1.0):
            raise ValueError(
                f"El volumen debe estar entre 0.0 y 1.0. "
                f"Recibido: {self.volume}"
            )
        if self.yellow_frequency_hz <= 0:
            raise ValueError(
                f"yellow_frequency_hz debe ser mayor que cero. "
                f"Recibido: {self.yellow_frequency_hz}"
            )
        if self.red_frequency_hz <= 0:
            raise ValueError(
                f"red_frequency_hz debe ser mayor que cero. "
                f"Recibido: {self.red_frequency_hz}"
            )
        if self.duration_ms <= 0:
            raise ValueError(
                f"duration_ms debe ser mayor que cero. "
                f"Recibido: {self.duration_ms}"
            )
        if self.cooldown_frames < 0:
            raise ValueError(
                f"cooldown_frames no puede ser negativo. "
                f"Recibido: {self.cooldown_frames}"
            )


@dataclass(frozen=True)
class VisualConfig:
    """
    Configuracion de feedback visual sobre el frame.

    Atributos:
        show_landmarks: muestra los puntos de pose sobre el cuerpo.
        show_skeleton: muestra las lineas del esqueleto entre landmarks.
        show_angles: muestra el angulo articular calculado en tiempo real.
        show_rep_count: muestra el contador de repeticiones en pantalla.
        show_performance_label: muestra el label verde/amarillo/rojo.
        show_rom_bar: muestra una barra de progreso del ROM actual
                      respecto al objetivo.
        landmark_color_by_visibility: colorea los landmarks segun su
                                      nivel de confianza de deteccion.
    """

    show_landmarks: bool = True
    show_skeleton: bool = True
    show_angles: bool = True
    show_rep_count: bool = True
    show_performance_label: bool = True
    show_rom_bar: bool = True
    landmark_color_by_visibility: bool = False


@dataclass(frozen=True)
class FeedbackConfig:
    """
    Configuracion completa de feedback para una sesion.

    Combina la configuracion de audio y visual en un objeto
    unico que se pasa a los modulos de feedback.

    Uso:
        config = FeedbackConfig.default()
        config_sin_audio = FeedbackConfig.silent()
        config_custom = FeedbackConfig(
            audio=AudioConfig(enabled=True, volume=0.5),
            visual=VisualConfig(show_angles=False),
        )
    """

    audio: AudioConfig = field(default_factory=AudioConfig)
    visual: VisualConfig = field(default_factory=VisualConfig)
    postural_config_enabled: bool = False

    @classmethod
    def default(cls) -> FeedbackConfig:
        """
        Configuracion estandar para uso clinico.
        Audio activado con parametros moderados.
        Todos los elementos visuales activos.
        """
        return cls(
            audio=AudioConfig(
                enabled=True,
                volume=0.7,
                yellow_frequency_hz=880,
                red_frequency_hz=440,
                duration_ms=200,
                cooldown_frames=30,
            ),
            visual=VisualConfig(
                show_landmarks=True,
                show_skeleton=True,
                show_angles=True,
                show_rep_count=True,
                show_performance_label=True,
                show_rom_bar=True,
            ),
        )

    @classmethod
    def silent(cls) -> FeedbackConfig:
        """
        Configuracion sin audio.
        Util para entornos donde el sonido es inapropiado
        o cuando el paciente prefiere feedback solo visual.
        """
        return cls(
            audio=AudioConfig(enabled=False),
            visual=VisualConfig(),
        )

    @classmethod
    def minimal(cls) -> FeedbackConfig:
        """
        Configuracion minimalista.
        Solo muestra el label de performance y el contador de reps.
        Util para pacientes que se distraen con demasiada informacion visual.
        """
        return cls(
            audio=AudioConfig(enabled=True, volume=0.5),
            visual=VisualConfig(
                show_landmarks=False,
                show_skeleton=False,
                show_angles=False,
                show_rep_count=True,
                show_performance_label=True,
                show_rom_bar=False,
            ),
        )

    def with_audio_disabled(self) -> FeedbackConfig:
        """
        Devuelve una nueva configuracion identica pero sin audio.
        Util para deshabilitar el audio en tiempo de ejecucion
        sin reconstruir toda la configuracion.
        """
        return FeedbackConfig(
            audio=AudioConfig(
                enabled=False,
                volume=self.audio.volume,
                yellow_frequency_hz=self.audio.yellow_frequency_hz,
                red_frequency_hz=self.audio.red_frequency_hz,
                duration_ms=self.audio.duration_ms,
                cooldown_frames=self.audio.cooldown_frames,
            ),
            visual=self.visual,
            postural_config_enabled=self.postural_config_enabled,
        )