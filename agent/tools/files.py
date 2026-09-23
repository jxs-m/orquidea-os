import json
import os
import shutil
import time
from pathlib import Path
from urllib.parse import unquote

from send2trash import send2trash


class SafeFileManager:
    def __init__(self, undo_directory: str | Path | None = None) -> None:
        self.undo_directory = Path(undo_directory or Path.home() / ".cache/orquidea/undo")

    @staticmethod
    def _trash_roots() -> list[Path]:
        roots = [Path.home() / ".local/share/Trash"]
        uid = os.getuid()
        try:
            for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
                fields = line.split()
                mount_point = Path(fields[1].replace("\\040", " "))
                for candidate in (mount_point / f".Trash-{uid}", mount_point / ".Trash" / str(uid)):
                    if candidate not in roots:
                        roots.append(candidate)
        except FileNotFoundError:
            pass
        return roots

    @classmethod
    def _find_trash_destination(cls, original: Path) -> Path:
        for root in cls._trash_roots():
            info_directory = root / "info"
            if not info_directory.is_dir():
                continue
            for info_path in info_directory.glob("*.trashinfo"):
                for line in info_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("Path=") and Path(unquote(line[5:])) == original:
                        return root / "files" / info_path.name.removesuffix(".trashinfo")
        raise FileNotFoundError(f"could not locate trashed file for {original}")

    def _write_manifest(self, manifest_path: Path, manifest: dict[str, object]) -> None:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.chmod(0o600)

    def safe_delete(self, paths: list[str]) -> Path:
        originals = [Path(path).expanduser().resolve(strict=True) for path in paths]
        if not originals:
            raise ValueError("at least one path is required")
        if len(set(originals)) != len(originals):
            raise ValueError("duplicate paths are not allowed")

        self.undo_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        manifest_path = self.undo_directory / f"{time.time_ns()}.json"
        manifest: dict[str, object] = {
            "entries": [
                {"origem": str(path), "destino": None, "restaurado": False}
                for path in originals
            ]
        }
        self._write_manifest(manifest_path, manifest)

        for index, original in enumerate(originals):
            send2trash(str(original))
            try:
                destination = self._find_trash_destination(original)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"file was sent to Trash but its destination could not be recorded; "
                    f"see manifest {manifest_path}"
                ) from exc
            manifest["entries"][index]["destino"] = str(destination)
            self._write_manifest(manifest_path, manifest)
        return manifest_path

    def undo(self, manifest_path: str | Path | None = None) -> list[str]:
        if manifest_path is None:
            manifests = sorted(self.undo_directory.glob("*.json"))
            if not manifests:
                return []
            selected_manifest = manifests[-1]
        else:
            selected_manifest = Path(manifest_path).expanduser()
        selected_manifest = selected_manifest.resolve(strict=True)
        try:
            selected_manifest.relative_to(self.undo_directory.resolve(strict=True))
        except ValueError as exc:
            raise ValueError("undo manifest must be inside the undo directory") from exc

        manifest = json.loads(selected_manifest.read_text(encoding="utf-8"))
        restored: list[str] = []
        for entry in manifest["entries"]:
            destination = entry["destino"]
            if entry.get("restaurado") or destination is None:
                continue
            trash_path = Path(destination).resolve(strict=True)
            if not any(trash_path.is_relative_to(root.resolve()) for root in self._trash_roots()):
                raise ValueError("undo destination must be inside a Trash directory")
            original = Path(entry["origem"]).expanduser().resolve()
            if original.exists():
                raise FileExistsError(original)
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_path), str(original))
            entry["restaurado"] = True
            restored.append(str(original))
            self._write_manifest(selected_manifest, manifest)
        return restored