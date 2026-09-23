import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from daemon.storage import StorageManager


def test_database_uses_wal_and_creates_expected_schemas(tmp_path) -> None:
    database_path = tmp_path / "state.db"

    with StorageManager(database_path) as storage:
        journal_mode = storage.connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode.lower() == "wal"

        expected_columns = {
            "metricas_sistema": ["id", "timestamp", "cpu", "ram", "disk", "iowait"],
            "incidentes_log": ["id", "timestamp", "severidade", "servico", "log_resumo", "status"],
            "grupos_virtuais": ["id", "nome", "caminhos", "criado_em"],
        }
        for table, columns in expected_columns.items():
            actual_columns = [
                row["name"]
                for row in storage.connection.execute(f"PRAGMA table_info({table})")
            ]
            assert actual_columns == columns

        group_name_index = storage.connection.execute(
            "PRAGMA index_list(grupos_virtuais)"
        ).fetchall()
        assert any(row["unique"] for row in group_name_index)


def test_metrics_round_trip_and_limit(tmp_path) -> None:
    timestamp = datetime.now(timezone.utc)
    with StorageManager(tmp_path / "state.db") as storage:
        metric_id = storage.add_metric(12.5, 45.0, 67.5, iowait=2.25, timestamp=timestamp)
        storage.add_metric(13.0, 46.0, 68.0, timestamp=timestamp + timedelta(seconds=1))

        metrics = storage.get_metrics(limit=1)

    assert len(metrics) == 1
    assert metrics[0] == {
        "id": metric_id + 1,
        "timestamp": timestamp + timedelta(seconds=1),
        "cpu": 13.0,
        "ram": 46.0,
        "disk": 68.0,
        "iowait": 0.0,
    }


def test_incidents_persist_in_new_storage_manager(tmp_path) -> None:
    database_path = tmp_path / "state.db"
    timestamp = datetime(2026, 2, 3, 4, 5, tzinfo=timezone.utc)
    with StorageManager(database_path) as storage:
        incident_id = storage.add_incident(
            "alta", "daemon", "Uso de CPU elevado", "aberto", timestamp
        )

    with StorageManager(database_path) as storage:
        incidents = storage.get_incidents()

    assert incidents == [
        {
            "id": incident_id,
            "timestamp": timestamp,
            "severidade": "alta",
            "servico": "daemon",
            "log_resumo": "Uso de CPU elevado",
            "status": "aberto",
        }
    ]


def test_virtual_groups_store_json_and_preserve_unicode_paths(tmp_path) -> None:
    paths = ["~/Área de trabalho/enem", "~/Documentos/iffar"]
    timestamp = datetime(2026, 3, 4, 5, 6, tzinfo=timezone.utc)

    with StorageManager(tmp_path / "state.db") as storage:
        group_id = storage.add_virtual_group("estudos", paths, timestamp)
        raw_paths = storage.connection.execute(
            "SELECT caminhos FROM grupos_virtuais WHERE id = ?", (group_id,)
        ).fetchone()["caminhos"]
        groups = storage.get_virtual_groups()

    assert json.loads(raw_paths) == paths
    assert groups == [
        {
            "id": group_id,
            "nome": "estudos",
            "caminhos": paths,
            "criado_em": timestamp,
        }
    ]


def test_virtual_group_names_are_unique(tmp_path) -> None:
    with StorageManager(tmp_path / "state.db") as storage:
        storage.add_virtual_group("estudos", ["~/Documentos"])

        with pytest.raises(sqlite3.IntegrityError):
            storage.add_virtual_group("estudos", ["~/Área de trabalho"])


def test_metric_retention_removes_data_older_than_seven_days(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    with StorageManager(tmp_path / "state.db") as storage:
        storage.add_metric(1.0, 1.0, 1.0, timestamp=now - timedelta(days=8))
        retained_id = storage.add_metric(2.0, 2.0, 2.0, timestamp=now - timedelta(days=6))
        storage.add_metric(3.0, 3.0, 3.0, timestamp=now)

        metrics = storage.get_metrics()

    assert {metric["id"] for metric in metrics} == {retained_id, retained_id + 1}
    assert all(metric["timestamp"] >= now - timedelta(days=7) for metric in metrics)
