from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtWidgets import QWidget


def fade_in(widget: QWidget, duration: int = 300) -> QPropertyAnimation:
    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def slide_in(
    widget: QWidget,
    start_x: int,
    end_x: int,
    duration: int = 350,
) -> QPropertyAnimation:
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(QPoint(start_x, widget.y()))
    anim.setEndValue(QPoint(end_x, widget.y()))
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


class FadeAnimator:
    def __init__(self, widget: QWidget, duration: int = 250) -> None:
        self._widget = widget
        self._duration = duration
        self._anim: QPropertyAnimation | None = None

    def fade_in(self) -> QPropertyAnimation:
        return self._animate(1.0)

    def fade_out(self) -> QPropertyAnimation:
        return self._animate(0.0)

    def _animate(self, end_value: float) -> QPropertyAnimation:
        if self._anim:
            self._anim.stop()

        self._anim = QPropertyAnimation(self._widget, b"windowOpacity")
        self._anim.setDuration(self._duration)
        self._anim.setStartValue(1.0 - end_value)
        self._anim.setEndValue(end_value)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        return self._anim
