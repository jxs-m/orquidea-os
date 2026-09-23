import os
from pathlib import Path


class ProcCollector:
    def __init__(
        self,
        stat_path: str | Path = "/proc/stat",
        meminfo_path: str | Path = "/proc/meminfo",
        disk_path: str = "/",
    ) -> None:
        self.stat_path = Path(stat_path)
        self.meminfo_path = Path(meminfo_path)
        self.disk_path = disk_path
        self._previous_cpu_ticks: tuple[int, int] | None = None

    def collect_cpu(self) -> dict[str, float]:
        with self.stat_path.open(encoding="utf-8") as stat_file:
            cpu_line = next(line for line in stat_file if line.startswith("cpu "))

        ticks = [int(value) for value in cpu_line.split()[1:]]
        idle_ticks = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)
        total_ticks = sum(ticks)
        current = (total_ticks, idle_ticks)
        previous = self._previous_cpu_ticks
        self._previous_cpu_ticks = current

        if previous is None:
            usage = 0.0
        else:
            total_delta = total_ticks - previous[0]
            idle_delta = idle_ticks - previous[1]
            usage = (
                (total_delta - idle_delta) / total_delta * 100.0
                if total_delta > 0
                else 0.0
            )

        return {"usage_percent": usage}

    def collect_memory(self) -> dict[str, float]:
        memory: dict[str, int] = {}
        with self.meminfo_path.open(encoding="utf-8") as meminfo_file:
            for line in meminfo_file:
                key, value = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable"}:
                    memory[key] = int(value.split()[0])

        total_kb = memory["MemTotal"]
        available_kb = memory["MemAvailable"]
        used_kb = total_kb - available_kb
        return {
            "total_bytes": float(total_kb * 1024),
            "used_bytes": float(used_kb * 1024),
            "usage_percent": used_kb / total_kb * 100.0,
        }

    def collect_disk(self) -> dict[str, float]:
        stats = os.statvfs(self.disk_path)
        total_bytes = stats.f_blocks * stats.f_frsize
        free_bytes = stats.f_bavail * stats.f_frsize
        used_bytes = total_bytes - free_bytes
        return {
            "total_bytes": float(total_bytes),
            "used_bytes": float(used_bytes),
            "free_bytes": float(free_bytes),
            "usage_percent": used_bytes / total_bytes * 100.0 if total_bytes else 0.0,
        }

    def collect(self) -> dict[str, dict[str, float]]:
        return {
            "cpu": self.collect_cpu(),
            "memory": self.collect_memory(),
            "disk": self.collect_disk(),
        }
