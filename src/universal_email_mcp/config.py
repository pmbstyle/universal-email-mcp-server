from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import tomli_w
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_PATH = Path("~/.config/universal_email_mcp/config.toml").expanduser()


class EmailServer(BaseModel):

    user_name: str
    password: str
    host: str
    port: int
    use_ssl: bool = True
    verify_ssl: bool = True


class EmailSettings(BaseModel):

    account_name: str = Field(..., description="A unique name for this account.")
    full_name: str
    email_address: str
    incoming: EmailServer
    outgoing: EmailServer


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        toml_file=CONFIG_PATH,
        env_prefix="UNIVERSAL_EMAIL_MCP_",
        case_sensitive=False,
    )

    accounts: list[EmailSettings] = Field(default_factory=list)

    def store(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"accounts": [acc.model_dump() for acc in self.accounts]}

        with open(CONFIG_PATH, "wb") as f:
            tomli_w.dump(data, f)

    def get_account(self, account_name: str) -> EmailSettings | None:
        for account in self.accounts:
            if account.account_name == account_name:
                return account
        return None

    def add_account(self, account: EmailSettings) -> None:
        self.accounts = [acc for acc in self.accounts if acc.account_name != account.account_name]
        self.accounts.append(account)

    def remove_account(self, account_name: str) -> bool:
        initial_count = len(self.accounts)
        self.accounts = [acc for acc in self.accounts if acc.account_name != account_name]
        return len(self.accounts) < initial_count


class SecureConfigStore:

    _encryption_key: bytes | None = None

    def __init__(self) -> None:
        self._key_path = CONFIG_PATH.parent / "encryption.key"
        self._setup_encryption_key()

    def _setup_encryption_key(self) -> None:
        # First, try to get key from system keyring
        try:
            import keyring
            key_b64 = keyring.get_password("universal_email_mcp", "encryption_key")
            if key_b64:
                self._encryption_key = base64.urlsafe_b64decode(key_b64.encode())
                return
        except ImportError:
            pass  # keyring not available
        except Exception:
            pass  # keyring setup issue

        # Try file-based key storage
        if self._key_path.exists():
            try:
                with open(self._key_path, "rb") as f:
                    self._encryption_key = f.read()
                return
            except Exception:
                pass

        # Generate new key
        self._encryption_key = Fernet.generate_key()
        self._save_encryption_key()

    def _save_encryption_key(self) -> None:
        if self._encryption_key is None:
            raise ValueError("No encryption key available")

        # Try keyring first
        try:
            import keyring
            key_b64 = base64.urlsafe_b64encode(self._encryption_key).decode()
            keyring.set_password("universal_email_mcp", "encryption_key", key_b64)
            return
        except Exception:
            pass

        # Fallback to file storage
        try:
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._key_path, "wb") as f:
                f.write(self._encryption_key)
            # Make key file readable only by owner
            os.chmod(self._key_path, 0o600)
        except Exception as e:
            raise RuntimeError(f"Failed to save encryption key: {e}")

    def encrypt_data(self, data: dict) -> str:
        if self._encryption_key is None:
            raise ValueError("No encryption key available")

        fernet = Fernet(self._encryption_key)
        json_data = json.dumps(data, separators=(',', ':'), sort_keys=True)
        encrypted = fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_data(self, encrypted_data: str) -> dict:
        if self._encryption_key is None:
            raise ValueError("No encryption key available")

        try:
            fernet = Fernet(self._encryption_key)
            encrypted = base64.b64decode(encrypted_data.encode())
            decrypted = fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except (InvalidToken, ValueError) as e:
            raise ValueError("Failed to decrypt configuration data") from e


class SecureSettings(Settings):

    _secure_store = None
    _cache = {}
    _cache_ttl = 30  # seconds

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self._secure_store is None:
            SecureSettings._secure_store = SecureConfigStore()

    def store(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Prepare data for encryption
        data = {"accounts": [acc.model_dump() for acc in self.accounts]}
        if self._secure_store is None:
            self._secure_store = SecureConfigStore()
        encrypted_data = self._secure_store.encrypt_data(data)

        # Store encrypted data
        with open(CONFIG_PATH, "w") as f:
            json.dump({"encrypted": True, "data": encrypted_data}, f)

        # Invalidate cache
        cache_key = str(CONFIG_PATH)
        if cache_key in self._cache:
            del self._cache[cache_key]

    @classmethod
    def load_secure(cls) -> SecureSettings:
        import time
        current_time = time.time()
        cache_key = str(CONFIG_PATH)

        # Check cache validity
        if cache_key in cls._cache:
            cached_data, cache_timestamp = cls._cache[cache_key]
            if current_time - cache_timestamp < cls._cache_ttl:
                return cached_data

        if not CONFIG_PATH.exists():
            instance = cls()
            # Cache the empty instance
            cls._cache[cache_key] = (instance, current_time)
            return instance

        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)

            # Handle legacy unencrypted format
            if not cfg.get("encrypted", False):
                # Migrate legacy format to encrypted
                instance = cls(**cfg)
                # Store securely
                instance.store()
                cls._cache[cache_key] = (instance, current_time)
                return instance

            # Decrypt new format
            if cls._secure_store is None:
                cls._secure_store = SecureConfigStore()
            decrypted_data = cls._secure_store.decrypt_data(cfg["data"])
            instance = cls(**decrypted_data)
            cls._cache[cache_key] = (instance, current_time)
            return instance

        except (FileNotFoundError, ValueError):
            # Migration or corruption - start fresh
            instance = cls()
            cls._cache[cache_key] = (instance, current_time)
            return instance
        except Exception:
            instance = cls()
            cls._cache[cache_key] = (instance, current_time)
            return instance


_settings: SecureSettings | None = None


def get_settings(reload: bool = False) -> SecureSettings:
    global _settings

    if _settings is None or reload:
        try:
            _settings = SecureSettings.load_secure()
        except Exception:
            _settings = SecureSettings()

    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
