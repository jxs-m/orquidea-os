from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import QEventLoop, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QListWidget, QPushButton, QSplitter, QWidget

from ui.views.workspace_view import WorkspaceView


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    return application if application is not None else QApplication([])


def _process_events(app: QApplication) -> None:
    loop = QEventLoop()
    QTimer.singleShot(0, loop.quit)
    loop.exec()
    app.processEvents()


def _columns(view: WorkspaceView) -> list[QWidget]:
    return [view.splitter.widget(index) for index in range(view.splitter.count())]


def test_view_shows_selected_group_files_and_column_statistics(app: QApplication) -> None:
    first_path = "/home/user/Área de Trabalho/enem"
    second_path = "/home/user/Documentos/iffar"
    modified = datetime(2025, 4, 3, 12, 30, tzinfo=timezone.utc)
    manager = Mock()
    manager.list_groups.return_value = [
        {"nome": "Estudos", "caminhos": [first_path, second_path]},
        {"nome": "Pessoal", "caminhos": [first_path]},
    ]
    manager.inspect_group_files.return_value = {
        first_path: [{"nome": "prova.pdf", "tamanho": 2048, "modificado_em": modified}],
        second_path: [{"nome": "resumo.txt", "tamanho": 512, "modificado_em": modified}],
    }

    view = WorkspaceView(manager)
    _process_events(app)

    assert view.splitter.orientation() == Qt.Orientation.Horizontal
    assert view.group_selector.count() == 2
    assert view.title_label.text() == "Estudos"
    assert manager.inspect_group_files.call_args.args == ("Estudos",)
    columns = _columns(view)
    assert len(columns) == 2
    assert [column.objectName() for column in columns] == ["folderColumn", "folderColumn"]

    first_labels = columns[0].findChildren(QLabel)
    assert any(label.text() == "enem" for label in first_labels)
    assert any(label.text() == first_path for label in first_labels)
    assert any(label.text() == "1 arquivos · 2.0 KB" for label in first_labels)
    first_list = columns[0].findChild(QListWidget, "folderFiles")
    assert first_list is not None
    assert first_list.count() == 1
    assert first_list.item(0).text() == (
        f"prova.pdf — 2.0 KB — {modified.astimezone().strftime('%d/%m/%Y %H:%M')}"
    )

    view.group_selector.setCurrentText("Pessoal")
    _process_events(app)
    assert view.title_label.text() == "Pessoal"
    assert manager.inspect_group_files.call_args.args == ("Pessoal",)
    assert view.splitter.count() == 1
    view.close()


def test_open_button_opens_its_folder_in_file_manager(app: QApplication) -> None:
    path = "/home/user/Documentos/iffar"
    manager = Mock()
    manager.list_groups.return_value = [{"nome": "Estudos", "caminhos": [path]}]
    manager.inspect_group_files.return_value = {path: []}

    view = WorkspaceView(manager)
    _process_events(app)
    button = view.splitter.widget(0).findChild(QPushButton)
    assert button is not None

    with patch("ui.views.workspace_view.QDesktopServices.openUrl", return_value=True) as open_url:
        button.click()

    open_url.assert_called_once()
    assert open_url.call_args.args[0].toLocalFile() == path
    view.close()


def test_view_with_no_groups_clears_columns(app: QApplication) -> None:
    manager = Mock()
    manager.list_groups.return_value = []

    view = WorkspaceView(manager)
    _process_events(app)

    assert view.title_label.text() == "Nenhum grupo"
    assert view.group_selector.count() == 0
    assert view.splitter.count() == 0
    manager.inspect_group_files.assert_not_called()
    view.close()
