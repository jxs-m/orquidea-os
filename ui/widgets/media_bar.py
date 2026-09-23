from typing import Any

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from agent.tools.media import MediaController, MediaMetadata


class _MediaWorker(QThread):
    metadata_ready = pyqtSignal(object)

    def __init__(self, controller: MediaController, operation: str, value: int | None = None) -> None:
        super().__init__()
        self._controller = controller
        self._operation = operation
        self._value = value

    def run(self) -> None:
        if self._operation == "metadata":
            result = self._controller.get_metadata()
            self.metadata_ready.emit(result)
        elif self._operation == "volume":
            self._controller.set_volume(self._value if self._value is not None else 0)
        elif self._operation == "play_pause":
            self._controller.play_pause()
        elif self._operation == "previous":
            self._controller.previous()
        elif self._operation == "next":
            self._controller.next()


class _ElidingLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text)

    def setText(self, text: Any) -> None:
        text_str = str(text) if text is not None else ""
        self._full_text = text_str
        self.setToolTip(text_str)
        self._update_elided_text()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self) -> None:
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.contentsRect().width()))


class MediaBar(QWidget):
    def __init__(self, controller: MediaController | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller or MediaController()
        self._workers: set[_MediaWorker] = set()
        self._metadata: MediaMetadata | None = None

        self.thumbnail_label = QLabel("♪")
        self.thumbnail_label.setObjectName("mediaThumbnail")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setFixedSize(48, 48)

        self.title_label = _ElidingLabel("Nenhuma faixa")
        self.title_label.setObjectName("mediaTitle")
        self.artist_label = _ElidingLabel("Offline")
        self.artist_label.setObjectName("mediaArtist")

        self.previous_button = QPushButton("⏮")
        self.previous_button.setAccessibleName("Previous")
        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setAccessibleName("Play/Pause")
        self.next_button = QPushButton("⏭")
        self.next_button.setAccessibleName("Next")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setAccessibleName("Volume")

        metadata_layout = QVBoxLayout()
        metadata_layout.setContentsMargins(0, 0, 0, 0)
        metadata_layout.setSpacing(2)
        metadata_layout.addWidget(self.title_label)
        metadata_layout.addWidget(self.artist_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        layout.addWidget(self.thumbnail_label)
        layout.addLayout(metadata_layout, 1)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.play_pause_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.volume_slider)

        self.previous_button.clicked.connect(lambda: self._start_worker("previous"))
        self.play_pause_button.clicked.connect(lambda: self._start_worker("play_pause"))
        self.next_button.clicked.connect(lambda: self._start_worker("next"))
        self.volume_slider.valueChanged.connect(self._volume_changed)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh_metadata)
        self.refresh_timer.start()
        self.refresh_metadata()

    def refresh_metadata(self) -> None:
        if not any(worker.isRunning() and getattr(worker, "_operation", None) == "metadata" for worker in self._workers):
            self._start_worker("metadata")

    def _volume_changed(self, value: int) -> None:
        self._start_worker("volume", value)

    def _start_worker(self, operation: str, value: int | None = None) -> None:
        worker = _MediaWorker(self.controller, operation, value)
        worker.metadata_ready.connect(self._apply_metadata)
        worker.finished.connect(self._worker_finished)
        self._workers.add(worker)
        worker.start()

    def _worker_finished(self) -> None:
        worker = self.sender()
        if isinstance(worker, _MediaWorker):
            self._discard_worker(worker)

    def _discard_worker(self, worker: _MediaWorker) -> None:
        self._workers.discard(worker)
        worker.deleteLater()

    def _apply_metadata(self, metadata: Any) -> None:
        if not isinstance(metadata, dict):
            return
        self._metadata = metadata
        title = str(metadata.get("title") or "")
        artist = str(metadata.get("artist") or "")
        album = str(metadata.get("album") or "")
        status = str(metadata.get("status") or "Offline")
        self.title_label.setText(title or "Nenhuma faixa")
        self.artist_label.setText(artist or status)
        self.play_pause_button.setText("⏸" if status == "Playing" else "▶")
        self.thumbnail_label.setText("♪")
        self.thumbnail_label.setToolTip(album)
