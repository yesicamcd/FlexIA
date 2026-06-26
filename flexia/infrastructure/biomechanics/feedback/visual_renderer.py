"""
infrastructure/biomechanics/feedback/visual_renderer.py

Dibuja feedback visual sobre el frame de video en tiempo real.
Es el unico modulo que modifica pixeles del frame.

Recibe datos calculados y los presenta visualmente.
No toma decisiones clinicas — solo presenta lo que recibe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from domain.value_objects.performance_label import PerformanceLabel
from domain.value_objects.rom_measurement import RomMeasurement
from infrastructure.biomechanics.analysis.pose_estimator import PoseLandmarks
from infrastructure.biomechanics.feedback.feedback_config import FeedbackConfig

logger = logging.getLogger(__name__)

# Colores en formato BGR (OpenCV)
_COLOR_GREEN  = (34, 197, 94)
_COLOR_YELLOW = (0, 200, 255)
_COLOR_RED    = (60, 60, 220)
_COLOR_WHITE  = (255, 255, 255)
_COLOR_BLACK  = (0, 0, 0)
_COLOR_GRAY   = (180, 180, 180)
_COLOR_TEAL   = (180, 130, 70)

# Conexiones del esqueleto — pares de indices de landmarks
_SKELETON_CONNECTIONS: list[tuple[int, int]] = [
    (11, 12),  # hombros
    (11, 13),  # hombro izq -> codo izq
    (13, 15),  # codo izq -> muneca izq
    (12, 14),  # hombro der -> codo der
    (14, 16),  # codo der -> muneca der
    (11, 23),  # hombro izq -> cadera izq
    (12, 24),  # hombro der -> cadera der
    (23, 24),  # caderas
    (23, 25),  # cadera izq -> rodilla izq
    (25, 27),  # rodilla izq -> tobillo izq
    (24, 26),  # cadera der -> rodilla der
    (26, 28),  # rodilla der -> tobillo der
    (27, 29),  # tobillo izq -> talon izq
    (28, 30),  # tobillo der -> talon der
]


@dataclass
class RenderData:
    """
    Datos necesarios para renderizar un frame.

    Agrupa toda la informacion calculada por frame_processor
    en un objeto unico para pasarla al renderer.

    Atributos:
        landmarks: landmarks de pose detectados en el frame.
        rom: medicion de ROM del frame actual. None si no hay deteccion.
        rep_count: repeticiones completadas hasta el momento.
        valid_rep_count: repeticiones validas completadas.
        reps_expected: repeticiones esperadas para el ejercicio.
        performance: label de performance del frame. None si no hay ROM.
        exercise_name: nombre del ejercicio para mostrar en pantalla.
        joint_name: nombre de la articulacion evaluada.
    """

    landmarks: Optional[PoseLandmarks]
    rom: Optional[RomMeasurement]
    rep_count: int
    valid_rep_count: int
    reps_expected: int
    performance: Optional[PerformanceLabel]
    exercise_name: str
    joint_name: str


class VisualRenderer:
    """
    Renderiza feedback visual sobre frames de video en tiempo real.

    Cada llamada a render() devuelve una copia del frame
    con los elementos visuales dibujados. El frame original
    no se modifica.

    Uso:
        renderer = VisualRenderer(config)
        annotated_frame = renderer.render(frame, render_data)
        cv2.imshow('FlexIA', annotated_frame)
    """

    def __init__(self, config: FeedbackConfig) -> None:
        self._config = config

    def render(
        self,
        frame: np.ndarray,
        data: RenderData,
    ) -> np.ndarray:
        """
        Dibuja todos los elementos visuales activos sobre el frame.

        Args:
            frame: frame original en formato BGR (H, W, 3).
            data: datos calculados para este frame.

        Returns:
            Frame anotado con los elementos visuales. El frame
            original no se modifica.
        """
        output = frame.copy()
        visual = self._config.visual

        if data.landmarks is not None:
            if visual.show_skeleton:
                self._draw_skeleton(output, data.landmarks)
            if visual.show_landmarks:
                self._draw_landmarks(output, data.landmarks)

        if visual.show_performance_label and data.performance is not None:
            self._draw_performance_label(output, data.performance)

        if visual.show_angles and data.rom is not None:
            self._draw_angle(output, data.rom, data.landmarks)

        if visual.show_rom_bar and data.rom is not None:
            self._draw_rom_bar(output, data.rom)

        if visual.show_rep_count:
            self._draw_rep_counter(
                output,
                data.rep_count,
                data.valid_rep_count,
                data.reps_expected,
            )

        self._draw_exercise_name(output, data.exercise_name)

        return output

    def render_countdown(
        self,
        frame: np.ndarray,
        seconds_remaining: int,
    ) -> np.ndarray:
        """
        Renderiza la cuenta regresiva sobre el frame.
        Muestra el numero centrado con fondo semitransparente.

        Args:
            frame: frame de camara en formato BGR.
            seconds_remaining: segundos restantes (5 a 1).

        Returns:
            Frame con la cuenta regresiva renderizada.
        """
        output = frame.copy()
        h, w = output.shape[:2]

        overlay = output.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), _COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.4, output, 0.6, 0, output)

        text = str(seconds_remaining)
        font = cv2.FONT_HERSHEY_DUPLEX
        scale = 8.0
        thickness = 12

        (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
        x = (w - text_w) // 2
        y = (h + text_h) // 2

        cv2.putText(output, text, (x, y), font, scale, _COLOR_WHITE, thickness)

        ready_text = "Preparese..."
        cv2.putText(
            output, ready_text,
            (w // 2 - 120, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0, _COLOR_GRAY, 2,
        )

        return output

    def render_validation_status(
        self,
        frame: np.ndarray,
        checks: dict[str, bool],
    ) -> np.ndarray:
        """
        Renderiza el estado de las validaciones pre-sesion.
        Muestra cada check con un indicador verde o rojo.

        Args:
            frame: frame de camara en formato BGR.
            checks: diccionario con nombre del check y su resultado.
                    Ejemplo: {'Camara OK': True, 'Cuerpo visible': False}

        Returns:
            Frame con el estado de validaciones renderizado.
        """
        output = frame.copy()
        h, w = output.shape[:2]

        overlay = output.copy()
        cv2.rectangle(overlay, (20, 20), (360, 40 + len(checks) * 35), _COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.6, output, 0.4, 0, output)

        cv2.putText(
            output, "Validando sesion...",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, _COLOR_WHITE, 2,
        )

        for i, (check_name, passed) in enumerate(checks.items()):
            y = 85 + i * 35
            color = _COLOR_GREEN if passed else _COLOR_RED
            symbol = "[OK]" if passed else "[--]"
            cv2.putText(
                output,
                f"{symbol} {check_name}",
                (35, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65, color, 2,
            )

        return output

    def _draw_skeleton(
        self,
        frame: np.ndarray,
        landmarks: PoseLandmarks,
    ) -> None:
        """
        Dibuja las conexiones del esqueleto entre landmarks.
        Solo dibuja conexiones donde ambos landmarks son visibles.
        """
        h, w = frame.shape[:2]

        for start_idx, end_idx in _SKELETON_CONNECTIONS:
            if not (
                landmarks.is_visible(start_idx, 0.4)
                and landmarks.is_visible(end_idx, 0.4)
            ):
                continue

            start = landmarks.get(start_idx)
            end = landmarks.get(end_idx)

            pt1 = (int(start.x * w), int(start.y * h))
            pt2 = (int(end.x * w), int(end.y * h))

            cv2.line(frame, pt1, pt2, _COLOR_TEAL, 2, cv2.LINE_AA)

    def _draw_landmarks(
        self,
        frame: np.ndarray,
        landmarks: PoseLandmarks,
    ) -> None:
        """
        Dibuja los puntos de pose sobre el cuerpo.
        El color refleja la visibilidad del landmark si esta
        activado landmark_color_by_visibility en la config.
        """
        h, w = frame.shape[:2]
        color_by_visibility = self._config.visual.landmark_color_by_visibility

        for i in range(len(landmarks.landmarks)):
            lm = landmarks.get(i)
            if lm.visibility < 0.3:
                continue

            x = int(lm.x * w)
            y = int(lm.y * h)

            if color_by_visibility:
                intensity = int(lm.visibility * 255)
                color = (0, intensity, 255 - intensity)
            else:
                color = _COLOR_WHITE

            cv2.circle(frame, (x, y), 4, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 4, _COLOR_BLACK, 1, cv2.LINE_AA)

    def _draw_performance_label(
        self,
        frame: np.ndarray,
        performance: PerformanceLabel,
    ) -> None:
        """
        Dibuja el label de performance en la esquina superior derecha.
        Verde, amarillo o rojo con fondo semitransparente.
        """
        h, w = frame.shape[:2]

        color_map = {
            PerformanceLabel.GREEN:  _COLOR_GREEN,
            PerformanceLabel.YELLOW: _COLOR_YELLOW,
            PerformanceLabel.RED:    _COLOR_RED,
        }
        label_map = {
            PerformanceLabel.GREEN:  "CORRECTO",
            PerformanceLabel.YELLOW: "CORRECCION LEVE",
            PerformanceLabel.RED:    "ERROR",
        }

        color = color_map[performance]
        text = label_map[performance]

        box_x1, box_y1 = w - 280, 15
        box_x2, box_y2 = w - 15, 55

        overlay = frame.copy()
        cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), color, -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        cv2.putText(
            frame, text,
            (box_x1 + 10, box_y1 + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65, _COLOR_WHITE, 2, cv2.LINE_AA,
        )

    def _draw_angle(
        self,
        frame: np.ndarray,
        rom: RomMeasurement,
        landmarks: Optional[PoseLandmarks],
    ) -> None:
        """
        Dibuja el angulo articular actual cerca de la articulacion.
        Si no hay landmarks disponibles, lo dibuja en posicion fija.
        """
        h, w = frame.shape[:2]
        text = f"{rom.achieved_degrees:.1f} / {rom.expected_degrees:.1f} grados"

        cv2.putText(
            frame, text,
            (20, h - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, _COLOR_WHITE, 2, cv2.LINE_AA,
        )

    def _draw_rom_bar(
        self,
        frame: np.ndarray,
        rom: RomMeasurement,
    ) -> None:
        """
        Dibuja una barra horizontal de progreso del ROM.
        Muestra visualmente cuanto del objetivo alcanzo el paciente.
        La barra se colorea segun el porcentaje alcanzado.
        """
        h, w = frame.shape[:2]

        bar_x, bar_y = 20, h - 70
        bar_w, bar_h = 300, 18

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                      _COLOR_GRAY, -1)

        fill_ratio = min(rom.percentage / 100.0, 1.0)
        fill_w = int(bar_w * fill_ratio)

        if rom.percentage >= 85:
            bar_color = _COLOR_GREEN
        elif rom.percentage >= 60:
            bar_color = _COLOR_YELLOW
        else:
            bar_color = _COLOR_RED

        if fill_w > 0:
            cv2.rectangle(
                frame,
                (bar_x, bar_y),
                (bar_x + fill_w, bar_y + bar_h),
                bar_color, -1,
            )

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                      _COLOR_WHITE, 1)

        cv2.putText(
            frame, f"ROM {rom.percentage:.0f}%",
            (bar_x + bar_w + 10, bar_y + 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, _COLOR_WHITE, 2, cv2.LINE_AA,
        )

    def _draw_rep_counter(
        self,
        frame: np.ndarray,
        rep_count: int,
        valid_rep_count: int,
        reps_expected: int,
    ) -> None:
        """
        Dibuja el contador de repeticiones en la esquina superior izquierda.
        Muestra repeticiones validas sobre el total esperado.
        """
        h, w = frame.shape[:2]

        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 15), (200, 65), _COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        cv2.putText(
            frame, "REPS",
            (25, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, _COLOR_GRAY, 1, cv2.LINE_AA,
        )

        rep_text = f"{valid_rep_count} / {reps_expected}"
        cv2.putText(
            frame, rep_text,
            (80, 55),
            cv2.FONT_HERSHEY_DUPLEX,
            1.1, _COLOR_WHITE, 2, cv2.LINE_AA,
        )

    def _draw_exercise_name(
        self,
        frame: np.ndarray,
        exercise_name: str,
    ) -> None:
        """
        Dibuja el nombre del ejercicio en la parte superior central.
        """
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.7
        thickness = 2

        (text_w, _), _ = cv2.getTextSize(exercise_name, font, scale, thickness)
        x = (w - text_w) // 2

        cv2.putText(
            frame, exercise_name,
            (x, 35),
            font, scale, _COLOR_WHITE, thickness, cv2.LINE_AA,
        )