import subprocess
from typing import Any, TypedDict

import dbus


class MediaMetadata(TypedDict):
    title: str
    artist: str
    album: str
    art_url: str
    status: str


class MediaController:
    MPRIS_INTERFACE = "org.mpris.MediaPlayer2.Player"
    PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
    OBJECT_PATH = "/org/mpris/MediaPlayer2"

    def __init__(self) -> None:
        self._bus: Any | None = None
        self._player: Any | None = None
        self._proxy: Any | None = None
        self._service_name = "org.mpris.MediaPlayer2.spotify"
        self._offline = False

    @staticmethod
    def _empty_metadata() -> MediaMetadata:
        return {
            "title": "",
            "artist": "",
            "album": "",
            "art_url": "",
            "status": "Offline",
        }

    def _clear_connection(self) -> None:
        self._bus = None
        self._player = None
        self._proxy = None
        self._offline = True

    def _connect(self) -> Any:
        if self._offline:
            raise dbus.exceptions.DBusException("MPRIS player is offline")
        if self._player is not None:
            return self._player

        bus = dbus.SessionBus()
        try:
            proxy = bus.get_object(self._service_name, self.OBJECT_PATH)
        except dbus.exceptions.DBusException:
            service = next(
                (
                    name
                    for name in bus.list_names()
                    if name.startswith("org.mpris.MediaPlayer2.")
                    and name != "org.mpris.MediaPlayer2"
                ),
                None,
            )
            if service is None:
                raise
            proxy = bus.get_object(service, self.OBJECT_PATH)
            self._service_name = str(service)

        self._bus = bus
        self._proxy = proxy
        self._player = dbus.Interface(proxy, self.MPRIS_INTERFACE)
        return self._player

    def _get_property(self, name: str) -> Any:
        if self._proxy is None:
            self._connect()
        properties = dbus.Interface(self._proxy, self.PROPERTIES_INTERFACE)
        return properties.Get(self.MPRIS_INTERFACE, name)

    def _get_connected_status(self) -> str:
        status = str(self._get_property("PlaybackStatus"))
        return status if status in {"Playing", "Paused", "Stopped"} else "Offline"

    def _call_player(self, method: str) -> None:
        try:
            player = self._connect()
            getattr(player, method)()
        except dbus.exceptions.DBusException:
            self._clear_connection()

    def play_pause(self) -> None:
        self._call_player("PlayPause")

    def next(self) -> None:
        self._call_player("Next")

    def previous(self) -> None:
        self._call_player("Previous")

    def get_status(self) -> str:
        try:
            return self._get_connected_status()
        except dbus.exceptions.DBusException:
            self._clear_connection()
            return "Offline"

    def get_metadata(self) -> MediaMetadata:
        try:
            metadata = self._get_property("Metadata")
            status = self._get_connected_status()
        except dbus.exceptions.DBusException:
            self._clear_connection()
            return self._empty_metadata()

        artists = metadata.get("xesam:artist", [])
        if isinstance(artists, (str, bytes)):
            artists = [artists]
        return {
            "title": str(metadata.get("xesam:title", "")),
            "artist": ", ".join(str(artist) for artist in artists),
            "album": str(metadata.get("xesam:album", "")),
            "art_url": str(metadata.get("mpris:artUrl", "")),
            "status": status,
        }

    def set_volume(self, percent: int) -> None:
        if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
            raise ValueError("percent must be an integer between 0 and 100")
        subprocess.run(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"],
            check=True,
        )
