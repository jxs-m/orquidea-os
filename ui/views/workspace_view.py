from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from agent.tools.workspaces import WorkspaceManager


class _WorkspaceWorker(QThread):
    result = pyqtSignal(int, str, object)
    failed = pyqtSignal(int, str)

    def __init__(self, manager: WorkspaceManager, request_id: int, action: str, *args: object) -> None:
        super().__init__()
        self.manager = manager
        self.request_id = request_id
        self.action = action
        self.args = args

    def run(self) -> None:
        try:
            value = getattr(self.manager, self.action)(*self.args)
        except Exception as exc:
            self.failed.emit(self.request_id, str(exc))
        else:
            self.result.emit(self.request_id, self.action, value)


class WorkspaceView(QWidget):
    workers_idle = pyqtSignal()

    def __init__(self, manager: WorkspaceManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._groups: list[dict[str, Any]] = []
        self._workers: set[_WorkspaceWorker] = set()
        self._request_id = 0
        self._list_id = 0
        self._inspect_id = 0
        self._preferred_group: str | None = None
        self._pending_names: dict[int, str] = {}
        self._closing = False

        self.title_label = QLabel("Selecione um grupo")
        self.title_label.setObjectName("card")
        self.group_selector = QComboBox()
        self.group_selector.setAccessibleName("Grupo de pastas")
        self.new_group_button = QPushButton("Novo Grupo")
        self.new_group_button.clicked.connect(self._create_group)
        self.group_selector.currentTextChanged.connect(self._show_group)

        header = QHBoxLayout()
        header.addWidget(self.title_label, 1)
        header.addWidget(self.group_selector)
        header.addWidget(self.new_group_button)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.splitter, 1)
        self.refresh_groups()

    def _start_worker(self, action: str, *args: object) -> int:
        self._request_id += 1
        worker = _WorkspaceWorker(self.manager, self._request_id, action, *args)
        self._workers.add(worker)
        worker.result.connect(self._on_result)
        worker.failed.connect(self._on_error)
        worker.finished.connect(lambda worker=worker: self._worker_finished(worker))
        worker.start()
        return self._request_id

    def _worker_finished(self, worker: _WorkspaceWorker) -> None:
        self._workers.discard(worker)
        worker.deleteLater()
        if self._closing and not self._workers:
            self.workers_idle.emit()

    def refresh_groups(self) -> None:
        if self._closing:
            return
        self._list_id = self._start_worker("list_groups")

    def _on_result(self, request_id: int, action: str, value: object) -> None:
        if self._closing:
            return
        if action == "create_group":
            name = self._pending_names.pop(request_id, None)
            if name is not None:
                self._preferred_group = name
                self.refresh_groups()
        elif action == "list_groups":
            if request_id != self._list_id:
                return
            self._groups = value
            selected_name = self._preferred_group or self.group_selector.currentText()
            self._preferred_group = None
            self.group_selector.blockSignals(True)
            self.group_selector.clear()
            self.group_selector.addItems([str(group["nome"]) for group in self._groups])
            selected_index = self.group_selector.findText(selected_name)
            if selected_index >= 0:
                self.group_selector.setCurrentIndex(selected_index)
            self.group_selector.blockSignals(False)
            if self._groups:
                self._show_group(self.group_selector.currentText())
            else:
                self.title_label.setText("Nenhum grupo")
                self._clear_columns()
        elif action == "inspect_group_files" and request_id == self._inspect_id:
            name = self.group_selector.currentText()
            group = next((item for item in self._groups if str(item["nome"]) == name), None)
            if group is None:
                return
            self._clear_columns()
            file_data = value if isinstance(value, dict) else {}
            for directory in group["caminhos"]:
                path = str(directory)
                self.splitter.addWidget(self._make_folder_column(path, file_data.get(path, [])))

    def _on_error(self, request_id: int, message: str) -> None:
        self._pending_names.pop(request_id, None)
        if not self._closing and request_id in (self._list_id, self._inspect_id, self._request_id):
            self.title_label.setText(f"Erro: {message}")

    def begin_close(self) -> bool:
        self._closing = True
        return not self._workers

    def closeEvent(self, event: Any) -> None:
        if self.begin_close():
            super().closeEvent(event)
        else:
            event.ignore()
            self.workers_idle.connect(self.close, Qt.ConnectionType.SingleShotConnection)

    def _create_group(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, accepted = QInputDialog.getText(self, "Novo Grupo", "Nome do grupo:")
        if not accepted or not name.strip():
            return
        paths, accepted = QInputDialog.getText(
            self,
            "Pastas do grupo",
            "Caminhos das pastas (separados por ponto e vírgula):",
        )
        if not accepted:
            return
        directories = [path.strip() for path in paths.split(";") if path.strip()]
        if not directories:
            return
        req_id = self._start_worker("create_group", name.strip(), directories)
        self._pending_names[req_id] = name.strip()

    def _show_group(self, name: str) -> None:
        if not name or self._closing:
            return
        group = next((item for item in self._groups if str(item["nome"]) == name), None)
        if group is None:
            return
        self.title_label.setText(name)
        self._clear_columns()
        self._inspect_id = self._start_worker("inspect_group_files", name)

    def _make_folder_column(self, path: str, files: list[dict[str, Any]]) -> QWidget:
        column = QWidget()
        column.setObjectName("folderColumn")
        layout = QVBoxLayout(column)

        folder_name = QLabel(Path(path).name or path)
        folder_name.setObjectName("card")
        folder_path = QLabel(path)
        folder_path.setWordWrap(True)
        folder_path.setObjectName("folderPath")
        total_size = sum(int(item["tamanho"]) for item in files)
        size_text = self._format_size(total_size)
        badge = QLabel(f"{len(files)} arquivos · {size_text}")
        badge.setObjectName("card")

        file_list = QListWidget()
        file_list.setObjectName("folderFiles")
        for item in files:
            modified = item["modificado_em"]
            if isinstance(modified, datetime):
                date_text = modified.astimezone().strftime("%d/%m/%Y %H:%M")
            else:
                date_text = str(modified)
            file_list.addItem(
                f'{item["nome"]} — {self._format_size(int(item["tamanho"]))} — {date_text}'
            )

        open_button = QPushButton("Abrir")
        open_button.clicked.connect(lambda checked=False, folder=path: self._open_folder(folder))
        layout.addWidget(folder_name)
        layout.addWidget(folder_path)
        layout.addWidget(badge)
        layout.addWidget(file_list, 1)
        layout.addWidget(open_button)
        return column

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def _open_folder(path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _clear_columns(self) -> None:
        while self.splitter.count():
            widget = self.splitter.widget(0)
            self.splitter.widget(0).setParent(None)
            widget.deleteLater()
