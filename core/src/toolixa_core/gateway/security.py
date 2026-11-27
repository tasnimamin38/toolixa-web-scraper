"""Encryption, authentication, and endpoint validation for the local gateway."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from cryptography.fernet import Fernet, InvalidToken


class VaultError(RuntimeError):
    """Raised when local encrypted credentials cannot be opened safely."""


class SecretVault:
    """Encrypt provider credentials with a key kept outside the repository."""

    def __init__(self, key: bytes) -> None:
        try:
            self._fernet = Fernet(key)
            self._signing_key = base64.urlsafe_b64decode(key)
        except (ValueError, TypeError) as exc:
            raise VaultError("the local vault key is invalid") from exc

    @classmethod
    def from_file(cls, path: Path) -> SecretVault:
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            key = path.read_bytes()
        except FileNotFoundError:
            key = Fernet.generate_key()
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                key = path.read_bytes()
            else:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(key)
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass
        return cls(key)

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError, ValueError) as exc:
            raise VaultError("stored provider credential could not be decrypted") from exc

    def sign(self, message: str) -> str:
        return hmac.new(self._signing_key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if len(password) < 12:
        raise ValueError("dashboard password must be at least 12 characters")
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt_bytes, n=2**14, r=8, p=1, dklen=32)
    return base64.b64encode(salt_bytes).decode("ascii"), base64.b64encode(digest).decode("ascii")


def verify_password(password: str, salt_b64: str, digest_b64: str) -> bool:
    try:
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(digest_b64, validate=True)
    except (ValueError, TypeError):
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, expected)


def issue_session(vault: SecretVault, *, lifetime_seconds: int = 43_200) -> str:
    expires = int(time.time()) + lifetime_seconds
    return f"{expires}.{vault.sign(f'toolixa-session:{expires}')}"


def verify_session(vault: SecretVault, token: str | None) -> bool:
    if not token:
        return False
    try:
        expires_text, signature = token.split(".", maxsplit=1)
        expires = int(expires_text)
    except (ValueError, TypeError):
        return False
    if expires < int(time.time()) or expires > int(time.time()) + 43_200:
        return False
    expected = vault.sign(f"toolixa-session:{expires}")
    return hmac.compare_digest(signature, expected)


def create_api_token() -> str:
    return f"tla_{secrets.token_urlsafe(32)}"


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_base_url(value: str) -> str:
    """Accept HTTPS endpoints and plain HTTP only for the local machine."""
    candidate = value.strip()
    if not candidate or any(ord(char) < 32 for char in candidate):
        raise ValueError("provider URL is required and must not contain control characters")
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("provider URL must be an absolute HTTP(S) API base URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("provider URL cannot contain credentials, query strings, or fragments")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("provider URL contains an invalid port") from exc

    host = parsed.hostname.rstrip(".").lower()
    loopback_names = {"localhost", "localhost.localdomain"}
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    is_loopback = host in loopback_names or (address is not None and address.is_loopback)
    if parsed.scheme == "http" and not is_loopback:
        raise ValueError("plain HTTP is allowed only for localhost or loopback model servers")
    if address is not None and not address.is_global and not is_loopback:
        raise ValueError("non-public IP addresses are not allowed as remote provider endpoints")

    normalized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    return normalized
