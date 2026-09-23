import sys
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from agent.tools.media import MediaController
from agent.tools.workspaces import WorkspaceManager
from daemon.storage import StorageManager
from ui.overlay import OrchidOverlay
from ui.theme import load_stylesheet
from ui.views.workspace_view import WorkspaceView
from ui.widgets.media_bar import MediaBar
from ui.widgets.quick_hud import QuickHUD


class MainWindow(QMainWindow):
    def __init__(
        self,
        workspace_manager: WorkspaceManager | None = None,
        media_controller: MediaController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Orquídea OS")
        self.resize(1200, 800)

        self._storage_manager = StorageManager() if workspace_manager is None else None
        self.workspace_manager = workspace_manager or WorkspaceManager(self._storage_manager)

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        root_layout.addWidget(self._make_header())

        body = QHBoxLayout()
        body.setSpacing(12)
        self.sidebar = self._make_sidebar()
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("mainPages")
        self.workspace_view = WorkspaceView(self.workspace_manager)
        self.pages.addWidget(self.workspace_view)
        self.pages.addWidget(self._make_named_page("Dashboard"))
        self.pages.addWidget(self._make_named_page("Cofre de Chaves"))
        body.addWidget(self.pages, 1)
        root_layout.addLayout(body, 1)

        self.media_bar = MediaBar(media_controller)
        self.media_bar.setObjectName("mediaFooter")
        root_layout.addWidget(self.media_bar)

        self.setCentralWidget(central)

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 4, 4, 4)

        title = QLabel("🌸 Orquídea OS")
        title.setObjectName("appTitle")
        layout.addWidget(title, 1)

        self.minimize_button = self._window_button("—", "Minimizar", "minimizeWindow")
        self.maximize_button = self._window_button("□", "Maximizar", "maximizeWindow")
        self.close_button = self._window_button("×", "Fechar", "closeWindow")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximized)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)
        return header

    @staticmethod
    def _window_button(text: str, accessible_name: str, object_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setAccessibleName(accessible_name)
        button.setObjectName(object_name)
        return button

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        labels = ("📁 Grupos de Pastas", "📊 Dashboard", "🔑 Cofre de Chaves")
        self.navigation_buttons: list[QPushButton] = []
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName(f"navigationButton{index}")
            button.clicked.connect(lambda checked=False, page=index: self.pages.setCurrentIndex(page))
            self.navigation_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)
        self.navigation_buttons[0].setChecked(True)
        return sidebar

    @staticmethod
    def _make_named_page(title: str) -> QWidget:
        page = QWidget()
        page.setObjectName(f"{title.lower().replace(' ', '')}Page")
        layout = QVBoxLayout(page)
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 1)
        return page

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("□")
            self.maximize_button.setAccessibleName("Maximizar")
        else:
            self.showMaximized()
            self.maximize_button.setText("❐")
            self.maximize_button.setAccessibleName("Restaurar")

    def closeEvent(self, event: Any) -> None:
        self.media_bar.refresh_timer.stop()
        if hasattr(self, "workspace_view"):
            self.workspace_view.begin_close()
        if self._storage_manager is not None:
            self._storage_manager.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())
    window = MainWindow()
    hud = QuickHUD(main_window=window)
    overlay = OrchidOverlay()
    overlay.signal_clicked.connect(lambda: hud.toggle_at(overlay.geometry().center()))
    hud.prompt_submitted.connect(
        lambda text: overlay.show_bubble(f"AGY: Mensagem recebida ('{text[:18]}...')")
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
