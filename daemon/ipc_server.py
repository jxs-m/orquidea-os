import json
import os
import socket
import stat
import threading
import time
from pathlib import Path
from typing import Any

from daemon.collectors.proc_collector import ProcCollector
from daemon.storage import StorageManager


class IPCServer:
    def __init__(
        self,
        socket_path: str | Path = "/run/orquidea.sock",
        storage_manager: StorageManager | None = None,
        proc_collector: ProcCollector | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.storage_manager = storage_manager or StorageManager()
        self.proc_collector = proc_collector or ProcCollector()
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._transition_lock = threading.Lock()
        self._socket_identity: tuple[int, int] | None = None

    def start(self) -> None:
        with self._transition_lock, self._lifecycle_lock:
            if self._server_socket is not None:
                return

            try:
                existing = self.socket_path.lstat()
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if not stat.S_ISSOCK(existing.st_mode):
                    raise FileExistsError(f"Refusing to replace non-socket: {self.socket_path}")
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.2)
                    try:
                        probe.connect(str(self.socket_path))
                    except ConnectionRefusedError:
                        pass
                    else:
                        raise FileExistsError(f"Socket already in use: {self.socket_path}")
                self.socket_path.unlink()

            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                server_socket.bind(str(self.socket_path))
                socket_stat = self.socket_path.lstat()
                self._socket_identity = (socket_stat.st_dev, socket_stat.st_ino)
                os.chmod(self.socket_path, 0o660)
                server_socket.listen()
                server_socket.settimeout(0.2)
                self._server_socket = server_socket
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._serve, name="orquidea-ipc", daemon=True)
                self._thread.start()
            except BaseException:
                server_socket.close()
                self._server_socket = None
                self._thread = None
                self._remove_socket_file()
                raise

    def _serve(self) -> None:
        server_socket = self._server_socket
        if server_socket is None:
            return

        try:
            while not self._stop_event.is_set():
                try:
                    client, _ = server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop_event.is_set():
                        break
                    raise
                with client:
                    client.settimeout(0.2)
                    self._handle_client(client)
        finally:
            with self._lifecycle_lock:
                if self._server_socket is server_socket:
                    self._server_socket = None
                    self._thread = None
                    server_socket.close()
                    self._remove_socket_file()

    def _handle_client(self, client: socket.socket) -> None:
        pending = bytearray()
        deadline = time.monotonic() + 2.0
        while not self._stop_event.is_set():
            if time.monotonic() >= deadline:
                return
            try:
                data = client.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not data:
                return

            deadline = time.monotonic() + 2.0
            pending.extend(data)
            if len(pending) > 65536:
                return
            while b"\n" in pending:
                line, _, remainder = pending.partition(b"\n")
                pending = bytearray(remainder)
                try:
                    response = self._dispatch(line)
                except Exception:
                    response = b'{"error": "Request failed"}'
                try:
                    client.sendall(response + b"\n")
                except OSError:
                    return

    def _dispatch(self, line: bytes) -> bytes:
        try:
            request = json.loads(line)
            method = request["method"]
            if method == "ping":
                result: Any = "pong"
            elif method == "get_metrics":
                result = self.proc_collector.collect()
            elif method == "get_groups":
                result = self.storage_manager.get_virtual_groups()
            else:
                return json.dumps({"error": "Unknown method"}).encode("utf-8")
            response = {"result": result}
        except (json.JSONDecodeError, KeyError, TypeError):
            response = {"error": "Invalid request"}
        return json.dumps(response, ensure_ascii=False, default=self._json_default).encode("utf-8")

    @staticmethod
    def _json_default(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _remove_socket_file(self) -> None:
        try:
            current = self.socket_path.lstat()
        except FileNotFoundError:
            self._socket_identity = None
            return

        identity = (current.st_dev, current.st_ino)
        if stat.S_ISSOCK(current.st_mode) and identity == self._socket_identity:
            self.socket_path.unlink()
        self._socket_identity = None

    def stop(self) -> None:
        with self._transition_lock:
            with self._lifecycle_lock:
                server_socket = self._server_socket
                thread = self._thread
                if server_socket is None:
                    return
                self._stop_event.set()
                server_socket.close()

            if thread is not None and thread is not threading.current_thread():
                thread.join()
