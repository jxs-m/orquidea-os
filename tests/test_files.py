import json
from pathlib import Path
import shutil

import pytest

import agent.tools.files as files_module
from agent.tools.files import SafeFileManager


def test_safe_delete_sends_files_to_trash_and_writes_manifest(tmp_path, monkeypatch) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("important", encoding="utf-8")
    trash_path = tmp_path / "trash" / "notes.txt"
    trash_path.parent.mkdir()
    manager = SafeFileManager(tmp_path / "undo")

    def move_to_trash(path: str) -> None:
        shutil.move(path, trash_path)

    monkeypatch.setattr(files_module, "send2trash", move_to_trash)
    monkeypatch.setattr(manager, "_find_trash_destination", lambda original: trash_path)

    manifest_path = manager.safe_delete([str(source)])

    assert not source.exists()
    assert trash_path.read_text(encoding="utf-8") == "important"
    assert manifest_path.parent == tmp_path / "undo"
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {
        "entries": [
            {
                "origem": str(source.resolve()),
                "destino": str(trash_path),
                "restaurado": False,
            }
        ]
    }


def test_undo_restores_from_explicit_manifest(tmp_path, monkeypatch) -> None:
    source = tmp_path / "nested" / "notes.txt"
    trash_path = tmp_path / "trash" / "notes.txt"
    trash_path.parent.mkdir()
    trash_path.write_text("important", encoding="utf-8")
    manager = SafeFileManager(tmp_path / "undo")
    monkeypatch.setattr(manager, "_trash_roots", lambda: [tmp_path / "trash"])
    manager.undo_directory.mkdir()
    manifest_path = manager.undo_directory / "operation.json"
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "origem": str(source),
                        "destino": str(trash_path),
                        "restaurado": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    restored = manager.undo(manifest_path)

    assert restored == [str(source)]
    assert source.read_text(encoding="utf-8") == "important"
    assert not trash_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["entries"][0]["restaurado"]
    assert manager.undo(manifest_path) == []


def test_undo_defaults_to_latest_manifest(tmp_path, monkeypatch) -> None:
    manager = SafeFileManager(tmp_path / "undo")
    manager.undo_directory.mkdir()
    old_source = tmp_path / "old.txt"
    latest_source = tmp_path / "latest.txt"
    old_trash = tmp_path / "trash" / "old.txt"
    latest_trash = tmp_path / "trash" / "latest.txt"
    old_trash.parent.mkdir()
    old_trash.write_text("old", encoding="utf-8")
    latest_trash.write_text("latest", encoding="utf-8")
    monkeypatch.setattr(manager, "_trash_roots", lambda: [tmp_path / "trash"])

    for name, source, destination in (
        ("1.json", old_source, old_trash),
        ("2.json", latest_source, latest_trash),
    ):
        (manager.undo_directory / name).write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "origem": str(source),
                            "destino": str(destination),
                            "restaurado": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    assert manager.undo() == [str(latest_source)]
    assert latest_source.read_text(encoding="utf-8") == "latest"
    assert old_trash.exists()


def test_safe_delete_rejects_empty_duplicate_and_missing_paths(tmp_path) -> None:
    manager = SafeFileManager(tmp_path / "undo")
    source = tmp_path / "notes.txt"
    source.write_text("important", encoding="utf-8")

    with pytest.raises(ValueError, match="at least one path"):
        manager.safe_delete([])
    with pytest.raises(ValueError, match="duplicate paths"):
        manager.safe_delete([str(source), str(source)])
    with pytest.raises(FileNotFoundError):
        manager.safe_delete([str(tmp_path / "missing.txt")])


def test_undo_returns_empty_when_no_manifest_exists(tmp_path) -> None:
    assert SafeFileManager(tmp_path / "undo").undo() == []
