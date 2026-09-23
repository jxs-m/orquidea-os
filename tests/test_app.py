from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from ui.app import MainWindow


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    return application if application is not None else QApplication([])


def _finish_workers(app: QApplication, window: MainWindow) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: loop.quit() if not window.media_bar._workers else None)
    timer.start()
    QTimer.singleShot(1000, loop.quit)
    loop.exec()
    timer.stop()
    app.processEvents()
    assert not window.media_bar._workers


def _make_window() -> tuple[MainWindow, Mock, Mock]:
    manager = Mock()
    manager.list_groups.return_value = []
    media_controller = Mock()
    media_controller.get_metadata.return_value = {
        "title": "",
        "artist": "",
        "album": "",
        "art_url": "",
        "status": "Offline",
    }
    return MainWindow(manager, media_controller), manager, media_controller


def test_main_window_has_expected_components(app: QApplication) -> None:
    window, manager, _ = _make_window()

    assert window.windowTitle() == "Orquídea OS"
    assert isinstance(window.workspace_view, QWidget)
    assert window.pages.count() == 3
    assert window.pages.widget(0) is window.workspace_view
    assert window.media_bar.objectName() == "mediaFooter"
    manager.list_groups.assert_called_once_with()
    assert window.minimize_button.accessibleName() == "Minimizar"
    assert window.maximize_button.accessibleName() == "Maximizar"
    assert window.close_button.accessibleName() == "Fechar"

    window.close()
    _finish_workers(app, window)


def test_sidebar_navigation_buttons_select_pages(app: QApplication) -> None:
    window, _, _ = _make_window()

    buttons = window.sidebar.findChildren(QPushButton)
    assert [button.text() for button in buttons] == [
        "📁 Grupos de Pastas",
        "📊 Dashboard",
        "🔑 Cofre de Chaves",
    ]
    assert window.sidebar.objectName() == "sidebar"
    for index, button in enumerate(buttons):
        button.click()
        assert window.pages.currentIndex() == index

    window.close()
    _finish_workers(app, window)


def test_media_bar_is_connected_to_injected_controller(app: QApplication) -> None:
    window, _, controller = _make_window()

    _finish_workers(app, window)

    assert window.media_bar.controller is controller
    assert window.media_bar.refresh_timer.isActive()
    window.close()


def test_header_includes_application_title(app: QApplication) -> None:
    window, _, _ = _make_window()

    labels = window.findChildren(QLabel)
    assert any(label.text() == "🌸 Orquídea OS" for label in labels)

    window.close()
    _finish_workers(app, window)
