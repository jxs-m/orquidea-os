import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from ui.widgets.media_bar import MediaBar


def _finish_workers(app: QApplication, bar: MediaBar) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: loop.quit() if not bar._workers else None)
    timer.start()
    QTimer.singleShot(1000, loop.quit)
    loop.exec()
    timer.stop()
    app.processEvents()
    assert not bar._workers


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    return application if application is not None else QApplication([])


def test_media_bar_builds_controls_and_refreshes_metadata(app: QApplication) -> None:
    controller = Mock()
    controller.get_metadata.return_value = {
        "title": "Song",
        "artist": "Artist",
        "album": "Album",
        "art_url": "",
        "status": "Playing",
    }
    bar = MediaBar(controller)

    assert bar.refresh_timer.interval() == 1000
    assert bar.refresh_timer.isActive()
    assert bar.volume_slider.minimum() == 0
    assert bar.volume_slider.maximum() == 100
    assert bar.previous_button.text() == "⏮"
    assert bar.play_pause_button.text() == "▶"
    assert bar.next_button.text() == "⏭"

    bar._apply_metadata(controller.get_metadata.return_value)

    assert bar.title_label.text() == "Song"
    assert bar.artist_label.text() == "Artist"
    assert bar.play_pause_button.text() == "⏸"
    bar.close()


def test_buttons_and_volume_route_to_controller_on_workers(app: QApplication) -> None:
    controller = Mock()
    bar = MediaBar(controller)
    bar.previous_button.click()
    bar.play_pause_button.click()
    bar.next_button.click()
    bar.volume_slider.setValue(65)

    _finish_workers(app, bar)

    assert controller.previous.call_count == 1
    assert controller.play_pause.call_count == 1
    assert controller.next.call_count == 1
    controller.set_volume.assert_called_once_with(65)
    bar.close()


def test_metadata_refresh_runs_in_worker_and_updates_play_state(app: QApplication) -> None:
    controller = Mock()
    controller.get_metadata.return_value = {
        "title": "Async Song",
        "artist": "Async Artist",
        "album": "Async Album",
        "art_url": "",
        "status": "Paused",
    }
    bar = MediaBar(controller)

    _finish_workers(app, bar)

    assert controller.get_metadata.call_count == 1
    assert bar.title_label.text() == "Async Song"
    assert bar.artist_label.text() == "Async Artist"
    assert bar.play_pause_button.text() == "▶"
    bar.close()
