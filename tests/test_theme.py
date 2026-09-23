from ui import theme


def test_theme_color_tokens() -> None:
    expected = {
        "BG_MAIN": "#0A060E",
        "BG_SIDEBAR": "#110816",
        "BG_CARD": "#190C22",
        "BG_CARD_HOVER": "#231030",
        "ACCENT_PRIMARY": "#C026D3",
        "ACCENT_HOVER": "#E879F9",
        "BORDER_SUBTLE": "#3A1448",
        "TEXT_PRIMARY": "#F5E8FF",
        "TEXT_MUTED": "#A892B5",
        "STATUS_SUCCESS": "#10B981",
        "STATUS_WARNING": "#F59E0B",
    }

    for name, value in expected.items():
        assert getattr(theme, name) == value


def test_load_stylesheet_returns_qt_stylesheet() -> None:
    stylesheet = theme.load_stylesheet()

    assert isinstance(stylesheet, str)
    assert stylesheet
    for selector in (
        "QMainWindow",
        "QWidget",
        "QPushButton",
        "QSplitter",
        "QProgressBar",
        "QSlider",
        "QScrollBar",
        "QLineEdit",
        "QListView",
    ):
        assert selector in stylesheet
    assert theme.ACCENT_PRIMARY in stylesheet
