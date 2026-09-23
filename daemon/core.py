import threading
from typing import Any

from daemon.collectors.proc_collector import ProcCollector
from daemon.ipc_server import IPCServer
from daemon.storage import StorageManager


class OrquideaDaemon:
    def __init__(
        self,
        storage_manager: StorageManager | None = None,
        proc_collector: ProcCollector | None = None,
        ipc_server: IPCServer | None = None,
        sample_interval: float = 2.0,
    ) -> None:
        self.storage_manager = storage_manager or StorageManager()
        self.proc_collector = proc_collector or ProcCollector()
        self.ipc_server = ipc_server or IPCServer(
            storage_manager=self.storage_manager,
            proc_collector=self.proc_collector,
        )
        self.sample_interval = sample_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.ipc_server.start()
            self._thread = threading.Thread(
                target=self._run,
                name="orquidea-sampler",
                daemon=True,
            )
            self._thread.start()

    def tick(self) -> None:
        metrics: dict[str, Any] = self.proc_collector.collect()
        self.storage_manager.add_metric(
            metrics["cpu"]["usage_percent"],
            metrics["memory"]["usage_percent"],
            metrics["disk"]["usage_percent"],
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self.sample_interval)

    def stop(self) -> None:
        with self._lifecycle_lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread is not None and thread is not threading.current_thread():
            thread.join()
        self.ipc_server.stop()
        self.storage_manager.close()
