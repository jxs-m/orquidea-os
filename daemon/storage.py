import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path


class StorageManager:
    def __init__(self, database_path: str | Path = "state.db") -> None:
        self.database_path = str(database_path)
        self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self.connection.execute("PRAGMA journal_mode=WAL;")
            self._create_tables()

    def _create_tables(self) -> None:
        with self._lock:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metricas_sistema (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME,
                    cpu REAL,
                    ram REAL,
                    disk REAL,
                    iowait REAL
                );
                CREATE TABLE IF NOT EXISTS incidentes_log (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME,
                    severidade TEXT,
                    servico TEXT,
                    log_resumo TEXT,
                    status TEXT
                );
                CREATE TABLE IF NOT EXISTS grupos_virtuais (
                    id INTEGER PRIMARY KEY,
                    nome TEXT UNIQUE,
                    caminhos TEXT,
                    criado_em DATETIME
                );
                """
            )
            self.connection.commit()

    @staticmethod
    def _timestamp(value: datetime | None) -> str:
        timestamp = value or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def add_metric(
        self,
        cpu: float,
        ram: float,
        disk: float,
        iowait: float = 0.0,
        timestamp: datetime | None = None,
    ) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO metricas_sistema (timestamp, cpu, ram, disk, iowait)
                   VALUES (?, ?, ?, ?, ?)""",
                (self._timestamp(timestamp), cpu, ram, disk, iowait),
            )
            self._prune_metrics(datetime.now(timezone.utc) - timedelta(days=7))
            self.connection.commit()
            return int(cursor.lastrowid)

    def get_metrics(self, limit: int | None = None) -> list[dict[str, float | int | datetime]]:
        query = "SELECT id, timestamp, cpu, ram, disk, iowait FROM metricas_sistema ORDER BY timestamp DESC, id DESC"
        parameters: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            parameters = (limit,)
        with self._lock:
            rows = self.connection.execute(query, parameters).fetchall()
        return [
            {
                "id": row["id"],
                "timestamp": self._datetime(row["timestamp"]),
                "cpu": row["cpu"],
                "ram": row["ram"],
                "disk": row["disk"],
                "iowait": row["iowait"],
            }
            for row in rows
        ]

    def _prune_metrics(self, cutoff: datetime) -> None:
        self.connection.execute(
            "DELETE FROM metricas_sistema WHERE timestamp < ?",
            (self._timestamp(cutoff),),
        )

    def add_incident(
        self,
        severidade: str,
        servico: str,
        log_resumo: str,
        status: str,
        timestamp: datetime | None = None,
    ) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO incidentes_log (timestamp, severidade, servico, log_resumo, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (self._timestamp(timestamp), severidade, servico, log_resumo, status),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def get_incidents(self, limit: int | None = None) -> list[dict[str, str | int | datetime]]:
        query = "SELECT id, timestamp, severidade, servico, log_resumo, status FROM incidentes_log ORDER BY timestamp DESC, id DESC"
        parameters: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            parameters = (limit,)
        with self._lock:
            rows = self.connection.execute(query, parameters).fetchall()
        return [
            {
                "id": row["id"],
                "timestamp": self._datetime(row["timestamp"]),
                "severidade": row["severidade"],
                "servico": row["servico"],
                "log_resumo": row["log_resumo"],
                "status": row["status"],
            }
            for row in rows
        ]

    def add_virtual_group(
        self,
        nome: str,
        caminhos: list[str],
        criado_em: datetime | None = None,
    ) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO grupos_virtuais (nome, caminhos, criado_em)
                   VALUES (?, ?, ?)""",
                (nome, json.dumps(caminhos, ensure_ascii=False), self._timestamp(criado_em)),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def get_virtual_groups(self) -> list[dict[str, str | int | datetime | list[str]]]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT id, nome, caminhos, criado_em FROM grupos_virtuais ORDER BY id"
            ).fetchall()
        return [
            {
                "id": row["id"],
                "nome": row["nome"],
                "caminhos": json.loads(row["caminhos"]),
                "criado_em": self._datetime(row["criado_em"]),
            }
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def __enter__(self) -> "StorageManager":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
