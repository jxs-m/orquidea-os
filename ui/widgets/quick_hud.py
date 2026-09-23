from typing import Any

from PyQt6.QtCore import QPoint, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent.tools.media import MediaController
from daemon.collectors.proc_collector import ProcCollector


class _QuickHUDWorker(QThread):
    result_ready = pyqtSignal(str, object)

    def __init__(self, operation: str, target: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._operation = operation
        self._target = target

    def run(self) -> None:
        if self._operation == "metrics":
            self.result_ready.emit(self._operation, self._target.collect())
        elif self._operation == "metadata":
            self.result_ready.emit(self._operation, self._target.get_metadata())
        elif self._operation == "play_pause":
            self._target.play_pause()


class QuickHUD(QWidget):
    open_main_requested = pyqtSignal()
    prompt_submitted = pyqtSignal(str)

    def __init__(
        self,
        collector: ProcCollector | None = None,
        media_controller: MediaController | None = None,
        main_window: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.collector = collector or ProcCollector()
        self.media_controller = media_controller or MediaController()
        self.main_window = main_window
        self._workers: set[_QuickHUDWorker] = set()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet(
            "QuickHUD { background-color: #0A060E; border: 1px solid #C026D3; "
            "border-radius: 12px; }"
        )
        self.setMinimumWidth(280)

        self.open_main_button = QPushButton("Abrir Orquídea OS")
        self.open_main_button.setObjectName("openMainButton")
        self.open_main_button.clicked.connect(self._open_main)

        self.cpu_bar = self._make_progress_bar("CPU", "cpuUsage")
        self.ram_bar = self._make_progress_bar("RAM", "ramUsage")
        self.disk_bar = self._make_progress_bar("Disco", "diskUsage")

        metrics_layout = QFormLayout()
        metrics_layout.addRow("CPU", self.cpu_bar)
        metrics_layout.addRow("RAM", self.ram_bar)
        metrics_layout.addRow("Disco", self.disk_bar)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Converse com o AGY...")
        self.prompt_input.setObjectName("agyPromptInput")
        self.prompt_button = QPushButton("Enviar")
        self.prompt_button.setObjectName("agyPromptButton")
        self.prompt_button.clicked.connect(self._submit_prompt)
        self.prompt_input.returnPressed.connect(self._submit_prompt)
        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(self.prompt_input, 1)
        prompt_layout.addWidget(self.prompt_button)

        self.track_title = QLabel("Nenhuma faixa")
        self.track_title.setObjectName("quickHudTrackTitle")
        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setAccessibleName("Play/Pause")
        self.play_pause_button.setObjectName("quickHudPlayPause")
        self.play_pause_button.clicked.connect(lambda: self._start_worker("play_pause", self.media_controller))
        media_layout = QHBoxLayout()
        media_layout.addWidget(self.track_title, 1)
        media_layout.addWidget(self.play_pause_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.open_main_button)
        layout.addLayout(metrics_layout)
        layout.addLayout(prompt_layout)
        layout.addLayout(media_layout)

        self._metrics_timer = QTimer(self)
        self._metrics_timer.setInterval(1000)
        self._metrics_timer.timeout.connect(self.refresh_metrics)
        self._metrics_timer.start()
        self.refresh_metrics()

        self._metadata_timer = QTimer(self)
        self._metadata_timer.setInterval(1000)
        self._metadata_timer.timeout.connect(self.refresh_metadata)
        self._metadata_timer.start()
        self.refresh_metadata()

    @staticmethod
    def _make_progress_bar(name: str, object_name: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setObjectName(object_name)
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFormat(f"{name}: %p%")
        return bar

    def _open_main(self) -> None:
        self.open_main_requested.emit()
        if self.main_window is not None:
            self.main_window.showNormal()
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def _submit_prompt(self) -> None:
        text = self.prompt_input.text().strip()
        if text:
            self.prompt_submitted.emit(text)
            self.prompt_input.clear()

    def toggle_at(self, point: QPoint) -> None:
        if self.isVisible():
            self.hide()
            return
        self.move(point - QPoint(self.width() // 2, self.height() // 2))
        self.show()
        self.raise_()
        self.activateWindow()

    def refresh_metrics(self) -> None:
        if not self._is_running("metrics"):
            self._start_worker("metrics", self.collector)

    def refresh_metadata(self) -> None:
        if not self._is_running("metadata"):
            self._start_worker("metadata", self.media_controller)

    def _is_running(self, operation: str) -> bool:
        return any(
            worker.isRunning() and worker._operation == operation
            for worker in self._workers
        )

    def _start_worker(self, operation: str, target: Any) -> None:
        worker = _QuickHUDWorker(operation, target, self)
        worker.result_ready.connect(self._apply_result)
        worker.finished.connect(self._worker_finished)
        self._workers.add(worker)
        worker.start()

    def _worker_finished(self) -> None:
        worker = self.sender()
        if isinstance(worker, _QuickHUDWorker):
            self._workers.discard(worker)
            worker.deleteLater()

    def _apply_result(self, operation: str, result: Any) -> None:
        if operation == "metrics":
            self._apply_metrics(result)
        elif operation == "metadata" and isinstance(result, dict):
            title = str(result.get("title") or "Nenhuma faixa")
            status = str(result.get("status") or "Offline")
            self.track_title.setText(title if title != "Nenhuma faixa" else status)
            self.play_pause_button.setText("⏸" if status == "Playing" else "▶")

    def _apply_metrics(self, metrics: Any) -> None:
        if not isinstance(metrics, dict):
            return
        for key, bar in (
            ("cpu", self.cpu_bar),
            ("memory", self.ram_bar),
            ("disk", self.disk_bar),
        ):
            category = metrics.get(key)
            if isinstance(category, dict) and "usage_percent" in category:
                bar.setValue(round(category["usage_percent"]))
