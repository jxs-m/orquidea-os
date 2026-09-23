from unittest.mock import Mock, patch

import dbus
import pytest

from agent.tools.media import MediaController


SERVICE = "org.mpris.MediaPlayer2.spotify"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
OBJECT_PATH = "/org/mpris/MediaPlayer2"


@pytest.fixture
def dbus_player():
    proxy = Mock()
    player = Mock()
    properties = Mock()
    bus = Mock()
    bus.get_object.return_value = proxy

    with patch("agent.tools.media.dbus.SessionBus", return_value=bus), patch(
        "agent.tools.media.dbus.Interface",
        side_effect=lambda obj, interface: player if interface == PLAYER_INTERFACE else properties,
    ):
        yield bus, proxy, player, properties


def test_playback_commands_call_mpris_methods(dbus_player) -> None:
    _, _, player, _ = dbus_player
    controller = MediaController()

    controller.play_pause()
    controller.next()
    controller.previous()

    player.PlayPause.assert_called_once_with()
    player.Next.assert_called_once_with()
    player.Previous.assert_called_once_with()


def test_status_returns_playback_status(dbus_player) -> None:
    _, _, _, properties = dbus_player
    properties.Get.return_value = "Playing"
    controller = MediaController()

    assert controller.get_status() == "Playing"
    properties.Get.assert_called_once_with(PLAYER_INTERFACE, "PlaybackStatus")


def test_get_metadata_returns_typed_fields_and_status(dbus_player) -> None:
    _, _, _, properties = dbus_player
    properties.Get.side_effect = [
        {
            "xesam:title": "Song",
            "xesam:artist": ["Artist One", "Artist Two"],
            "xesam:album": "Album",
            "mpris:artUrl": "file:///cover.jpg",
        },
        "Paused",
    ]
    controller = MediaController()

    assert controller.get_metadata() == {
        "title": "Song",
        "artist": "Artist One, Artist Two",
        "album": "Album",
        "art_url": "file:///cover.jpg",
        "status": "Paused",
    }


def test_falls_back_to_active_mpris_player(dbus_player) -> None:
    bus, _, player, _ = dbus_player
    bus.get_object.side_effect = [
        dbus.exceptions.DBusException("Spotify unavailable"),
        Mock(),
    ]
    bus.list_names.return_value = ["org.mpris.MediaPlayer2.vlc"]
    controller = MediaController()

    controller.next()

    assert bus.get_object.call_args_list[0].args == (SERVICE, OBJECT_PATH)
    assert bus.get_object.call_args_list[1].args == (
        "org.mpris.MediaPlayer2.vlc",
        OBJECT_PATH,
    )
    player.Next.assert_called_once_with()


def test_closed_player_returns_offline_status_and_empty_metadata() -> None:
    with patch(
        "agent.tools.media.dbus.SessionBus",
        side_effect=dbus.exceptions.DBusException("No session bus"),
    ):
        controller = MediaController()

        assert controller.get_status() == "Offline"
        assert controller.get_metadata() == {
            "title": "",
            "artist": "",
            "album": "",
            "art_url": "",
            "status": "Offline",
        }


def test_player_disappearing_returns_offline_metadata(dbus_player) -> None:
    _, _, _, properties = dbus_player
    properties.Get.side_effect = dbus.exceptions.DBusException("Player closed")
    controller = MediaController()

    assert controller.get_metadata() == {
        "title": "",
        "artist": "",
        "album": "",
        "art_url": "",
        "status": "Offline",
    }


def test_set_volume_invokes_wpctl(dbus_player) -> None:
    controller = MediaController()
    with patch("agent.tools.media.subprocess.run") as run:
        controller.set_volume(35)

    run.assert_called_once_with(
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "35%"],
        check=True,
    )


@pytest.mark.parametrize("percent", [-1, 101, 1.5, True, "50"])
def test_set_volume_rejects_invalid_percent(percent) -> None:
    controller = MediaController()
    with patch("agent.tools.media.subprocess.run") as run:
        with pytest.raises(ValueError):
            controller.set_volume(percent)

    run.assert_not_called()
