"""Universal Email MCP Server - Connect to any IMAP/SMTP email provider."""

__version__ = "0.1.0"
__author__ = "Universal Email MCP Team"
__description__ = "Universal Email MCP Server for AI agents to connect to any email provider"

from .server import UniversalEmailServer, create_server

__all__ = ["UniversalEmailServer", "create_server"]
