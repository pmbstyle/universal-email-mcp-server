"""
Authentication system for Universal Email MCP Server.

Provides token-based authentication for HTTP/SSE transport.
Handles token generation, validation, and persistence across
Claude Desktop, VPS, and Docker deployments.
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import secrets
from datetime import datetime, timedelta

from starlette.authentication import AuthCredentials, AuthenticationBackend, AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.types import Scope, Receive, Send
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger("universal-email-mcp-auth")


class AuthTokenManager:
    """Manages authentication tokens for MCP server."""
    
    TOKEN_FILE_NAME = "token.txt"
    TOKEN_HISTORY_FILE = "token_history.txt"
    
    def __init__(self, token_dir: Optional[Path] = None):
        """Initialize token manager with directory for token storage."""
        if token_dir is None:
            # For Docker: /data, for local: ~/.config/universal_email_mcp/tokens
            self.token_dir = Path(os.getenv("TOKEN_DATA_DIR", "~/.config/universal_email_mcp/tokens")).expanduser()
        else:
            self.token_dir = Path(token_dir)
            
        self.token_path = self.token_dir / self.TOKEN_FILE_NAME
        self.history_path = self.token_dir / self.TOKEN_HISTORY_FILE
        
        # Ensure directory exists
        self.token_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_token(self) -> str:
        """Generate a new secure random token."""
        # Use UUID4 + additional entropy for better security
        return f"ue-{uuid.uuid4().hex}-{secrets.token_urlsafe(16)}"
    
    def save_token(self, token: str, app_context: str = "unknown") -> None:
        """Save token to file and log for user access."""
        with open(self.token_path, "w") as f:
            f.write(token)
        
        # Make token file readable only by owner (600 permissions)
        os.chmod(self.token_path, 0o600)
        
        # Log for container/CLI usage
        logger.info("🔐 MCP Auth Token generated")
        logger.info(f"📌 Token: {token}")
        logger.info(f"📂 Token file: {self.token_path}")
        
        # Save to history with context
        history_entry = {
            "token": token,
            "created": datetime.now().isoformat(),
            "context": app_context,
            "method": "generated"
        }
        
        import json
        with open(self.history_path, "a") as f:
            f.write(json.dumps(history_entry) + "\n")
    
    def load_token(self) -> Optional[str]:
        """Load existing token from file."""
        if not self.token_path.exists():
            return None
            
        try:
            with open(self.token_path, "r") as f:
                token = f.read().strip()
            return token if token else None
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return None
    
    def get_or_create_token(self, app_context: str = "unknown") -> str:
        """Get existing token or create a new one."""
        existing_token = self.load_token()
        if existing_token:
            logger.info("🔑 Using existing MCP auth token")
            home_path = str(self.token_path).replace(os.path.expanduser("~"), "~")
            logger.info(f"📂 Token file: {home_path}")
            return existing_token
        
        # Generate new token
        new_token = self.generate_token()
        self.save_token(new_token, app_context)
        return new_token
    
    def validate_token(self, token: str) -> bool:
        """Validate if the provided token is correct."""
        expected_token = self.load_token()
        return expected_token is not None and secrets.compare_digest(
            expected_token.encode(), token.encode()
        )
    
    def rotate_token(self, app_context: str = "unknown") -> str:
        """Generate and save a new token, invalidating the old one."""
        new_token = self.generate_token()
        self.save_token(new_token, app_context)
        
        # Log rotation
        logger.info("🔄 Token rotated successfully")
        logger.info(f"📌 New token: {new_token}")
        
        return new_token
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about current token setup."""
        token = self.load_token()
        return {
            "token_exists": token is not None,
            "token_file": str(self.token_path),
            "token_dir": str(self.token_dir),
            "token_length": len(token) if token else 0,
            "token_preview": f"{token[:8]}..." if token else None
        }


