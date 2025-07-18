# Universal Email MCP Server

A Model Context Protocol (MCP) server that provides AI agents with universal email capabilities. Connect to any email provider that supports IMAP (for receiving) and SMTP (for sending) protocols.

## Features

- **Universal Compatibility**: Connect to any email provider (Gmail, Outlook, Yahoo, custom IMAP/SMTP servers)
- **Multiple Account Support**: Manage multiple email accounts simultaneously
- **Comprehensive Email Operations**: List, read, send, and manage emails
- **Multiple Transports**: Support for both stdio (local) and HTTP (remote) connections
- **Docker Support**: Ready for cloud deployment

## Quick Start

### For Local Development (Claude Desktop, Cursor)

1. **Install dependencies**:
   ```bash
   git clone <repository-url>
   cd universal-email-mcp-server
   poetry install
   ```

2. **Run with stdio transport**:
   ```bash
   poetry run python -m universal_email_mcp.stdio_main
   ```

### For Cloud Deployment

1. **Run with Docker**:
   ```bash
   docker-compose up -d --build
   ```

2. **Or run directly with HTTP transport**:
   ```bash
   poetry run python -m universal_email_mcp.http_main --host 0.0.0.0 --port 8000
   ```

## Integration Guide

### Claude Desktop

Add to your Claude Desktop configuration file:

**For Windows:**
```json
{
  "mcpServers": {
    "universal-email": {
      "command": "cmd",
      "args": ["/c", "cd /d \"C:\\path\\to\\universal-email-mcp-server\" && poetry run python -m universal_email_mcp.stdio_main"],
      "env": {}
    }
  }
}
```

**For macOS/Linux:**
```json
{
  "mcpServers": {
    "universal-email": {
      "command": "sh",
      "args": ["-c", "cd '/path/to/universal-email-mcp-server' && poetry run python -m universal_email_mcp.stdio_main"],
      "env": {}
    }
  }
}
```

> **Important**: Replace `/path/to/universal-email-mcp-server` with your actual project directory.

**Alternative: Using Python with PYTHONPATH**

If you prefer not to use Poetry:

```json
{
  "mcpServers": {
    "universal-email": {
      "command": "python",
      "args": ["-m", "universal_email_mcp.stdio_main"],
      "env": {
        "PYTHONPATH": "/path/to/universal-email-mcp-server/src"
      }
    }
  }
}
```

### Cursor IDE

Configure in Cursor Settings > Extensions > MCP:

```json
{
  "servers": {
    "universal-email": {
      "command": "poetry",
      "args": ["run", "python", "-m", "universal_email_mcp.stdio_main"],
      "cwd": "/path/to/universal-email-mcp-server"
    }
  }
}
```

### OpenAI and Cloud Clients

For cloud-based AI services, deploy the server and use HTTP transport:

1. **Deploy with ngrok (development)**:
   ```bash
   # Terminal 1: Start the server
   docker-compose up -d --build
   
   # Terminal 2: Expose with ngrok
   ngrok http 8000
   ```

2. **Use the public URL in your MCP client**:
   ```json
   {
     "type": "mcp",
     "server_label": "universal-email",
     "server_url": "https://your-ngrok-url.ngrok.app/sse",
     "require_approval": "never"
   }
   ```

3. **Production deployment**: Deploy to Railway, Heroku, Google Cloud Run, etc.

## Available Tools

### Account Management

#### `add_account`
Add a new email account configuration.

**Parameters:**
- `account_name` (string): Unique identifier for the account
- `full_name` (string): Full name for outgoing emails
- `email_address` (string): Email address
- `user_name` (string): Authentication username
- `password` (string): Authentication password
- `imap_host` (string): IMAP server hostname
- `smtp_host` (string): SMTP server hostname
- `imap_port` (integer, optional): IMAP port (default: 993)
- `smtp_port` (integer, optional): SMTP port (default: 465)

#### `list_accounts`
List all configured email accounts.

#### `remove_account`
Remove an email account configuration.

### Email Operations

#### `list_messages`
List email messages with optional filtering and pagination.

**Parameters:**
- `account_name` (string): Account to list messages from
- `page` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Messages per page (default: 10)
- `subject_filter` (string, optional): Filter by subject
- `sender_filter` (string, optional): Filter by sender
- `unread_only` (boolean, optional): Only unread messages

#### `send_message`
Send an email message.

**Parameters:**
- `account_name` (string): Account to send from
- `recipients` (array): List of recipient email addresses
- `subject` (string): Email subject
- `body` (string): Email body content
- `cc` (array, optional): CC recipients
- `bcc` (array, optional): BCC recipients

#### `get_message`
Get a specific email message by UID.

#### `mark_message`
Mark a message as read or unread.

#### `list_mailboxes`
List available mailboxes/folders for an account.

## Common Email Provider Settings

### Gmail
```json
{
  "imap_host": "imap.gmail.com",
  "smtp_host": "smtp.gmail.com"
}
```

### Outlook/Hotmail
```json
{
  "imap_host": "outlook.office365.com",
  "smtp_host": "smtp-mail.outlook.com",
  "smtp_port": 587
}
```

### Yahoo Mail
```json
{
  "imap_host": "imap.mail.yahoo.com",
  "smtp_host": "smtp.mail.yahoo.com"
}
```

## Testing the Server

Try these example prompts with your AI agent:

### Setup
- "Add my Gmail account with the name 'personal'"
- "List all my configured email accounts"

### Reading Email
- "Show me the latest 5 emails from my personal account"
- "List unread emails from my work account"
- "Get the full content of message UID 12345"

### Sending Email
- "Send an email to john@example.com with subject 'Meeting Tomorrow'"
- "Send a follow-up email to the team with updates"

### Management
- "List all mailboxes in my Gmail account"
- "Mark message 12345 as read"

## Development

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Docker (optional, for containerized deployment)

### Setup

```bash
# Clone and install
git clone <repository-url>
cd universal-email-mcp-server
poetry install

# Run tests
poetry run pytest
```

## Deployment

### Docker

```bash
# Build and run
docker-compose up -d --build

# Check logs
docker-compose logs universal-email-mcp

# Stop
docker-compose down
```

### Environment Variables

For production deployment, you can configure:

- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 8000)

## License

MIT License