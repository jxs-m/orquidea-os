from math import pi, sin

from PyQt6.QtCore import QElapsedTimer, QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QLabel, QWidget

from ui.theme import ACCENT_HOVER, ACCENT_PRIMARY, BG_CARD, TEXT_PRIMARY


class OrchidOverlay(QWidget):
    signal_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(72, 72)
        self.setMouseTracking(True)

        self._rest_position = QPoint(100, 100)
        self._press_position: QPoint | None = None
        self._dragging = False
        self._elapsed = QElapsedTimer()
        self._elapsed.start()

        self._float_timer = QTimer(self)
        self._float_timer.setInterval(16)
        self._float_timer.timeout.connect(self._update_float_position)
        self._float_timer.start()

        self._bubble = QLabel(self)
        self._bubble.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._bubble.setObjectName("orchidSpeechBubble")
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bubble.setWordWrap(True)
        self._bubble.setStyleSheet(
            f"QLabel#orchidSpeechBubble {{ background-color: rgba(25, 12, 34, 225); "
            f"color: {TEXT_PRIMARY}; border: 1px solid {ACCENT_PRIMARY}; "
            "border-radius: 10px; padding: 7px 10px; }"
        )
        self._bubble.hide()
        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._bubble.hide)

        self.show()

    def show_bubble(self, text: str, duration_ms: int = 3000) -> None:
        self._bubble.setText(text)
        self._bubble.adjustSize()
        width = min(max(self._bubble.sizeHint().width(), 110), 260)
        self._bubble.setFixedWidth(width)
        self._bubble.adjustSize()
        self._bubble.move((self.width() - self._bubble.width()) // 2, -self._bubble.height() - 8)
        self._bubble.show()
        self._bubble.raise_()
        self._bubble_timer.start(max(0, duration_ms))

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BG_CARD + "D9")))
        painter.drawEllipse(QRectF(3, 3, 66, 66))

        gradient = QLinearGradient(20, 15, 54, 57)
        gradient.setColorAt(0.0, QColor(ACCENT_HOVER))
        gradient.setColorAt(1.0, QColor(ACCENT_PRIMARY))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(ACCENT_HOVER + "AA"), 1.2))

        petals = QPainterPath()
        petals.moveTo(36, 37)
        petals.cubicTo(25, 34, 24, 23, 34, 17)
        petals.cubicTo(40, 23, 41, 30, 36, 37)
        petals.moveTo(37, 36)
        petals.cubicTo(39, 25, 50, 23, 56, 33)
        petals.cubicTo(50, 39, 43, 40, 37, 36)
        petals.moveTo(37, 37)
        petals.cubicTo(48, 39, 50, 50, 40, 56)
        petals.cubicTo(34, 50, 33, 43, 37, 37)
        petals.moveTo(35, 37)
        petals.cubicTo(33, 48, 22, 50, 16, 40)
        petals.cubicTo(22, 34, 29, 33, 35, 37)
        petals.moveTo(36, 35)
        petals.cubicTo(27, 29, 30, 17, 40, 15)
        petals.cubicTo(45, 22, 43, 29, 36, 35)
        painter.drawPath(petals)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT_HOVER))
        painter.drawEllipse(QPointF(36, 36), 4.5, 4.5)
        painter.end()

    def mousePressEvent(self, event: object) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.globalPosition().toPoint()
            self._dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: object) -> None:
        if self._press_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            delta = current - self._press_position
            if not self._dragging and delta.manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
            if self._dragging:
                self._rest_position += delta
                self._press_position = current
                self.move(self._rest_position + QPoint(0, self._float_offset()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: object) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press_position is not None:
            if not self._dragging:
                self.signal_clicked.emit()
            self._press_position = None
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _float_offset(self) -> int:
        elapsed_seconds = self._elapsed.elapsed() / 1000
        return round(4 * sin(2 * pi * elapsed_seconds / 2.4))

    def _update_float_position(self) -> None:
        if not self._dragging:
            self.move(self._rest_position + QPoint(0, self._float_offset()))

