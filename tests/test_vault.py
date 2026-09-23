import json
import stat

import pytest
from cryptography.exceptions import InvalidTag

from agent.tools.vault import LocalVault, SSHAuditor


def test_audit_detects_unsafe_ssh_permissions(tmp_path) -> None:
    ssh_directory = tmp_path / ".ssh"
    ssh_directory.mkdir(mode=0o755)
    key_path = ssh_directory / "id_ed25519"
    key_path.write_text("private key", encoding="utf-8")
    key_path.chmod(0o644)
    ssh_directory.chmod(0o755)
    auditor = SSHAuditor(ssh_directory)

    diagnostics = auditor.audit()

    assert diagnostics == [
        {
            "path": str(ssh_directory),
            "current_mode": "0755",
            "expected_mode": "0700",
            "status": "vulnerable",
        },
        {
            "path": str(key_path),
            "current_mode": "0644",
            "expected_mode": "0600",
            "status": "vulnerable",
        },
    ]


def test_fix_permissions_secures_ssh_directory_and_private_keys(tmp_path) -> None:
    ssh_directory = tmp_path / ".ssh"
    ssh_directory.mkdir(mode=0o755)
    key_path = ssh_directory / "id_rsa"
    key_path.write_text("private key", encoding="utf-8")
    key_path.chmod(0o644)
    public_key = ssh_directory / "id_rsa.pub"
    public_key.write_text("public key", encoding="utf-8")
    public_key.chmod(0o644)
    ssh_directory.chmod(0o755)
    auditor = SSHAuditor(ssh_directory)

    auditor.fix_permissions()

    assert stat.S_IMODE(ssh_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_key.stat().st_mode) == 0o644
    assert all(item["status"] == "secure" for item in auditor.audit())


def test_fix_permissions_ignores_symlinked_private_keys(tmp_path) -> None:
    ssh_directory = tmp_path / ".ssh"
    ssh_directory.mkdir(mode=0o700)
    outside_key = tmp_path / "outside_key"
    outside_key.write_text("private key", encoding="utf-8")
    outside_key.chmod(0o644)
    (ssh_directory / "id_ed25519").symlink_to(outside_key)
    auditor = SSHAuditor(ssh_directory)

    assert len(auditor.audit()) == 1
    auditor.fix_permissions()

    assert stat.S_IMODE(outside_key.stat().st_mode) == 0o644


def test_audit_reports_secure_permissions(tmp_path) -> None:
    ssh_directory = tmp_path / ".ssh"
    ssh_directory.mkdir(mode=0o700)
    key_path = ssh_directory / "id_ecdsa"
    key_path.write_text("private key", encoding="utf-8")
    key_path.chmod(0o600)
    ssh_directory.chmod(0o700)

    diagnostics = SSHAuditor(ssh_directory).audit()

    assert [item["status"] for item in diagnostics] == ["secure", "secure"]


def test_local_vault_encrypts_and_decrypts_secret(tmp_path) -> None:
    vault_path = tmp_path / "vault.json"
    vault = LocalVault(vault_path)

    vault.store_secret("mail", "sensitive value", "correct password")

    assert vault.get_secret("mail", "correct password") == "sensitive value"
    assert vault.list_keys() == ["mail"]
    assert "sensitive value" not in vault_path.read_text(encoding="utf-8")
    assert stat.S_IMODE(vault_path.stat().st_mode) == 0o600


def test_local_vault_rejects_wrong_password(tmp_path) -> None:
    vault = LocalVault(tmp_path / "vault.json")
    vault.store_secret("mail", "sensitive value", "correct password")

    with pytest.raises(InvalidTag):
        vault.get_secret("mail", "wrong password")


def test_local_vault_rejects_wrong_password_when_storing(tmp_path) -> None:
    vault = LocalVault(tmp_path / "vault.json")
    vault.store_secret("mail", "sensitive value", "correct password")

    with pytest.raises(InvalidTag):
        vault.store_secret("calendar", "calendar secret", "wrong password")

    assert vault.list_keys() == ["mail"]



def test_local_vault_raises_for_unknown_key(tmp_path) -> None:
    vault = LocalVault(tmp_path / "vault.json")
    vault.store_secret("mail", "sensitive value", "correct password")

    with pytest.raises(KeyError):
        vault.get_secret("calendar", "correct password")


def test_local_vault_lists_only_secret_labels(tmp_path) -> None:
    vault_path = tmp_path / "nested" / "vault.json"
    vault = LocalVault(vault_path)
    vault.store_secret("mail", "mail secret", "master password")
    vault.store_secret("calendar", "calendar secret", "master password")

    assert vault.list_keys() == ["calendar", "mail"]
    stored_data = json.loads(vault_path.read_text(encoding="utf-8"))
    assert set(stored_data) == {"salt", "secrets"}
    assert set(stored_data["secrets"]) == {"calendar", "mail"}
