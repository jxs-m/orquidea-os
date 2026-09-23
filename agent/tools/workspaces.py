from datetime import datetime
from pathlib import Path

from daemon.storage import StorageManager


class WorkspaceManager:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    @staticmethod
    def _files(directory: Path) -> list[Path]:
        return sorted(path for path in directory.rglob("*") if path.is_file())

    @classmethod
    def _statistics(cls, paths: list[str]) -> tuple[int, int]:
        files = [file for path in paths for file in cls._files(Path(path))]
        return sum(file.stat().st_size for file in files), len(files)

    def create_group(self, name: str, paths: list[str]) -> int:
        if not name.strip():
            raise ValueError("group name cannot be empty")
        if not paths:
            raise ValueError("at least one directory is required")

        normalized_paths = []
        for value in paths:
            directory = Path(value).expanduser().resolve()
            if not directory.is_dir():
                raise ValueError(f"workspace path is not a directory: {directory}")
            normalized_paths.append(str(directory))
        return self.storage.add_virtual_group(name, normalized_paths)

    def get_group(self, name: str) -> dict[str, object]:
        group = next((item for item in self.storage.get_virtual_groups() if item["nome"] == name), None)
        if group is None:
            raise KeyError(name)
        total_size, file_count = self._statistics(group["caminhos"])
        return {
            **group,
            "tamanho_total": total_size,
            "contagem_arquivos": file_count,
        }

    def list_groups(self) -> list[dict[str, object]]:
        return [self.get_group(str(group["nome"])) for group in self.storage.get_virtual_groups()]

    def inspect_group_files(self, name: str) -> dict[str, list[dict[str, str | int | datetime]]]:
        group = self.get_group(name)
        result: dict[str, list[dict[str, str | int | datetime]]] = {}
        for directory_name in group["caminhos"]:
            directory = Path(directory_name)
            result[directory_name] = [
                {
                    "nome": file.name,
                    "tamanho": file.stat().st_size,
                    "extensao": file.suffix,
                    "modificado_em": datetime.fromtimestamp(file.stat().st_mtime).astimezone(),
                }
                for file in self._files(directory)
            ]
        return result
