from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QUrl
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


class WorkspaceView(QWidget):
    def __init__(self, manager: WorkspaceManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._groups: list[dict[str, Any]] = []

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

    def refresh_groups(self) -> None:
        selected_name = self.group_selector.currentText()
        self._groups = self.manager.list_groups()
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
        self.manager.create_group(name.strip(), directories)
        self.refresh_groups()
        self.group_selector.setCurrentText(name.strip())

    def _show_group(self, name: str) -> None:
        if not name:
            return
        group = next((item for item in self._groups if str(item["nome"]) == name), None)
        if group is None:
            return
        self.title_label.setText(name)
        file_data = self.manager.inspect_group_files(name)
        self._clear_columns()
        for directory in group["caminhos"]:
            path = str(directory)
            files = file_data.get(path, [])
            self.splitter.addWidget(self._make_folder_column(path, files))

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
