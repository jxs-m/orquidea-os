import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication

from ui.overlay import OrchidOverlay


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    return application if application is not None else QApplication([])


def test_overlay_initializes_as_translucent_topmost_widget(app: QApplication) -> None:
    overlay = OrchidOverlay()

    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.SubWindow
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert overlay.size() == overlay.minimumSize() == overlay.maximumSize()
    overlay.close()


def test_simple_click_emits_signal_once(app: QApplication) -> None:
    overlay = OrchidOverlay()
    spy = QSignalSpy(overlay.signal_clicked)
    overlay.show()

    from PyQt6.QtTest import QTest

    QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, pos=QPoint(36, 36))

    assert len(spy) == 1
    overlay.close()


def test_show_bubble_displays_text_and_hides_after_duration(app: QApplication) -> None:
    from PyQt6.QtTest import QTest

    overlay = OrchidOverlay()
    overlay.show_bubble("Olá, mundo", 40)
    app.processEvents()

    assert overlay._bubble.isVisible()
    assert overlay._bubble.text() == "Olá, mundo"
    assert overlay._bubble.y() < 0

    QTest.qWait(70)
    assert not overlay._bubble.isVisible()
    overlay.close()
