"""Tests for email operation tools."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from universal_email_mcp import config, models
from universal_email_mcp.tools import account, mail


@pytest.fixture
def mock_account_settings():
    """Mock account settings for testing."""
    return config.EmailSettings(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        incoming=config.EmailServer(
            user_name="testuser",
            password="testpass",
            host="imap.example.com",
            port=993,
            use_ssl=True
        ),
        outgoing=config.EmailServer(
            user_name="testuser",
            password="testpass",
            host="smtp.example.com",
            port=465,
            use_ssl=True
        )
    )


@pytest.fixture
def mock_email_message():
    """Mock email message for testing."""
    return models.EmailMessage(
        uid="12345",
        subject="Test Subject",
        sender="sender@example.com",
        body="Test email body content",
        date=datetime(2024, 1, 15, 10, 30, 0),
        is_read=False,
        has_attachments=False
    )


class TestEmailClient:
    """Test the EmailClient class."""
    
    @pytest.mark.asyncio
    async def test_email_client_init(self, mock_account_settings):
        """Test EmailClient initialization."""
        client = mail.EmailClient(mock_account_settings)
        
        assert client.account_settings == mock_account_settings
        assert client._imap_client is None
        assert client._smtp_client is None
    
    @pytest.mark.asyncio
    async def test_email_client_context_manager(self, mock_account_settings):
        """Test EmailClient as context manager."""
        client = mail.EmailClient(mock_account_settings)
        
        async with client as c:
            assert c is client
        
        # close() should have been called
        assert client._imap_client is None
        assert client._smtp_client is None


class TestListMessages:
    """Test the list_messages tool."""
    
    @pytest.mark.asyncio
    async def test_list_messages_success(self, mock_account_settings, mock_email_message):
        """Test successful message listing."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                # Setup mock client
                mock_client = AsyncMock()
                mock_client.get_messages.return_value = ([mock_email_message], 1)
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.ListMessagesInput(account_name="test_account")
                result = await mail.list_messages(input_data)
                
                assert result.account_name == "test_account"
                assert result.mailbox == "INBOX"
                assert result.page == 1
                assert result.page_size == 10
                assert result.total_messages == 1
                assert len(result.messages) == 1
                assert result.messages[0].uid == "12345"
    
    @pytest.mark.asyncio
    async def test_list_messages_with_filters(self, mock_account_settings):
        """Test message listing with filters."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get_messages.return_value = ([], 0)
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.ListMessagesInput(
                    account_name="test_account",
                    subject_filter="Important",
                    sender_filter="boss@company.com",
                    unread_only=True
                )
                
                result = await mail.list_messages(input_data)
                
                # Verify the client was called with correct parameters
                mock_client.get_messages.assert_called_once()
                call_args = mock_client.get_messages.call_args[1]
                assert call_args['subject_filter'] == "Important"
                assert call_args['sender_filter'] == "boss@company.com"
                assert call_args['unread_only'] is True
    
    @pytest.mark.asyncio
    async def test_list_messages_account_not_found(self):
        """Test listing messages for non-existent account."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', side_effect=ValueError("Account not found")):
            input_data = models.ListMessagesInput(account_name="nonexistent")
            result = await mail.list_messages(input_data)
            
            assert result.total_messages == 0
            assert len(result.messages) == 0


