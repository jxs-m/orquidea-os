from pathlib import Path
from typing import Final

BG_MAIN: Final[str] = "#0A060E"
BG_SIDEBAR: Final[str] = "#110816"
BG_CARD: Final[str] = "#190C22"
BG_CARD_HOVER: Final[str] = "#231030"
ACCENT_PRIMARY: Final[str] = "#C026D3"
ACCENT_HOVER: Final[str] = "#E879F9"
BORDER_SUBTLE: Final[str] = "#3A1448"
TEXT_PRIMARY: Final[str] = "#F5E8FF"
TEXT_MUTED: Final[str] = "#A892B5"
STATUS_SUCCESS: Final[str] = "#10B981"
STATUS_WARNING: Final[str] = "#F59E0B"


def load_stylesheet() -> str:
    return Path(__file__).with_name("styles.qss").read_text(encoding="utf-8")
