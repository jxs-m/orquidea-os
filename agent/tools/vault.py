import base64
import json
import os
import secrets
import stat
import tempfile
from pathlib import Path
from typing import Literal, TypedDict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SSHDiagnostic(TypedDict):
    path: str
    current_mode: str
    expected_mode: str
    status: Literal["secure", "vulnerable"]


class SSHAuditor:
    PRIVATE_KEY_NAMES = {"id_rsa", "id_ed25519", "id_ecdsa"}

    def __init__(self, ssh_directory: str | Path | None = None) -> None:
        self.ssh_directory = Path(ssh_directory or Path.home() / ".ssh")

    def _private_keys(self) -> list[Path]:
        return sorted(
            path
            for path in self.ssh_directory.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and path.name.startswith("id_")
            and not path.name.endswith(".pub")
        )

    def audit(self) -> list[SSHDiagnostic]:
        diagnostics: list[SSHDiagnostic] = []
        directory_mode = stat.S_IMODE(self.ssh_directory.stat().st_mode)
        diagnostics.append(
            {
                "path": str(self.ssh_directory),
                "current_mode": f"{directory_mode:04o}",
                "expected_mode": "0700",
                "status": "secure" if directory_mode == 0o700 else "vulnerable",
            }
        )
        for key_path in self._private_keys():
            key_mode = stat.S_IMODE(key_path.stat().st_mode)
            diagnostics.append(
                {
                    "path": str(key_path),
                    "current_mode": f"{key_mode:04o}",
                    "expected_mode": "0600",
                    "status": "secure" if key_mode == 0o600 else "vulnerable",
                }
            )
        return diagnostics

    def fix_permissions(self) -> None:
        self.ssh_directory.chmod(0o700)
        for key_path in self._private_keys():
            key_path.chmod(0o600)


class LocalVault:
    ITERATIONS = 100_000
    SALT_SIZE = 16
    NONCE_SIZE = 12
    KEY_SIZE = 32

    def __init__(self, vault_path: str | Path) -> None:
        self.vault_path = Path(vault_path)

    @staticmethod
    def _derive_key(master_password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=LocalVault.KEY_SIZE,
            salt=salt,
            iterations=LocalVault.ITERATIONS,
        )
        return kdf.derive(master_password.encode("utf-8"))

    def _read_data(self) -> dict[str, object] | None:
        if self.vault_path.is_symlink():
            raise ValueError("Vault path must not be a symlink")
        try:
            with self.vault_path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except FileNotFoundError:
            return None
        if not isinstance(data, dict):
            raise ValueError("Invalid vault format")
        salt = data.get("salt")
        entries = data.get("secrets")
        if not isinstance(salt, str) or not isinstance(entries, dict):
            raise ValueError("Invalid vault format")
        try:
            if len(base64.b64decode(salt, validate=True)) != self.SALT_SIZE:
                raise ValueError("Invalid vault format")
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("Invalid vault format") from exc
        for name, entry in entries.items():
            if not isinstance(name, str) or not isinstance(entry, dict):
                raise ValueError("Invalid vault format")
            nonce = entry.get("nonce")
            ciphertext = entry.get("ciphertext")
            if not isinstance(nonce, str) or not isinstance(ciphertext, str):
                raise ValueError("Invalid vault format")
            try:
                if len(base64.b64decode(nonce, validate=True)) != self.NONCE_SIZE:
                    raise ValueError("Invalid vault format")
                base64.b64decode(ciphertext, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                raise ValueError("Invalid vault format") from exc
        return data

    def _write_data(self, data: dict[str, object]) -> None:
        if self.vault_path.is_symlink():
            raise ValueError("Vault path must not be a symlink")
        self.vault_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(dir=self.vault_path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(data, stream, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.vault_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def store_secret(self, key_name: str, secret_value: str, master_password: str) -> None:
        data = self._read_data()
        if data is None:
            salt = secrets.token_bytes(self.SALT_SIZE)
            entries: dict[str, dict[str, str]] = {}
        else:
            salt = base64.b64decode(data["salt"])
            entries = data["secrets"]

        encryption_key = self._derive_key(master_password, salt)
        if entries:
            existing_name, existing_entry = next(iter(entries.items()))
            AESGCM(encryption_key).decrypt(
                base64.b64decode(existing_entry["nonce"]),
                base64.b64decode(existing_entry["ciphertext"]),
                existing_name.encode("utf-8"),
            )

        nonce = secrets.token_bytes(self.NONCE_SIZE)
        ciphertext = AESGCM(encryption_key).encrypt(
            nonce,
            secret_value.encode("utf-8"),
            key_name.encode("utf-8"),
        )
        entries[key_name] = {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        self._write_data(
            {
                "salt": base64.b64encode(salt).decode("ascii"),
                "secrets": entries,
            }
        )

    def get_secret(self, key_name: str, master_password: str) -> str:
        data = self._read_data()
        if data is None:
            raise KeyError(key_name)
        entries = data["secrets"]
        if key_name not in entries:
            raise KeyError(key_name)

        salt = base64.b64decode(data["salt"])
        entry = entries[key_name]
        encryption_key = self._derive_key(master_password, salt)
        plaintext = AESGCM(encryption_key).decrypt(
            base64.b64decode(entry["nonce"]),
            base64.b64decode(entry["ciphertext"]),
            key_name.encode("utf-8"),
        )
        return plaintext.decode("utf-8")

    def list_keys(self) -> list[str]:
        data = self._read_data()
        if data is None:
            return []
        return sorted(data["secrets"])
