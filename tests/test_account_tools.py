"""Tests for account management tools."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from universal_email_mcp import config, models
from universal_email_mcp.tools import account


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_settings():
    """Create a mock settings instance for testing."""
    settings = config.Settings()
    return settings


@pytest.fixture
def clean_settings(temp_config_file, mock_settings):
    """Reset settings singleton for each test."""
    with patch.object(config, 'CONFIG_PATH', temp_config_file):
        with patch('universal_email_mcp.config.get_settings') as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            with patch('universal_email_mcp.tools.account.config.get_settings') as mock_get_settings2:
                mock_get_settings2.return_value = mock_settings
                yield mock_settings


@pytest.mark.asyncio
async def test_add_account_success(clean_settings):
    """Test successfully adding a new account."""
    input_data = models.AddAccountInput(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        user_name="testuser",
        password="testpass",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    result = await account.add_account(input_data)
    
    assert result.status == "success"
    assert "test_account" in result.details
    
    # Verify account was actually added
    assert len(clean_settings.accounts) == 1
    assert clean_settings.accounts[0].account_name == "test_account"
    assert clean_settings.accounts[0].email_address == "test@example.com"


@pytest.mark.asyncio
async def test_add_account_duplicate(clean_settings):
    """Test adding an account with duplicate name."""
    input_data = models.AddAccountInput(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        user_name="testuser",
        password="testpass",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    # Add account first time
    await account.add_account(input_data)
    
    # Try to add same account again
    result = await account.add_account(input_data)
    
    assert result.status == "error"
    assert "already exists" in result.details


@pytest.mark.asyncio
async def test_list_accounts_empty():
    """Test listing accounts when none are configured."""
    with patch('universal_email_mcp.tools.account.config.get_settings') as mock_get_settings:
        mock_settings = config.Settings()
        mock_get_settings.return_value = mock_settings
        
        result = await account.list_accounts()
        
        assert isinstance(result, models.ListAccountsOutput)
        assert result.accounts == []


@pytest.mark.asyncio
async def test_list_accounts_with_data(clean_settings):
    """Test listing accounts when some are configured."""
    # Add two accounts
    input_data1 = models.AddAccountInput(
        account_name="account1",
        full_name="User One",
        email_address="user1@example.com",
        user_name="user1",
        password="pass1",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    input_data2 = models.AddAccountInput(
        account_name="account2",
        full_name="User Two",
        email_address="user2@example.com",
        user_name="user2",
        password="pass2",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    await account.add_account(input_data1)
    await account.add_account(input_data2)
    
    result = await account.list_accounts()
    
    assert len(result.accounts) == 2
    assert "account1" in result.accounts
    assert "account2" in result.accounts


@pytest.mark.asyncio
async def test_remove_account_success(clean_settings):
    """Test successfully removing an account."""
    # First add an account
    input_data = models.AddAccountInput(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        user_name="testuser",
        password="testpass",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    await account.add_account(input_data)
    
    # Now remove it
    remove_data = models.RemoveAccountInput(account_name="test_account")
    result = await account.remove_account(remove_data)
    
    assert result.status == "success"
    assert "removed successfully" in result.details
    
    # Verify account was actually removed
    assert len(clean_settings.accounts) == 0


@pytest.mark.asyncio
async def test_remove_account_not_found():
    """Test removing an account that doesn't exist."""
    with patch('universal_email_mcp.tools.account.config.get_settings') as mock_get_settings:
        mock_settings = config.Settings()
        mock_get_settings.return_value = mock_settings
        
        remove_data = models.RemoveAccountInput(account_name="nonexistent")
        result = await account.remove_account(remove_data)
        
        assert result.status == "error"
        assert "not found" in result.details


@pytest.mark.asyncio
async def test_get_account_settings_success(clean_settings):
    """Test getting account settings for existing account."""
    # Add an account
    input_data = models.AddAccountInput(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        user_name="testuser",
        password="testpass",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com"
    )
    
    await account.add_account(input_data)
    
    # Get account settings
    settings = account.get_account_settings("test_account")
    
    assert settings.account_name == "test_account"
    assert settings.email_address == "test@example.com"
    assert settings.incoming.host == "imap.example.com"
    assert settings.outgoing.host == "smtp.example.com"


@pytest.mark.asyncio
async def test_get_account_settings_not_found():
    """Test getting account settings for non-existent account."""
    with patch('universal_email_mcp.tools.account.config.get_settings') as mock_get_settings:
        mock_settings = config.Settings()
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(ValueError, match="Account 'nonexistent' not found"):
            account.get_account_settings("nonexistent")


@pytest.mark.asyncio
async def test_account_with_custom_ports(clean_settings):
    """Test adding account with custom IMAP/SMTP ports."""
    input_data = models.AddAccountInput(
        account_name="custom_ports",
        full_name="Custom User",
        email_address="custom@example.com",
        user_name="customuser",
        password="custompass",
        imap_host="imap.example.com",
        imap_port=143,
        imap_use_ssl=False,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_use_ssl=False
    )
    
    result = await account.add_account(input_data)
    assert result.status == "success"
    
    settings = account.get_account_settings("custom_ports")
    assert settings.incoming.port == 143
    assert settings.incoming.use_ssl is False
    assert settings.outgoing.port == 587
    assert settings.outgoing.use_ssl is False