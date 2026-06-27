"""
infrastructure/biomechanics/pipeline/countdown.py

Ejecuta la cuenta regresiva antes de iniciar un ejercicio.

Muestra 5-4-3-2-1 con feedback visual y auditivo.
Sigue mostrando el video en vivo durante la cuenta para
que el paciente pueda posicionarse correctamente.

Es un proceso bloqueante: run() retorna cuando la cuenta termina
o cuando se cancela.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import cv2

from infrastructure.biomechanics.capture.dual_capture import DualCapture
from infrastructure.biomechanics.feedback.audio_alert import AudioAlert
from infrastructure.biomechanics.feedback.visual_renderer import VisualRenderer
from shared.constants import COUNTDOWN_SECONDS

logger = logging.getLogger(__name__)

# Tiempo de espera entre ticks de la cuenta regresiva en segundos.
# Exactamente 1 segundo por numero.
_TICK_INTERVAL_SECONDS: float = 1.0

# Tecla para cancelar la cuenta regresiva durante el desarrollo.
# ord('q') = 113
_CANCEL_KEY: int = ord("q")


class CountdownCancelled(Exception):
    """
    Lanzada cuando el usuario cancela la cuenta regresiva.
    Permite que session_runner.py distinga entre cuenta completada
    y cuenta cancelada sin usar valores de retorno booleanos.
    """


class Countdown:
    """
    Ejecuta la cuenta regresiva antes de iniciar un ejercicio.

    Muestra el video en vivo en una ventana de OpenCV durante
    la cuenta para que el paciente pueda ver su posicion.

    Uso:
        countdown = Countdown(
            capture=dual_capture,
            audio=audio_alert,
            renderer=visual_renderer,
        )
        try:
            countdown.run(exercise_name='Flexion de rodilla')
        except CountdownCancelled:
            session_runner.abort('Cuenta regresiva cancelada')
    """

    def __init__(
        self,
        capture: DualCapture,
        audio: AudioAlert,
        renderer: VisualRenderer,
        seconds: int = COUNTDOWN_SECONDS,
        window_name: str = "FlexIA",
    ) -> None:
        """
        Args:
            capture: sistema de captura dual ya abierto.
            audio: sistema de audio ya inicializado.
            renderer: renderizador visual.
            seconds: duracion de la cuenta regresiva.
            window_name: nombre de la ventana de OpenCV.
        """
        self._capture = capture
        self._audio = audio
        self._renderer = renderer
        self._seconds = seconds
        self._window_name = window_name

    def run(
        self,
        exercise_name: str,
        on_tick: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        Ejecuta la cuenta regresiva completa.

        Muestra el video en vivo con el numero de segundos
        restantes superpuesto. Emite un beep en cada tick.

        Args:
            exercise_name: nombre del ejercicio que va a comenzar.
                           Se muestra en pantalla durante la cuenta.
            on_tick: callback opcional llamado en cada tick con el
                     numero de segundos restantes. Util para que
                     Streamlit pueda actualizar su UI en paralelo.

        Raises:
            CountdownCancelled: si el usuario presiona 'q' durante
                                la cuenta.
        """
        logger.info(
            "Iniciando cuenta regresiva de %d segundos para '%s'.",
            self._seconds,
            exercise_name,
        )

        for remaining in range(self._seconds, 0, -1):
            tick_start = time.monotonic()

            self._audio.emit_countdown()

            if on_tick is not None:
                on_tick(remaining)

            cancelled = self._render_tick_for_duration(
                remaining=remaining,
                duration=_TICK_INTERVAL_SECONDS,
                tick_start=tick_start,
            )

            if cancelled:
                raise CountdownCancelled(
                    f"Cuenta regresiva cancelada en {remaining} segundos."
                )

        logger.info("Cuenta regresiva completada. Iniciando '%s'.", exercise_name)

    def _render_tick_for_duration(
        self,
        remaining: int,
        duration: float,
        tick_start: float,
    ) -> bool:
        """
        Muestra el frame de cuenta regresiva durante el tiempo
        indicado, actualizando el video en vivo frame a frame.

        Returns:
            True si el usuario cancelo durante este tick.
            False si el tick completo sin cancelacion.
        """
        while True:
            elapsed = time.monotonic() - tick_start
            if elapsed >= duration:
                break

            pair = self._capture.read_frames()

            if pair.front is not None:
                annotated = self._renderer.render_countdown(
                    frame=pair.front,
                    seconds_remaining=remaining,
                )
                cv2.imshow(self._window_name, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == _CANCEL_KEY:
                logger.info("Cuenta regresiva cancelada por el usuario.")
                return True

        return False