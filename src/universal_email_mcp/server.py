"""Universal Email MCP Server implementation."""

from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool

from . import models
from .tools import account, mail


class UniversalEmailServer:
    """Universal Email MCP Server for connecting to any IMAP/SMTP email provider."""
    
    def __init__(self):
        self.server = Server("universal-email-mcp")
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP tool handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List all available email tools."""
            return [
                Tool(
                    name="add_account",
                    description="Add a new email account configuration with IMAP and SMTP settings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "A unique name for this account, e.g., 'work_email' or 'personal'"
                            },
                            "full_name": {
                                "type": "string", 
                                "description": "Full name for outgoing emails"
                            },
                            "email_address": {
                                "type": "string",
                                "description": "Email address for this account"
                            },
                            "user_name": {
                                "type": "string",
                                "description": "Username for both IMAP and SMTP authentication"
                            },
                            "password": {
                                "type": "string",
                                "description": "Password for both IMAP and SMTP authentication"
                            },
                            "imap_host": {
                                "type": "string",
                                "description": "IMAP server hostname"
                            },
                            "imap_port": {
                                "type": "integer",
                                "default": 993,
                                "description": "IMAP server port (default: 993)"
                            },
                            "imap_use_ssl": {
                                "type": "boolean",
                                "default": True,
                                "description": "Use SSL for IMAP connection"
                            },
                            "imap_verify_ssl": {
                                "type": "boolean",
                                "default": True,
                                "description": "Verify SSL certificates for IMAP (set to false for self-signed certificates)"
                            },
                            "smtp_host": {
                                "type": "string",
                                "description": "SMTP server hostname"
                            },
                            "smtp_port": {
                                "type": "integer", 
                                "default": 465,
                                "description": "SMTP server port (default: 465)"
                            },
                            "smtp_use_ssl": {
                                "type": "boolean",
                                "default": True,
                                "description": "Use SSL for SMTP connection"
                            },
                            "smtp_verify_ssl": {
                                "type": "boolean",
                                "default": True,
                                "description": "Verify SSL certificates for SMTP (set to false for self-signed certificates)"
                            }
                        },
                        "required": ["account_name", "full_name", "email_address", "user_name", "password", "imap_host", "smtp_host"]
                    }
                ),
                Tool(
                    name="list_accounts",
                    description="List all configured email accounts",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="remove_account", 
                    description="Remove an email account configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account to remove"
                            }
                        },
                        "required": ["account_name"]
                    }
                ),
                Tool(
                    name="list_messages",
                    description="List email messages from a specified account with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account to list messages from"
                            },
                            "mailbox": {
                                "type": "string",
                                "default": "INBOX",
                                "description": "Mailbox to list messages from"
                            },
                            "page": {
                                "type": "integer",
                                "default": 1,
                                "minimum": 1,
                                "description": "Page number for pagination"
                            },
                            "page_size": {
                                "type": "integer",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Number of messages per page"
                            },
                            "subject_filter": {
                                "type": "string",
                                "description": "Filter messages by subject (partial match)"
                            },
                            "sender_filter": {
                                "type": "string", 
                                "description": "Filter messages by sender email"
                            },
                            "since": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Only show messages since this date (ISO format)"
                            },
                            "before": {
                                "type": "string",
                                "format": "date-time", 
                                "description": "Only show messages before this date (ISO format)"
                            },
                            "unread_only": {
                                "type": "boolean",
                                "default": False,
                                "description": "Only show unread messages"
                            }
                        },
                        "required": ["account_name"]
                    }
                ),
                Tool(
                    name="send_message",
                    description="Send an email message from a specified account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account to send from"
                            },
                            "recipients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of recipient email addresses"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body content"
                            },
                            "cc": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of CC recipient email addresses"
                            },
                            "bcc": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of BCC recipient email addresses"
                            },
                            "is_html": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether the body content is HTML"
                            }
                        },
                        "required": ["account_name", "recipients", "subject", "body"]
                    }
                ),
                Tool(
                    name="get_message",
                    description="Get a specific email message by UID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account"
                            },
                            "message_uid": {
                                "type": "string",
                                "description": "Unique identifier of the message"
                            },
                            "mailbox": {
                                "type": "string",
                                "default": "INBOX",
                                "description": "Mailbox containing the message"
                            },
                            "mark_as_read": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether to mark the message as read"
                            }
                        },
                        "required": ["account_name", "message_uid"]
                    }
                ),
                Tool(
                    name="mark_message",
                    description="Mark a message as read or unread",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account"
                            },
                            "message_uid": {
                                "type": "string",
                                "description": "Unique identifier of the message"
                            },
                            "mailbox": {
                                "type": "string",
                                "default": "INBOX",
                                "description": "Mailbox containing the message"
                            },
                            "mark_as_read": {
                                "type": "boolean",
                                "description": "True to mark as read, False to mark as unread"
                            }
                        },
                        "required": ["account_name", "message_uid", "mark_as_read"]
                    }
                ),
                Tool(
                    name="list_mailboxes",
                    description="List available mailboxes/folders for an account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "Name of the account"
                            }
                        },
                        "required": ["account_name"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[Dict[str, Any]]:
            """Handle tool execution."""
            if arguments is None:
                arguments = {}
                
            try:
                if name == "add_account":
                    input_data = models.AddAccountInput(**arguments)
                    result = await account.add_account(input_data)
                    return [{"type": "text", "text": f"Status: {result.status}\nDetails: {result.details}"}]
                
                elif name == "list_accounts":
                    result = await account.list_accounts()
                    if result.accounts:
                        account_list = "\n".join(f"- {acc}" for acc in result.accounts)
                        return [{"type": "text", "text": f"Configured accounts:\n{account_list}"}]
                    else:
                        return [{"type": "text", "text": "No email accounts configured."}]
                
                elif name == "remove_account":
                    input_data = models.RemoveAccountInput(**arguments)
                    result = await account.remove_account(input_data)
                    return [{"type": "text", "text": f"Status: {result.status}\nDetails: {result.details}"}]
                
                elif name == "list_messages":
                    input_data = models.ListMessagesInput(**arguments)
                    result = await mail.list_messages(input_data)
                    
                    if result.messages:
                        message_list = []
                        for msg in result.messages:
                            status = "✉️" if not msg.is_read else "📧"
                            attachment = "📎" if msg.has_attachments else ""
                            message_list.append(
                                f"{status} {attachment} [{msg.uid}] {msg.subject}\n"
                                f"    From: {msg.sender}\n"
                                f"    Date: {msg.date.strftime('%Y-%m-%d %H:%M')}"
                            )
                        
                        messages_text = "\n\n".join(message_list)
                        return [{"type": "text", "text": 
                                f"Messages from {result.account_name} ({result.mailbox})\n"
                                f"Page {result.page} of {(result.total_messages + result.page_size - 1) // result.page_size} "
                                f"({result.total_messages} total)\n\n{messages_text}"}]
                    else:
                        return [{"type": "text", "text": f"No messages found in {result.account_name} ({result.mailbox})."}]
                
                elif name == "send_message":
                    input_data = models.SendMessageInput(**arguments)
                    result = await mail.send_message(input_data)
                    return [{"type": "text", "text": f"Status: {result.status}\nDetails: {result.details}"}]
                
                elif name == "get_message":
                    input_data = models.GetMessageInput(**arguments)
                    result = await mail.get_message(input_data)
                    
                    msg = result.message
                    status = "✉️ (Unread)" if not msg.is_read else "📧 (Read)"
                    attachment = " 📎 Has attachments" if msg.has_attachments else ""
                    
                    return [{"type": "text", "text": 
                            f"{status}{attachment}\n\n"
                            f"Subject: {msg.subject}\n"
                            f"From: {msg.sender}\n"
                            f"Date: {msg.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"UID: {msg.uid}\n\n"
                            f"Body:\n{msg.body}"}]
                
                elif name == "mark_message":
                    input_data = models.MarkMessageInput(**arguments)
                    result = await mail.mark_message(input_data)
                    return [{"type": "text", "text": f"Status: {result.status}\nDetails: {result.details}"}]
                
                elif name == "list_mailboxes":
                    input_data = models.ListMailboxesInput(**arguments)
                    result = await mail.list_mailboxes(input_data)
                    
                    if result.mailboxes:
                        mailbox_list = "\n".join(f"- {mb}" for mb in result.mailboxes)
                        return [{"type": "text", "text": f"Mailboxes for {result.account_name}:\n{mailbox_list}"}]
                    else:
                        return [{"type": "text", "text": f"No mailboxes found for {result.account_name}."}]
                
                else:
                    return [{"type": "text", "text": f"Unknown tool: {name}"}]
                    
            except ValueError as e:
                return [{"type": "text", "text": f"Error: {str(e)}"}]
            except Exception as e:
                return [{"type": "text", "text": f"Unexpected error: {str(e)}"}]

    async def run_stdio(self):
        """Run server with STDIO transport."""
        from mcp.server.stdio import stdio_server
        from mcp.server.models import InitializationOptions
        from mcp.types import ServerCapabilities, ToolsCapability
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="universal-email-mcp",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    ),
                ),
            )

    async def run_sse(self, host: str = "localhost", port: int = 8000):
        """Run server with Server-Sent Events transport."""
        from mcp.server.sse import SseServerTransport
        from mcp.server.models import InitializationOptions
        from mcp.types import ServerCapabilities, ToolsCapability
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import Response
        import uvicorn
        
        sse = SseServerTransport("/messages/")
        
        async def handle_sse(request):
            try:
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await self.server.run(
                        streams[0], streams[1], 
                        InitializationOptions(
                            server_name="universal-email-mcp",
                            server_version="0.1.0",
                            capabilities=ServerCapabilities(
                                tools=ToolsCapability()
                            ),
                        )
                    )
            except Exception:
                raise
            return Response()
        
        async def handle_messages(request):
            return await sse.handle_post_message(request.scope, request.receive, request._send)
        
        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=handle_messages, methods=["POST"]),
            ]
        )
        
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


def create_server() -> UniversalEmailServer:
    """Create and return a Universal Email MCP Server instance."""
    return UniversalEmailServer()