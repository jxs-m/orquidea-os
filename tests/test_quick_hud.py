import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QEventLoop, QPoint, QTimer, Qt
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication, QWidget

from ui.widgets.quick_hud import QuickHUD


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    return application if application is not None else QApplication([])


def _finish_workers(app: QApplication, hud: QuickHUD) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: loop.quit() if not hud._workers else None)
    timer.start()
    QTimer.singleShot(1000, loop.quit)
    loop.exec()
    timer.stop()
    app.processEvents()
    assert not hud._workers


def test_quick_hud_initializes_controls_and_refresh_timers(app: QApplication) -> None:
    collector = Mock()
    collector.collect.return_value = {
        "cpu": {"usage_percent": 12},
        "memory": {"usage_percent": 34},
        "disk": {"usage_percent": 56},
    }
    media_controller = Mock()
    media_controller.get_metadata.return_value = {"title": "Song", "status": "Playing"}
    hud = QuickHUD(collector, media_controller)

    assert hud.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert hud.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert hud.windowFlags() & Qt.WindowType.Tool
    assert hud.open_main_button.text() == "Abrir Orquídea OS"
    assert hud.prompt_input.placeholderText() == "Converse com o AGY..."
    assert hud._metrics_timer.interval() == hud._metadata_timer.interval() == 1000
    assert hud._metrics_timer.isActive()
    assert hud._metadata_timer.isActive()

    _finish_workers(app, hud)

    assert hud.cpu_bar.value() == 12
    assert hud.ram_bar.value() == 34
    assert hud.disk_bar.value() == 56
    assert hud.track_title.text() == "Song"
    assert hud.play_pause_button.text() == "⏸"
    hud.close()


def test_open_main_button_emits_signal_and_reveals_window(app: QApplication) -> None:
    main_window = Mock(spec=QWidget)
    hud = QuickHUD(collector=Mock(), media_controller=Mock(), main_window=main_window)
    spy = QSignalSpy(hud.open_main_requested)

    hud.open_main_button.click()

    assert len(spy) == 1
    main_window.showNormal.assert_called_once_with()
    main_window.show.assert_called_once_with()
    main_window.raise_.assert_called_once_with()
    main_window.activateWindow.assert_called_once_with()
    _finish_workers(app, hud)
    hud.close()


def test_prompt_submits_button_and_enter_and_clears_input(app: QApplication) -> None:
    hud = QuickHUD(collector=Mock(), media_controller=Mock())
    spy = QSignalSpy(hud.prompt_submitted)

    hud.prompt_input.setText("  Olá AGY  ")
    hud.prompt_button.click()
    assert len(spy) == 1
    assert spy[0][0] == "Olá AGY"
    assert hud.prompt_input.text() == ""

    hud.prompt_input.setText("Outra mensagem")
    hud.prompt_input.returnPressed.emit()
    assert len(spy) == 2
    assert spy[1][0] == "Outra mensagem"
    assert hud.prompt_input.text() == ""

    hud.prompt_input.setText("   ")
    hud._submit_prompt()
    assert len(spy) == 2
    _finish_workers(app, hud)
    hud.close()


def test_toggle_at_centers_hud_and_alternates_visibility(app: QApplication) -> None:
    hud = QuickHUD(collector=Mock(), media_controller=Mock())
    hud.resize(300, 200)
    point = QPoint(500, 400)

    hud.toggle_at(point)

    assert hud.isVisible()
    assert hud.pos() == QPoint(350, 300)
    hud.toggle_at(point)
    assert not hud.isVisible()
    _finish_workers(app, hud)
    hud.close()
