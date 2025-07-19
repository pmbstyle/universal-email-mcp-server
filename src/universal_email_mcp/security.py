"""Security utilities for encrypted configuration storage and secure credential management."""

import base64
import os
from pathlib import Path
from typing import Any

import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureStore:
    """Manages encrypted storage of sensitive configuration data."""

    SERVICE_NAME = "universal-email-mcp"
    MASTER_KEY_NAME = "master-key"

    def __init__(self):
        self.cipher_suite = self._get_or_create_cipher_suite()

    def _get_or_create_cipher_suite(self) -> Fernet:
        """Get or create a Fernet cipher suite for encryption."""
        master_key = keyring.get_password(self.SERVICE_NAME, self.MASTER_KEY_NAME)

        if master_key is None:
            master_key = Fernet.generate_key().decode()
            keyring.set_password(
                self.SERVICE_NAME,
                self.MASTER_KEY_NAME,
                master_key
            )

        return Fernet(master_key.encode())

    def encrypt_data(self, data: str | dict) -> str:
        """Encrypt sensitive data."""
        if isinstance(data, dict):
            import json
            data_str = json.dumps(data)
        else:
            data_str = str(data)

        encrypted = self.cipher_suite.encrypt(data_str.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_data(self, encrypted_data: str) -> str | dict:
        """Decrypt sensitive data."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(encrypted_bytes)
            data_str = decrypted.decode()

            if data_str.startswith('{"') or data_str.startswith('[{'):
                import json
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    return data_str
            return data_str
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")

    def store_secure_string(self, key: str, value: str) -> None:
        """Store a secure string in the system keyring."""
        keyring.set_password(self.SERVICE_NAME, key, value)

    def get_secure_string(self, key: str) -> str | None:
        """Retrieve a secure string from the system keyring."""
        return keyring.get_password(self.SERVICE_NAME, key)

    def delete_secure_string(self, key: str) -> bool:
        """Delete a secure string from the system keyring."""
        try:
            from keyring.errors import PasswordDeleteError
            keyring.delete_password(self.SERVICE_NAME, key)
            return True
        except PasswordDeleteError:
            return False

    def clear_all_secrets(self) -> None:
        """Clear all stored secrets (primarily for testing)."""
        try:
            if hasattr(keyring, 'get_keyring'):
                backend = keyring.get_keyring()
                if hasattr(backend, 'clear_passwords'):
                    backend.clear_passwords()
        except (AttributeError, NotImplementedError):
            pass


def generate_key_from_password(password: str, salt: bytes) -> bytes:
    """Generate a Fernet key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


class SecureConfigManager:
    """Manages encrypted configuration with secure credential storage."""

    def __init__(self):
        self.secure_store = SecureStore()
        self.salt_file = Path.home() / ".local" / "share" / "universal-email-mcp" / "salt"
        self.salt_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_or_create_salt(self) -> bytes:
        """Get or create a salt for password-based key derivation."""
        if self.salt_file.exists():
            return self.salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            self.salt_file.write_bytes(salt)
            return salt

    def encrypt_account_credentials(self, account_data: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive parts of account credentials."""
        encrypted_data = account_data.copy()

        if 'incoming' in encrypted_data and 'password' in encrypted_data['incoming']:
            encrypted_data['incoming']['password'] = self.secure_store.encrypt_data(
                encrypted_data['incoming']['password']
            )

        if 'outgoing' in encrypted_data and 'password' in encrypted_data['outgoing']:
            encrypted_data['outgoing']['password'] = self.secure_store.encrypt_data(
                encrypted_data['outgoing']['password']
            )

        return encrypted_data

    def decrypt_account_credentials(self, account_data: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive parts of account credentials."""
        decrypted_data = account_data.copy()

        if 'incoming' in decrypted_data and 'password' in decrypted_data['incoming']:
            decrypted_data['incoming']['password'] = self.secure_store.decrypt_data(
                decrypted_data['incoming']['password']
            )

        if 'outgoing' in decrypted_data and 'password' in decrypted_data['outgoing']:
            decrypted_data['outgoing']['password'] = self.secure_store.decrypt_data(
                decrypted_data['outgoing']['password']
            )

        return decrypted_data


secure_config = SecureConfigManager()
