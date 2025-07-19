"""Email operation tools for Universal Email MCP Server."""

import email
import email.message
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aioimaplib
import aiosmtplib

from .. import config, models
from .account import get_account_settings


class EmailClient:
    """Async email client for IMAP and SMTP operations."""

    def __init__(self, account_settings: config.EmailSettings):
        self.account_settings = account_settings
        self._imap_client = None
        self._smtp_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close all connections."""
        if self._imap_client:
            try:
                await self._imap_client.logout()
            except Exception:
                pass
            self._imap_client = None

        if self._smtp_client:
            try:
                await self._smtp_client.quit()
            except Exception:
                pass
            self._smtp_client = None

    async def _get_imap_client(self):
        """Get or create IMAP client connection."""
        if self._imap_client is None:
            incoming = self.account_settings.incoming

            ssl_context = None
            if incoming.use_ssl and not incoming.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            if incoming.use_ssl:
                self._imap_client = aioimaplib.IMAP4_SSL(
                    host=incoming.host,
                    port=incoming.port,
                    ssl_context=ssl_context
                )
            else:
                self._imap_client = aioimaplib.IMAP4(
                    host=incoming.host,
                    port=incoming.port
                )

            await self._imap_client.wait_hello_from_server()
            await self._imap_client.login(incoming.user_name, incoming.password)

        return self._imap_client

    async def _get_smtp_client(self) -> aiosmtplib.SMTP:
        """Get or create SMTP client connection."""
        if self._smtp_client is None:
            outgoing = self.account_settings.outgoing

            ssl_context = None
            if outgoing.use_ssl and not outgoing.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            smtp_kwargs = {
                "hostname": outgoing.host,
                "port": outgoing.port,
            }

            if outgoing.use_ssl:
                smtp_kwargs["use_tls"] = True
                if ssl_context:
                    smtp_kwargs["tls_context"] = ssl_context
            else:
                smtp_kwargs["use_tls"] = False
                smtp_kwargs["start_tls"] = False
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                smtp_kwargs["tls_context"] = ssl_context

            self._smtp_client = aiosmtplib.SMTP(**smtp_kwargs)

            await self._smtp_client.connect()
            await self._smtp_client.login(outgoing.user_name, outgoing.password)

        return self._smtp_client

    async def list_mailboxes(self) -> list[str]:
        """List available mailboxes."""
        imap = await self._get_imap_client()
        response = await imap.list()

        mailboxes = []
        for line in response.lines:
            parts = line.decode().split('"')
            if len(parts) >= 3:
                mailbox_name = parts[-2]
                mailboxes.append(mailbox_name)

        return sorted(mailboxes)

    async def get_message_count(self, mailbox: str = "INBOX", search_criteria: str = "ALL") -> int:
        """Get count of messages matching criteria."""
        imap = await self._get_imap_client()
        await imap.select(mailbox)

        response = await imap.search(search_criteria)
        if response.result == "OK":
            message_ids = response.lines[0].decode().split()
            return len(message_ids)
        return 0

    def _build_search_criteria(
        self,
        subject_filter: str | None = None,
        sender_filter: str | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        unread_only: bool = False
    ) -> str:
        """Build IMAP search criteria."""
        criteria = []

        if unread_only:
            criteria.append("UNSEEN")

        if subject_filter:
            criteria.append(f'SUBJECT "{subject_filter}"')

        if sender_filter:
            criteria.append(f'FROM "{sender_filter}"')

        if since:
            criteria.append(f'SINCE "{since.strftime("%d-%b-%Y")}"')

        if before:
            criteria.append(f'BEFORE "{before.strftime("%d-%b-%Y")}"')

        return " ".join(criteria) if criteria else "ALL"

    async def get_messages(
        self,
        mailbox: str = "INBOX",
        page: int = 1,
        page_size: int = 10,
        subject_filter: str | None = None,
        sender_filter: str | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        unread_only: bool = False
    ) -> tuple[list[models.EmailMessage], int]:
        """Get paginated list of messages."""
        imap = await self._get_imap_client()
        await imap.select(mailbox)

        search_criteria = self._build_search_criteria(
            subject_filter, sender_filter, since, before, unread_only
        )

        response = await imap.search(search_criteria)
        if response.result != "OK":
            return [], 0

        message_ids = response.lines[0].decode().split()
        total_count = len(message_ids)

        if not message_ids:
            return [], 0

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_message_ids = list(reversed(message_ids))[start_idx:end_idx]

        messages = []
        for msg_id in page_message_ids:
            try:
                fetch_response = await imap.fetch(
                    msg_id, "(UID RFC822.HEADER RFC822.TEXT FLAGS)"
                )

                if fetch_response.result == "OK":
                    message = self._parse_message(fetch_response.lines, msg_id)
                    if message:
                        messages.append(message)

            except Exception:
                continue

        return messages, total_count

    def _parse_message(self, fetch_lines: list[bytes], msg_id: str) -> models.EmailMessage | None:
        """Parse IMAP fetch response into EmailMessage."""
        try:
            raw_message = b"\r\n".join(fetch_lines)
            msg = email.message_from_bytes(raw_message)

            subject = msg.get("Subject", "")
            sender = msg.get("From", "")
            date_str = msg.get("Date", "")

            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                date = datetime.now()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            is_read = "\\Seen" in str(fetch_lines)
            has_attachments = msg.get_content_maintype() == "multipart"

            return models.EmailMessage(
                uid=msg_id,
                subject=subject,
                sender=sender,
                body=body,
                date=date,
                is_read=is_read,
                has_attachments=has_attachments
            )

        except Exception:
            return None

    async def get_message_by_uid(self, uid: str, mailbox: str = "INBOX") -> models.EmailMessage | None:
        """Get a specific message by UID."""
        imap = await self._get_imap_client()
        await imap.select(mailbox)

        try:
            fetch_response = await imap.fetch(uid, "(UID RFC822.HEADER RFC822.TEXT FLAGS)")
            if fetch_response.result == "OK":
                return self._parse_message(fetch_response.lines, uid)
        except Exception:
            pass

        return None

    async def mark_message(self, uid: str, mark_as_read: bool, mailbox: str = "INBOX"):
        """Mark a message as read or unread."""
        imap = await self._get_imap_client()
        await imap.select(mailbox)

        flag = "\\Seen"
        command = "FLAGS.SILENT" if mark_as_read else "-FLAGS.SILENT"

        await imap.store(uid, command, flag)

    async def send_message(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        is_html: bool = False
    ):
        """Send an email message."""
        smtp = await self._get_smtp_client()

        msg = MIMEMultipart() if cc or bcc else MIMEText(body, "html" if is_html else "plain")

        if isinstance(msg, MIMEMultipart):
            msg.attach(MIMEText(body, "html" if is_html else "plain"))

        msg["From"] = f"{self.account_settings.full_name} <{self.account_settings.email_address}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)

        all_recipients = recipients[:]
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        await smtp.send_message(msg, recipients=all_recipients)


async def list_messages(data: models.ListMessagesInput) -> models.ListMessagesOutput:
    """List email messages from specified account."""
    try:
        account_settings = get_account_settings(data.account_name)

        async with EmailClient(account_settings) as client:
            messages, total = await client.get_messages(
                mailbox=data.mailbox,
                page=data.page,
                page_size=data.page_size,
                subject_filter=data.subject_filter,
                sender_filter=data.sender_filter,
                since=data.since,
                before=data.before,
                unread_only=data.unread_only
            )

            return models.ListMessagesOutput(
                account_name=data.account_name,
                mailbox=data.mailbox,
                page=data.page,
                page_size=data.page_size,
                total_messages=total,
                messages=messages
            )

    except Exception:
        return models.ListMessagesOutput(
            account_name=data.account_name,
            mailbox=data.mailbox,
            page=data.page,
            page_size=data.page_size,
            total_messages=0,
            messages=[]
        )


async def send_message(data: models.SendMessageInput) -> models.StatusOutput:
    """Send an email message."""
    try:
        account_settings = get_account_settings(data.account_name)

        async with EmailClient(account_settings) as client:
            await client.send_message(
                recipients=data.recipients,
                subject=data.subject,
                body=data.body,
                cc=data.cc,
                bcc=data.bcc,
                is_html=data.is_html
            )

            return models.StatusOutput(
                status="success",
                details=f"Email sent successfully to {len(data.recipients)} recipients"
            )

    except Exception as e:
        return models.StatusOutput(
            status="error",
            details=f"Failed to send email: {str(e)}"
        )


async def get_message(data: models.GetMessageInput) -> models.GetMessageOutput:
    """Get a specific email message."""
    try:
        account_settings = get_account_settings(data.account_name)

        async with EmailClient(account_settings) as client:
            message = await client.get_message_by_uid(data.message_uid, data.mailbox)

            if not message:
                raise ValueError(f"Message with UID {data.message_uid} not found")

            if data.mark_as_read:
                await client.mark_message(data.message_uid, True, data.mailbox)
                message.is_read = True

            return models.GetMessageOutput(message=message)

    except Exception as e:
        raise ValueError(f"Failed to get message: {str(e)}")


async def mark_message(data: models.MarkMessageInput) -> models.StatusOutput:
    """Mark a message as read or unread."""
    try:
        account_settings = get_account_settings(data.account_name)

        async with EmailClient(account_settings) as client:
            await client.mark_message(data.message_uid, data.mark_as_read, data.mailbox)

            status = "read" if data.mark_as_read else "unread"
            return models.StatusOutput(
                status="success",
                details=f"Message marked as {status}"
            )

    except Exception as e:
        return models.StatusOutput(
            status="error",
            details=f"Failed to mark message: {str(e)}"
        )


async def list_mailboxes(data: models.ListMailboxesInput) -> models.ListMailboxesOutput:
    """List available mailboxes for an account."""
    try:
        account_settings = get_account_settings(data.account_name)

        async with EmailClient(account_settings) as client:
            mailboxes = await client.list_mailboxes()

            return models.ListMailboxesOutput(
                account_name=data.account_name,
                mailboxes=mailboxes
            )

    except Exception:
        return models.ListMailboxesOutput(
            account_name=data.account_name,
            mailboxes=[]
        )
