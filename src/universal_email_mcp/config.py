"""Configuration management for Universal Email MCP Server."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import tomli
import tomli_w
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_PATH = Path("~/.config/universal_email_mcp/config.toml").expanduser()


class EmailServer(BaseModel):
    """Email server configuration for IMAP or SMTP."""
    
    user_name: str
    password: str
    host: str
    port: int
    use_ssl: bool = True
    verify_ssl: bool = True


class EmailSettings(BaseModel):
    """Complete email account configuration."""
    
    account_name: str = Field(..., description="A unique name for this account.")
    full_name: str
    email_address: str
    incoming: EmailServer
    outgoing: EmailServer


class Settings(BaseSettings):
    """Application settings loaded from config file."""
    
    model_config = SettingsConfigDict(
        toml_file=CONFIG_PATH,
        env_prefix="UNIVERSAL_EMAIL_MCP_",
        case_sensitive=False,
    )
    
    accounts: List[EmailSettings] = Field(default_factory=list)

    def store(self) -> None:
        """Store settings to the configuration file."""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"accounts": [acc.model_dump() for acc in self.accounts]}
        
        with open(CONFIG_PATH, "wb") as f:
            tomli_w.dump(data, f)

    def get_account(self, account_name: str) -> Optional[EmailSettings]:
        """Get account settings by name."""
        for account in self.accounts:
            if account.account_name == account_name:
                return account
        return None

    def add_account(self, account: EmailSettings) -> None:
        """Add a new account or update existing one."""
        self.accounts = [acc for acc in self.accounts if acc.account_name != account.account_name]
        self.accounts.append(account)

    def remove_account(self, account_name: str) -> bool:
        """Remove an account by name. Returns True if removed, False if not found."""
        initial_count = len(self.accounts)
        self.accounts = [acc for acc in self.accounts if acc.account_name != account_name]
        return len(self.accounts) < initial_count


_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Get the global settings instance."""
    global _settings
    
    if _settings is None or reload:
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'rb') as f:
                    data = tomli.load(f)
                _settings = Settings(**data)
            else:
                _settings = Settings()
        except Exception:
            _settings = Settings()
    
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance. Useful for testing."""
    global _settings
    _settings = None