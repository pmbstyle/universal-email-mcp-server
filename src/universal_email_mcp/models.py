"""Pydantic models for Universal Email MCP Server tool inputs and outputs."""

from datetime import datetime

from pydantic import BaseModel, Field

# --- Account Management Models ---

class AddAccountInput(BaseModel):
    """Input model for adding a new email account."""

    account_name: str = Field(
        description="A unique name for this account, e.g., 'work_email' or 'personal'"
    )
    full_name: str = Field(description="Full name for outgoing emails")
    email_address: str = Field(description="Email address for this account")
    user_name: str = Field(
        description="Username for both IMAP and SMTP authentication"
    )
    password: str = Field(description="Password for both IMAP and SMTP authentication")
    imap_host: str = Field(description="IMAP server hostname")
    imap_port: int = Field(default=993, description="IMAP server port (default: 993)")
    imap_use_ssl: bool = Field(default=True, description="Use SSL for IMAP connection")
    imap_verify_ssl: bool = Field(default=True, description="Verify SSL certificates for IMAP")
    smtp_host: str = Field(description="SMTP server hostname")
    smtp_port: int = Field(default=465, description="SMTP server port (default: 465)")
    smtp_use_ssl: bool = Field(default=True, description="Use SSL for SMTP connection")
    smtp_verify_ssl: bool = Field(default=True, description="Verify SSL certificates for SMTP")


class ListAccountsOutput(BaseModel):
    """Output model for listing configured accounts."""

    accounts: list[str] = Field(description="List of configured account names")


class RemoveAccountInput(BaseModel):
    """Input model for removing an email account."""

    account_name: str = Field(description="Name of the account to remove")


# --- Mail Operation Models ---

class EmailMessage(BaseModel):
    """Represents an email message."""

    uid: str = Field(description="Unique identifier for the email")
    subject: str = Field(description="Email subject")
    sender: str = Field(description="Sender email address")
    body: str = Field(description="Email body content")
    date: datetime = Field(description="Date the email was sent")
    is_read: bool = Field(default=False, description="Whether the email has been read")
    has_attachments: bool = Field(default=False, description="Whether the email has attachments")


class ListMessagesInput(BaseModel):
    """Input model for listing email messages."""

    account_name: str = Field(description="Name of the account to list messages from")
    mailbox: str = Field(default="INBOX", description="Mailbox to list messages from")
    page: int = Field(default=1, ge=1, description="Page number for pagination")
    page_size: int = Field(
        default=10, ge=1, le=100, description="Number of messages per page"
    )
    subject_filter: str | None = Field(
        default=None, description="Filter messages by subject (partial match)"
    )
    sender_filter: str | None = Field(
        default=None, description="Filter messages by sender email"
    )
    since: datetime | None = Field(
        default=None, description="Only show messages since this date"
    )
    before: datetime | None = Field(
        default=None, description="Only show messages before this date"
    )
    unread_only: bool = Field(
        default=False, description="Only show unread messages"
    )


class ListMessagesOutput(BaseModel):
    """Output model for listing email messages."""

    account_name: str = Field(description="Account name used for the query")
    mailbox: str = Field(description="Mailbox that was queried")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of messages per page")
    total_messages: int = Field(description="Total number of messages matching filters")
    messages: list[EmailMessage] = Field(description="List of email messages")


class SendMessageInput(BaseModel):
    """Input model for sending an email message."""

    account_name: str = Field(description="Name of the account to send from")
    recipients: list[str] = Field(description="List of recipient email addresses")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body content")
    cc: list[str] | None = Field(
        default=None, description="List of CC recipient email addresses"
    )
    bcc: list[str] | None = Field(
        default=None, description="List of BCC recipient email addresses"
    )
    is_html: bool = Field(
        default=False, description="Whether the body content is HTML"
    )


class GetMessageInput(BaseModel):
    """Input model for getting a specific email message."""

    account_name: str = Field(description="Name of the account")
    message_uid: str = Field(description="Unique identifier of the message")
    mailbox: str = Field(default="INBOX", description="Mailbox containing the message")
    mark_as_read: bool = Field(
        default=False, description="Whether to mark the message as read"
    )


class GetMessageOutput(BaseModel):
    """Output model for getting a specific email message."""

    message: EmailMessage = Field(description="The requested email message")


class MarkMessageInput(BaseModel):
    """Input model for marking a message as read/unread."""

    account_name: str = Field(description="Name of the account")
    message_uid: str = Field(description="Unique identifier of the message")
    mailbox: str = Field(default="INBOX", description="Mailbox containing the message")
    mark_as_read: bool = Field(description="True to mark as read, False to mark as unread")


class ListMailboxesInput(BaseModel):
    """Input model for listing mailboxes/folders."""

    account_name: str = Field(description="Name of the account")


class ListMailboxesOutput(BaseModel):
    """Output model for listing mailboxes/folders."""

    account_name: str = Field(description="Account name used for the query")
    mailboxes: list[str] = Field(description="List of available mailbox names")


# --- Common Output Models ---

class StatusOutput(BaseModel):
    """Generic status output model."""

    status: str = Field(description="Status message indicating success or failure")
    details: str | None = Field(
        default=None, description="Additional details about the operation"
    )


class ErrorOutput(BaseModel):
    """Error output model."""

    error: str = Field(description="Error message")
    error_type: str = Field(description="Type of error that occurred")
    details: str | None = Field(default=None, description="Additional error details")
