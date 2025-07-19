# Universal Email MCP Server

**Connect any email provider to your AI assistant in minutes. Zero friction, maximum security.**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP 1.2+](https://img.shields.io/badge/MCP-1.2+-green.svg)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://hub.docker.com/r/universal-email-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A secure MCP server that connects AI agents to any email provider via IMAP/SMTP protocols. Zero config required for local development, enterprise-ready for cloud deployment.

## 🏆 Available Tools

### Account Management
- **add_account** - Add email account with IMAP/SMTP settings
- **list_accounts** - View all configured accounts  
- **remove_account** - Remove account configuration

### Email Operations
- **list_messages** - List emails with filtering & pagination
- **get_message** - Get specific email by UID
- **send_message** - Send emails with attachments
- **mark_message** - Mark read/unread
- **list_mailboxes** - Show available folders/mailboxes

## ⚡ Quick Start (Choose Your Path)

### 1. Claude Desktop (30 seconds) 🎯
**Windows CMD setup that actually works:**
```json
{
  "mcpServers": {
    "universal-email": {
      "command": "cmd",
      "args": ["/c", "cd", "/d", "C:\\path\\to\\universal-email-mcp-server", "&&", "poetry", "run", "python", "-m", "universal_email_mcp.stdio_main"],
      "cwd": "C:\\path\\to\\universal-email-mcp-server"
    }
  }
}
```

### 2. One-Command Setup ⚡
```bash
# Works on Windows, Mac, Linux
poetry run universal-email-cli deploy claude-desktop
```

### 3. Docker (Cloud ready)
```bash
# Creates config automatically
docker run -v ~/.claude-email-mcp:/data -p 8000:8000 universal-email-mcp:latest
```

## 📦 Installation

```bash
git clone <repo-url>
cd universal-email-mcp-server
poetry install
poetry run universal-email-cli deploy claude-desktop  # Done!
```

## 🖥️ Client Configurations

### Claude Desktop (Recommended)
**Windows CMD with proper path handling:**
```json
{
  "mcpServers": {
    "universal-email": {
      "command": "cmd",
      "args": ["/c", "cd", "/d", "C:\\path\\to\\universal-email-mcp-server", "&&", "poetry", "run", "python", "-m", "universal_email_mcp.stdio_main"],
      "cwd": "C:\\path\\to\\universal-email-mcp-server"
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "universal-email": {
      "command": "poetry",
      "args": ["run", "python", "-m", "universal_email_mcp.stdio_main"],
      "cwd": "/path/to/universal-email-mcp-server"
    }
  }
}
```

### Cursor IDE
Same as Claude Desktop - supports both stdio and HTTP transports.

### Cloud Deployment
Use HTTP with Bearer tokens - see [DEPLOYMENT.md](DEPLOYMENT.md)

## 📧 Email Prompt Examples

**Setup:**
```
"Add my Gmail account named 'personal'"
"List all my accounts"
```

**Email Management:**
```
"Show me latest 10 unread emails from personal"
"Send email to john@company.com with subject 'Meeting tomorrow'"
"Mark message 12345 as read"
```

---

**🎈 That's it! Run `poetry run universal-email-cli deploy claude-desktop` and you're connected.**