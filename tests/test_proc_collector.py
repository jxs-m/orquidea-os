from types import SimpleNamespace

from daemon.collectors.proc_collector import ProcCollector


def test_cpu_usage_is_calculated_from_tick_deltas(tmp_path) -> None:
    stat_path = tmp_path / "stat"
    stat_path.write_text("cpu 100 0 50 850 0 0 0 0 0 0\n", encoding="utf-8")
    collector = ProcCollector(stat_path=stat_path)

    first = collector.collect_cpu()
    stat_path.write_text("cpu 150 0 70 880 0 0 0 0 0 0\n", encoding="utf-8")
    second = collector.collect_cpu()

    assert first["usage_percent"] == 0.0
    assert second["usage_percent"] == 70.0


def test_memory_uses_memtotal_and_memavailable(tmp_path) -> None:
    meminfo_path = tmp_path / "meminfo"
    meminfo_path.write_text(
        "MemTotal:       1000 kB\nMemAvailable:    400 kB\n",
        encoding="utf-8",
    )
    collector = ProcCollector(meminfo_path=meminfo_path)

    memory = collector.collect_memory()

    assert memory == {
        "total_bytes": 1_024_000.0,
        "used_bytes": 614_400.0,
        "usage_percent": 60.0,
    }


def test_disk_uses_statvfs_root_capacity(monkeypatch) -> None:
    monkeypatch.setattr(
        "daemon.collectors.proc_collector.os.statvfs",
        lambda path: SimpleNamespace(f_blocks=100, f_frsize=4096, f_bavail=25),
    )
    collector = ProcCollector()

    disk = collector.collect_disk()

    assert disk == {
        "total_bytes": 409_600.0,
        "used_bytes": 307_200.0,
        "free_bytes": 102_400.0,
        "usage_percent": 75.0,
    }