class TestSendMessage:
    """Test the send_message tool."""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_account_settings):
        """Test successful message sending."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.SendMessageInput(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test body"
                )
                
                result = await mail.send_message(input_data)
                
                assert result.status == "success"
                assert "sent successfully" in result.details
                
                # Verify send_message was called
                mock_client.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_with_cc_bcc(self, mock_account_settings):
        """Test sending message with CC and BCC."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.SendMessageInput(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test body",
                    cc=["cc@example.com"],
                    bcc=["bcc@example.com"],
                    is_html=True
                )
                
                result = await mail.send_message(input_data)
                
                assert result.status == "success"
                
                # Verify parameters were passed correctly
                call_args = mock_client.send_message.call_args[1]
                assert call_args['cc'] == ["cc@example.com"]
                assert call_args['bcc'] == ["bcc@example.com"]
                assert call_args['is_html'] is True
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self, mock_account_settings):
        """Test message sending failure."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.send_message.side_effect = Exception("SMTP Error")
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.SendMessageInput(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test body"
                )
                
                result = await mail.send_message(input_data)
                
                assert result.status == "error"
                assert "SMTP Error" in result.details


class TestGetMessage:
    """Test the get_message tool."""
    
    @pytest.mark.asyncio
    async def test_get_message_success(self, mock_account_settings, mock_email_message):
        """Test successful message retrieval."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get_message_by_uid.return_value = mock_email_message
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.GetMessageInput(
                    account_name="test_account",
                    message_uid="12345"
                )
                
                result = await mail.get_message(input_data)
                
                assert result.message.uid == "12345"
                assert result.message.subject == "Test Subject"
    
    @pytest.mark.asyncio
    async def test_get_message_with_mark_as_read(self, mock_account_settings, mock_email_message):
        """Test message retrieval with mark as read."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get_message_by_uid.return_value = mock_email_message
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.GetMessageInput(
                    account_name="test_account",
                    message_uid="12345",
                    mark_as_read=True
                )
                
                result = await mail.get_message(input_data)
                
                # Verify mark_message was called
                mock_client.mark_message.assert_called_once_with("12345", True, "INBOX")
                assert result.message.is_read is True
    
    @pytest.mark.asyncio
    async def test_get_message_not_found(self, mock_account_settings):
        """Test getting non-existent message."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get_message_by_uid.return_value = None
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.GetMessageInput(
                    account_name="test_account",
                    message_uid="nonexistent"
                )
                
                with pytest.raises(ValueError, match="Message with UID nonexistent not found"):
                    await mail.get_message(input_data)


class TestMarkMessage:
    """Test the mark_message tool."""
    
    @pytest.mark.asyncio
    async def test_mark_message_as_read(self, mock_account_settings):
        """Test marking message as read."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.MarkMessageInput(
                    account_name="test_account",
                    message_uid="12345",
                    mark_as_read=True
                )
                
                result = await mail.mark_message(input_data)
                
                assert result.status == "success"
                assert "marked as read" in result.details
                mock_client.mark_message.assert_called_once_with("12345", True, "INBOX")
    
    @pytest.mark.asyncio
    async def test_mark_message_as_unread(self, mock_account_settings):
        """Test marking message as unread."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.MarkMessageInput(
                    account_name="test_account",
                    message_uid="12345",
                    mark_as_read=False
                )
                
                result = await mail.mark_message(input_data)
                
                assert result.status == "success"
                assert "marked as unread" in result.details
                mock_client.mark_message.assert_called_once_with("12345", False, "INBOX")


class TestListMailboxes:
    """Test the list_mailboxes tool."""
    
    @pytest.mark.asyncio
    async def test_list_mailboxes_success(self, mock_account_settings):
        """Test successful mailbox listing."""
        mock_mailboxes = ["INBOX", "Sent", "Drafts", "Trash"]
        
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.list_mailboxes.return_value = mock_mailboxes
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.ListMailboxesInput(account_name="test_account")
                result = await mail.list_mailboxes(input_data)
                
                assert result.account_name == "test_account"
                assert result.mailboxes == mock_mailboxes
    
    @pytest.mark.asyncio
    async def test_list_mailboxes_failure(self, mock_account_settings):
        """Test mailbox listing failure."""
        with patch('universal_email_mcp.tools.mail.get_account_settings', return_value=mock_account_settings):
            with patch.object(mail, 'EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.list_mailboxes.side_effect = Exception("IMAP Error")
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                input_data = models.ListMailboxesInput(account_name="test_account")
                result = await mail.list_mailboxes(input_data)
                
                assert result.account_name == "test_account"
                assert result.mailboxes == []