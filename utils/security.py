"""Secrets are encrypted; random recovery tokens are stored only as hashes."""
import hashlib
import hmac
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet


class SecretBox:
    def __init__(self, key: str | bytes):
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, text: str) -> str:
        return self.cipher.decrypt(text.encode()).decode()


def encryption_box(env_file: Path, *, allow_create=False) -> SecretBox:
    key = os.getenv("APP_ENCRYPTION_KEY")
    if not key:
        if not allow_create:
            raise ValueError("APP_ENCRYPTION_KEY is missing. Restore the original key from your secure copy.")
        from dotenv import dotenv_values
        content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        key = dotenv_values(env_file).get("APP_ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            with env_file.open("a", encoding="utf-8") as handle:
                handle.write(("" if content.endswith("\n") else "\n") + "APP_ENCRYPTION_KEY=" + key + "\n")
        os.environ["APP_ENCRYPTION_KEY"] = key
    return SecretBox(key)


def recovery_hash(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def recovery_codes(count=10) -> list[str]:
    return [secrets.token_hex(16).upper() for _ in range(count)]


def matches_recovery(code: str, stored: str) -> bool:
    return hmac.compare_digest(recovery_hash(code), stored)
