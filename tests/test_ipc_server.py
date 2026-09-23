import json
import socket
import stat
from datetime import datetime, timezone

import pytest

from daemon.ipc_server import IPCServer


class FakeStorage:
    def get_virtual_groups(self):
        return [
            {
                "id": 1,
                "nome": "estudos",
                "caminhos": ["~/Documentos"],
                "criado_em": datetime(2026, 1, 2, tzinfo=timezone.utc),
            }
        ]


class FakeCollector:
    def collect(self):
        return {"cpu": {"usage_percent": 12.5}, "memory": {"usage_percent": 40.0}}


def request(socket_path, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        response = bytearray()
        while b"\n" not in response:
            response.extend(client.recv(4096))
    return json.loads(response.partition(b"\n")[0])


def test_server_handles_json_line_commands_and_serializes_groups(tmp_path) -> None:
    socket_path = tmp_path / "orquidea.sock"
    server = IPCServer(socket_path, FakeStorage(), FakeCollector())
    server.start()
    try:
        assert request(socket_path, {"method": "ping"}) == {"result": "pong"}
        assert request(socket_path, {"method": "get_metrics"}) == {
            "result": {"cpu": {"usage_percent": 12.5}, "memory": {"usage_percent": 40.0}}
        }
        assert request(socket_path, {"method": "get_groups"}) == {
            "result": [
                {
                    "id": 1,
                    "nome": "estudos",
                    "caminhos": ["~/Documentos"],
                    "criado_em": "2026-01-02T00:00:00+00:00",
                }
            ]
        }
    finally:
        server.stop()


def test_server_sets_socket_permissions_and_removes_path_on_stop(tmp_path) -> None:
    socket_path = tmp_path / "orquidea.sock"
    server = IPCServer(socket_path, FakeStorage(), FakeCollector())

    server.start()
    assert stat.S_IMODE(socket_path.stat().st_mode) == 0o660

    server.stop()

    assert not socket_path.exists()


def test_server_removes_stale_socket_before_bind(tmp_path) -> None:
    socket_path = tmp_path / "orquidea.sock"
    stale_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale_socket.bind(str(socket_path))
    stale_socket.close()
    server = IPCServer(socket_path, FakeStorage(), FakeCollector())

    server.start()
    try:
        assert request(socket_path, {"method": "ping"}) == {"result": "pong"}
    finally:
        server.stop()


def test_server_refuses_to_remove_non_socket_path(tmp_path) -> None:
    socket_path = tmp_path / "orquidea.sock"
    socket_path.write_text("keep", encoding="utf-8")
    server = IPCServer(socket_path, FakeStorage(), FakeCollector())

    with pytest.raises(FileExistsError):
        server.start()

    assert socket_path.read_text(encoding="utf-8") == "keep"


def test_server_returns_error_for_unknown_method(tmp_path) -> None:
    socket_path = tmp_path / "orquidea.sock"
    server = IPCServer(socket_path, FakeStorage(), FakeCollector())
    server.start()
    try:
        assert request(socket_path, {"method": "unknown"}) == {"error": "Unknown method"}
    finally:
        server.stop()
