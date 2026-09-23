import threading

import pytest

from daemon.core import OrquideaDaemon


class FakeStorage:
    def __init__(self) -> None:
        self.metrics: list[tuple[float, float, float]] = []
        self.closed = False

    def add_metric(self, cpu: float, ram: float, disk: float) -> None:
        self.metrics.append((cpu, ram, disk))

    def close(self) -> None:
        self.closed = True


class FakeCollector:
    def __init__(self) -> None:
        self.collect_calls = 0

    def collect(self) -> dict[str, dict[str, float]]:
        self.collect_calls += 1
        return {
            "cpu": {"usage_percent": 12.5},
            "memory": {"usage_percent": 45.0},
            "disk": {"usage_percent": 67.0},
        }


class FakeIPCServer:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def test_tick_collects_metrics_and_stores_values() -> None:
    storage = FakeStorage()
    collector = FakeCollector()
    daemon = OrquideaDaemon(storage, collector, FakeIPCServer())

    daemon.tick()

    assert collector.collect_calls == 1
    assert storage.metrics == [(12.5, 45.0, 67.0)]


def test_start_starts_ipc_and_sampling_thread() -> None:
    storage = FakeStorage()
    collector = FakeCollector()
    ipc_server = FakeIPCServer()
    daemon = OrquideaDaemon(storage, collector, ipc_server, sample_interval=60.0)

    daemon.start()
    try:
        assert ipc_server.started
        assert isinstance(daemon._thread, threading.Thread)
        assert daemon._thread.is_alive()
        assert collector.collect_calls >= 1
    finally:
        daemon.stop()


def test_start_failure_does_not_start_sampler() -> None:
    storage = FakeStorage()
    collector = FakeCollector()
    ipc_server = FakeIPCServer()
    daemon = OrquideaDaemon(storage, collector, ipc_server)

    def fail() -> None:
        raise OSError("Socket unavailable")

    ipc_server.start = fail
    try:
        with pytest.raises(OSError, match="Socket unavailable"):
            daemon.start()
        assert collector.collect_calls == 0
        assert daemon._thread is None
    finally:
        daemon.stop()


def test_stop_stops_thread_ipc_and_storage() -> None:
    storage = FakeStorage()
    ipc_server = FakeIPCServer()
    daemon = OrquideaDaemon(
        storage,
        FakeCollector(),
        ipc_server,
        sample_interval=60.0,
    )

    daemon.start()
    thread = daemon._thread
    daemon.stop()

    assert daemon._stop_event.is_set()
    assert thread is not None and not thread.is_alive()
    assert ipc_server.stopped
    assert storage.closed
