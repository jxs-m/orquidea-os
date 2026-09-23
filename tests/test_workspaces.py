import sqlite3

import pytest

from agent.tools.workspaces import WorkspaceManager
from daemon.storage import StorageManager


@pytest.fixture
def workspace_manager(tmp_path):
    storage = StorageManager(tmp_path / "state.db")
    yield WorkspaceManager(storage)
    storage.close()


def test_create_group_normalizes_and_persists_paths(tmp_path, workspace_manager) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()
    (directory / "a.txt").write_text("hello", encoding="utf-8")

    group_id = workspace_manager.create_group("docs", [str(directory / ".." / "folder")])

    group = workspace_manager.get_group("docs")
    assert group["id"] == group_id
    assert group["caminhos"] == [str(directory.resolve())]
    assert group["tamanho_total"] == 5
    assert group["contagem_arquivos"] == 1


def test_create_group_rejects_empty_or_invalid_paths(tmp_path, workspace_manager) -> None:
    with pytest.raises(ValueError):
        workspace_manager.create_group("", [str(tmp_path)])
    with pytest.raises(ValueError):
        workspace_manager.create_group("invalid", [str(tmp_path / "missing")])
    with pytest.raises(ValueError):
        workspace_manager.create_group("empty", [])


def test_group_names_are_unique(tmp_path, workspace_manager) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()
    workspace_manager.create_group("docs", [str(directory)])

    with pytest.raises(sqlite3.IntegrityError):
        workspace_manager.create_group("docs", [str(directory)])


def test_list_groups_and_inspect_files(tmp_path, workspace_manager) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    file_path = first / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")
    (second / "image.png").write_bytes(b"png")
    workspace_manager.create_group("project", [str(first), str(second)])

    groups = workspace_manager.list_groups()
    files = workspace_manager.inspect_group_files("project")

    assert [group["nome"] for group in groups] == ["project"]
    assert groups[0]["tamanho_total"] == 8
    assert groups[0]["contagem_arquivos"] == 2
    assert files[str(first.resolve())] == [
        {
            "nome": "notes.txt",
            "tamanho": 5,
            "extensao": ".txt",
            "modificado_em": files[str(first.resolve())][0]["modificado_em"],
        }
    ]
    assert files[str(first.resolve())][0]["modificado_em"].tzinfo is not None
    assert files[str(second.resolve())][0]["extensao"] == ".png"


def test_get_unknown_group_raises_key_error(workspace_manager) -> None:
    with pytest.raises(KeyError):
        workspace_manager.get_group("missing")