class BearerTokenValidator(AuthenticationBackend):
    """Authentication backend for Bearer token validation."""
    
    def __init__(self, token_manager: AuthTokenManager):
        self.token_manager = token_manager
    
    async def authenticate(self, request):
        """Authenticate request using Bearer token."""
        header = request.headers.get("Authorization")
        
        if not header:
            raise AuthenticationError("Missing Authorization header")
        
        try:
            scheme, token = header.split(" ", 1)
        except ValueError:
            raise AuthenticationError("Invalid Authorization header format")
        
        if scheme.lower() != "bearer":
            raise AuthenticationError("Invalid authentication scheme")
        
        if not self.token_manager.validate_token(token):
            raise AuthenticationError("Invalid or expired token")
        
        # Return authenticated scope with basic credentials
        return AuthCredentials(["authenticated"]), None


class MCPAuthMiddleware:
    """Middleware to handle MCP HTTP authentication."""
    
    def __init__(self, app, token_manager: AuthTokenManager):
        self.app = app
        self.token_manager = token_manager
        self.auth_backend = BearerTokenValidator(token_manager)
        self.auth_middleware = AuthenticationMiddleware(
            app, backend=self.auth_backend
        )
    
    def get_public_routes(self):
        """Define routes that don't require authentication."""
        return {
            "/health",           # Health check endpoint
            "/get-token",        # One-time token retrieval (can add basic auth)
            "/",                 # Root/info endpoint
        }
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """Middleware entry point."""
        # Check if this is an HTTP request
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if this is a public route
        path = scope.get("path", "/")
        if path in self.get_public_routes():
            await self.app(scope, receive, send)
            return
        
        # For MCP endpoints, check Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = None
        
        for name, value in headers.items():
            if name.lower() == b"authorization":
                auth_header = value.decode("utf-8")
                break
        
        if not auth_header:
            response = JSONResponse(
                {"error": {"code": 401, "message": "Missing Authorization header. Use 'Bearer <token>'"}},
                status_code=401
            )
            await response(scope, receive, send)
            return
        
        try:
            scheme, token = auth_header.split(" ", 1)
        except ValueError:
            response = JSONResponse(
                {"error": {"code": 401, "message": "Invalid Authorization header format"}},
                status_code=401
            )
            await response(scope, receive, send)
            return
        
        if scheme.lower() != "bearer":
            response = JSONResponse(
                {"error": {"code": 401, "message": "Unsupported authentication scheme"}},
                status_code=401
            )
            await response(scope, receive, send)
            return
        
        if not self.token_manager.validate_token(token):
            response = JSONResponse(
                {"error": {"code": 403, "message": "Invalid or expired token"}},
                status_code=403
            )
            await response(scope, receive, send)
            return
        
        # Token is valid, continue to application
        await self.app(scope, receive, send)


def initialize_auth(app_context: str = "general") -> AuthTokenManager:
    """
    Initialize authentication system based on environment.
    
    Args:
        app_context: Context identifier for logging ("docker", "heroku", "local", etc.)
    
    Returns:
        Configured AuthTokenManager
    """
    # Determine token directory based on environment
    if os.getenv("DOCKER_DEPLOYMENT") == "true":
        token_dir = Path("/data")
    elif os.getenv("HEROKU_DEPLOYMENT") == "true":
        token_dir = Path("/tmp")  # Ephemeral but works for Heroku
    else:
        # Local development - use standard config location
        token_dir = None
    
    # Create token manager
    token_manager = AuthTokenManager(token_dir)
    
    # Get or create token based on environment
    required_token = os.getenv("AUTH_TOKEN")
    
    if required_token:
        # Use provided token from environment
        logger.info("🔑 Using AUTH_TOKEN from environment")
        token_manager.save_token(required_token, "environment")
        return token_manager
    
    # Auto-generate if no token provided
    logger.info("🤖 Auto-generating MCP auth token...")
    token_manager.get_or_create_token(app_context)
    
    return token_manager