"""SQLite-backed local storage for providers, API keys, and dashboard auth."""

from __future__ import annotations

import hmac
import json
import re
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from toolixa_core.gateway.security import (
    SecretVault,
    create_api_token,
    hash_api_token,
    hash_password,
    validate_base_url,
    verify_password,
)


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    id: str
    name: str
    base_url: str
    models: tuple[str, ...]
    created_at: str


class GatewayStore:
    """Store provider metadata and encrypted secrets in a local SQLite DB."""

    def __init__(self, db_path: Path, vault: SecretVault) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault = vault
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS providers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    base_url TEXT NOT NULL,
                    encrypted_api_key TEXT NOT NULL DEFAULT '',
                    models_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_keys (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    prefix TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        if not slug:
            raise ValueError("provider name must contain letters or numbers")
        return slug[:48]

    def add_provider(
        self, *, name: str, base_url: str, api_key: str = "", models: list[str] | None = None
    ) -> ProviderRecord:
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 80:
            raise ValueError("provider name must contain 1 to 80 characters")
        clean_url = validate_base_url(base_url)
        normalized_models = tuple(
            dict.fromkeys(item.strip() for item in (models or []) if item.strip())
        )
        if len(normalized_models) > 300:
            raise ValueError("a provider can define at most 300 models")
        provider_id = self._slug(clean_name)
        created_at = self._now()
        encrypted_key = self.vault.encrypt(api_key.strip())
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT 1 FROM providers WHERE id = ?", (provider_id,)
            ).fetchone()
            suffix = 2
            while existing is not None:
                provider_id = f"{self._slug(clean_name)[:43]}-{suffix}"
                existing = connection.execute(
                    "SELECT 1 FROM providers WHERE id = ?", (provider_id,)
                ).fetchone()
                suffix += 1
            try:
                connection.execute(
                    "INSERT INTO providers(id, name, base_url, encrypted_api_key, models_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        provider_id,
                        clean_name,
                        clean_url,
                        encrypted_key,
                        json.dumps(normalized_models),
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("a provider with this display name already exists") from exc
        return ProviderRecord(provider_id, clean_name, clean_url, normalized_models, created_at)

    @staticmethod
    def _provider_from_row(row: sqlite3.Row) -> ProviderRecord:
        return ProviderRecord(
            id=row["id"],
            name=row["name"],
            base_url=row["base_url"],
            models=tuple(json.loads(row["models_json"])),
            created_at=row["created_at"],
        )

    def list_providers(self) -> list[ProviderRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, base_url, models_json, created_at FROM providers ORDER BY name"
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def get_provider(self, provider_id: str) -> ProviderRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, base_url, models_json, created_at FROM providers WHERE id = ?",
                (provider_id,),
            ).fetchone()
        return self._provider_from_row(row) if row else None

    def get_provider_secret(self, provider_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT encrypted_api_key FROM providers WHERE id = ?", (provider_id,)
            ).fetchone()
        if row is None:
            raise KeyError(provider_id)
        return self.vault.decrypt(row["encrypted_api_key"])

    def update_provider_models(self, provider_id: str, models: list[str]) -> None:
        normalized = tuple(dict.fromkeys(item.strip() for item in models if item.strip()))
        if len(normalized) > 300:
            raise ValueError("a provider can expose at most 300 models")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE providers SET models_json = ? WHERE id = ?",
                (json.dumps(normalized), provider_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(provider_id)

    def delete_provider(self, provider_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
        return cursor.rowcount > 0

    def create_api_key(self, name: str) -> str:
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 80:
            raise ValueError("API key name must contain 1 to 80 characters")
        token = create_api_token()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO gateway_keys(id, name, prefix, token_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    secrets.token_hex(8),
                    clean_name,
                    token[:12],
                    hash_api_token(token),
                    self._now(),
                ),
            )
        return token

    def authenticate_api_key(self, token: str) -> bool:
        if not token or len(token) > 256:
            return False
        token_hash = hash_api_token(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, token_hash FROM gateway_keys WHERE revoked = 0 AND token_hash = ?",
                (token_hash,),
            ).fetchone()
            if row is None or not hmac.compare_digest(row["token_hash"], token_hash):
                return False
            connection.execute(
                "UPDATE gateway_keys SET last_used_at = ? WHERE id = ?",
                (self._now(), row["id"]),
            )
        return True

    def list_api_keys(self) -> list[dict[str, str | bool | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, prefix, created_at, revoked, last_used_at "
                "FROM gateway_keys ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def revoke_api_key(self, key_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE gateway_keys SET revoked = 1 WHERE id = ? AND revoked = 0", (key_id,)
            )
        return cursor.rowcount > 0

    def has_admin_password(self) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = 'admin_password_hash'"
            ).fetchone()
        return row is not None

    def set_admin_password(self, password: str) -> None:
        salt, digest = hash_password(password)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES('admin_password_salt', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (salt,),
            )
            connection.execute(
                "INSERT INTO settings(key, value) VALUES('admin_password_hash', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (digest,),
            )

    def verify_admin_password(self, password: str) -> bool:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM settings WHERE key IN "
                "('admin_password_salt', 'admin_password_hash')"
            ).fetchall()
        values = {row["key"]: row["value"] for row in rows}
        salt = values.get("admin_password_salt")
        digest = values.get("admin_password_hash")
        return bool(salt and digest and verify_password(password, salt, digest))

    def create_admin_password_if_missing(self) -> str | None:
        if self.has_admin_password():
            return None
        password = secrets.token_urlsafe(24)
        self.set_admin_password(password)
        return password
