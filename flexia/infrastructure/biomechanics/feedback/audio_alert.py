"""
infrastructure/biomechanics/feedback/audio_alert.py

Reproduce alertas sonoras durante la ejecucion de ejercicios.

Orden de busqueda de archivos de audio:
    1. sounds/custom/   -> archivo personalizado de la clinica
    2. sounds/default/  -> archivo default del sistema
    3. Tono sintetizado -> fallback matematico sin archivos

El sistema nunca falla por causa del audio.
Si la reproduccion falla, se loguea y la sesion continua.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from domain.value_objects.performance_label import PerformanceLabel
from infrastructure.biomechanics.feedback.feedback_config import FeedbackConfig

logger = logging.getLogger(__name__)

# Ruta base de la carpeta sounds relativa a este archivo
_SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"
_CUSTOM_DIR = _SOUNDS_DIR / "custom"
_DEFAULT_DIR = _SOUNDS_DIR / "default"

# Nombres de archivo por tipo de alerta
_SOUND_FILES: dict[str, str] = {
    "yellow": "alert_yellow.wav",
    "red": "alert_red.wav",
    "countdown": "countdown_beep.wav",
}


class AudioAlert:
    """
    Reproductor de alertas sonoras para feedback clinico en tiempo real.

    Gestiona el cooldown entre alertas para evitar sonidos repetitivos
    que distraigan al paciente durante el ejercicio.

    Uso:
        alert = AudioAlert(config)
        alert.initialize()

        # En cada frame donde hay resultado de performance:
        alert.emit_performance(label, frame_number)

        # En cada tick de cuenta regresiva:
        alert.emit_countdown()

        alert.shutdown()
    """

    def __init__(self, config: FeedbackConfig) -> None:
        self._config = config
        self._initialized = False
        self._pygame_available = False
        self._last_alert_frame: dict[str, int] = {
            "yellow": -999,
            "red": -999,
        }
        self._sound_cache: dict[str, object] = {}

    def initialize(self) -> None:
        """
        Inicializa el sistema de audio.

        Si pygame no esta disponible o el dispositivo de audio falla,
        marca el sistema como no disponible sin lanzar excepcion.
        La sesion puede continuar sin audio.
        """
        if not self._config.audio.enabled:
            logger.info("Audio desactivado en configuracion. No se inicializa pygame.")
            self._initialized = True
            return

        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._pygame_available = True
            self._preload_sounds()
            logger.info("Sistema de audio inicializado correctamente.")
        except Exception as e:
            logger.warning(
                "No se pudo inicializar el sistema de audio. "
                "La sesion continuara sin alertas sonoras. Error: %s",
                str(e),
            )

        self._initialized = True

    def emit_performance(
        self,
        label: PerformanceLabel,
        current_frame: int,
    ) -> None:
        """
        Emite una alerta sonora segun el label de performance.

        No emite nada si:
            - El audio esta desactivado en la configuracion.
            - El label es verde (no requiere alerta).
            - El cooldown desde la ultima alerta del mismo tipo
              no ha expirado.

        Args:
            label: clasificacion del desempeno del frame actual.
            current_frame: numero del frame actual para calcular cooldown.
        """
        if not self._initialized:
            logger.warning("AudioAlert.emit_performance() llamado antes de initialize().")
            return

        if not self._config.audio.enabled or not self._pygame_available:
            return

        if label == PerformanceLabel.GREEN:
            return

        key = label.value
        frames_since_last = current_frame - self._last_alert_frame.get(key, -999)

        if frames_since_last < self._config.audio.cooldown_frames:
            return

        self._play(key)
        self._last_alert_frame[key] = current_frame

    def emit_countdown(self) -> None:
        """
        Emite el beep de la cuenta regresiva.
        Se llama una vez por segundo durante los 5 segundos previos
        al inicio del ejercicio.
        """
        if not self._initialized:
            return

        if not self._config.audio.enabled or not self._pygame_available:
            return

        self._play("countdown")

    def shutdown(self) -> None:
        """
        Libera los recursos de audio.
        Debe llamarse cuando la sesion termina.
        """
        if self._pygame_available:
            try:
                import pygame
                pygame.mixer.quit()
                logger.info("Sistema de audio liberado.")
            except Exception as e:
                logger.warning("Error al liberar audio: %s", str(e))

        self._sound_cache.clear()
        self._initialized = False
        self._pygame_available = False

    def _preload_sounds(self) -> None:
        """
        Precarga todos los archivos de audio en memoria al iniciar.
        Evita latencia en la primera reproduccion durante el ejercicio.
        """
        import pygame

        for key, filename in _SOUND_FILES.items():
            path = self._resolve_sound_path(filename)
            if path is None:
                logger.warning(
                    "Archivo de audio no encontrado para '%s': %s. "
                    "Esta alerta no emitira sonido.",
                    key,
                    filename,
                )
                continue
            try:
                self._sound_cache[key] = pygame.mixer.Sound(str(path))
                self._sound_cache[key].set_volume(self._config.audio.volume)
                logger.debug("Audio precargado: %s -> %s", key, path)
            except Exception as e:
                logger.warning(
                    "No se pudo cargar el archivo de audio '%s': %s",
                    path,
                    str(e),
                )

    def _play(self, key: str) -> None:
        """
        Reproduce el sonido correspondiente a la clave indicada.
        Si el sonido no esta en cache, no hace nada.

        Args:
            key: clave del sonido ('yellow', 'red', 'countdown').
        """
        sound = self._sound_cache.get(key)
        if sound is None:
            return

        try:
            sound.play()
        except Exception as e:
            logger.warning("Error al reproducir audio '%s': %s", key, str(e))

    def _resolve_sound_path(self, filename: str) -> Optional[Path]:
        """
        Resuelve la ruta del archivo de audio siguiendo el orden de prioridad:
            1. sounds/custom/  -> personalizacion de la clinica
            2. sounds/default/ -> sonidos default del sistema

        Args:
            filename: nombre del archivo de audio (ej: 'alert_yellow.wav').

        Returns:
            Path al archivo encontrado, o None si no existe en ninguna ubicacion.
        """
        custom_path = _CUSTOM_DIR / filename
        if custom_path.is_file():
            logger.debug("Usando audio personalizado: %s", custom_path)
            return custom_path

        default_path = _DEFAULT_DIR / filename
        if default_path.is_file():
            logger.debug("Usando audio default: %s", default_path)
            return default_path

        return None