"""
HTTP client utility for interacting with the authenticated MCP server.

Provides utilities for testing authenticated endpoints and client configuration.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

import httpx

from .auth import AuthTokenManager


class MCPClient:
    """HTTP client for interacting with the MCP server with authentication."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        
        if not token:
            # Try to load token from environment or file
            env_token = os.getenv("AUTH_TOKEN")
            if env_token:
                self.token = env_token
            else:
                # Try to load from filesystem
                token_manager = AuthTokenManager()
                self.token = token_manager.load_token()
                
    async def get_health(self) -> Dict[str, Any]:
        """Check server health (no auth required)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def get_token(self) -> Optional[str]:
        """Get current token (internal auth required)."""
        if not self.token:
            return None
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/get-token", 
                    headers=headers
                )
                if response.status_code == 200:
                    return response.json().get("token")
            except httpx.HTTPStatusError:
                pass
        
        return None
    
    def generate_config(self, client_type: str = "general") -> Dict[str, Any]:
        """Generate client configuration for different use cases."""
        if not self.token:
            raise ValueError("No authentication token available")
            
        base_config = {
            "base_url": self.base_url,
            "headers": {"Authorization": f"Bearer {self.token}"}
        }
        
        if client_type == "claude-json":
            return {
                "type": "mcp",
                "server_label": "secure-email",
                "command": "docker",
                "args": [
                    "run",
                    "-v", f"{Path.home()}/.claude-email-mcp:/data",
                    "universal-email-mcp:latest"
                ],
                "headers": {"Authorization": f"Bearer {self.token}"}
            }
        elif client_type == "http":
            return base_config
        elif client_type == "curl":
            return {
                "usage_example": f'curl -H "Authorization: Bearer {self.token}" {self.base_url}/health',
                "fetch_messages": f'curl -H "Authorization: Bearer {self.token}" {self.base_url}/messages',
                "sse_endpoint": f'curl -H "Authorization: Bearer {self.token}" {self.base_url}/sse"
            }
        
        return base_config


def create_claude_desktop_config() -> str:
    """Create Claude Desktop configuration template."""
    token_manager = AuthTokenManager()
    token = token_manager.load_token()
    
    if not token:
        token_manager.get_or_create_token("claude-desktop")
        token = token_manager.load_token()
    
    config_text = """
# Add this to your ~/.claude_desktop_config.json
{
  "mcpServers": {
    "universal-email": {
      "type": "mcp",
      "server_label": "secure-email",
      "transport": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer {token}"
      }
    },
    "universal-email-local": {
      "type": "mcp",
      "server_label": "secure-email-docker",
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-v", "{home}/.claude-email-mcp:/data",
        "-p", "8000:8000",
        "universal-email-mcp:latest"
      ],
      "env": {
        "TOKEN_DATA_DIR": "/data"
      },
      "headers": {
        "Authorization": "Bearer {docker_token}"
      }
    }
  }
}
""".format(
    token=token,
    docker_token=token_manager.load_token(),
    home=os.path.expanduser("~")
)

    # Save configuration
    config_dir = Path.home() / ".claude-desktop-mcp"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "universal-email-config.json"
    with open(config_file, "w") as f:
        f.write(config_text.strip())
    
    print(f"📄 Claude Desktop config saved: {config_file}")
    return config_text


def test_auth(base_url: str = "http://localhost:8000") -> bool:
    """Test authentication setup."""
    async def async_test():
        client = MCPClient(base_url)
        
        print("🧪 Testing MCP Server Authentication...")
        
        # Test health endpoint (should not require auth)
        try:
            health = await client.get_health()
            print("✅ Health check passed")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        
        # Test token status
        token_info = AuthTokenManager().get_token_info()
        if token_info["token_exists"]:
            print(f"✅ Authentication token found: {token_info['token_preview']}")
        else:
            print("❌ No authentication token found")
            return False
        
        # Test authenticated endpoints
        try:
            # This will fail gracefully without proper token
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/dmesg", 
                                          headers={"Authorization": "Bearer invalid"})
                if response.status_code == 403:
                    print("✅ Authentication middleware working correctly")
                else:
                    print(f"⚠️  Unexpected auth response: {response.status_code}")
        except Exception:
            pass
        
        return True
    
    return asyncio.run(async_test())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Client utilities")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("(" --token", help="Authentication token")
    parser.add_argument("--test", action="store_true", help="Run auth tests")
    
    args = parser.parse_args()
    
    if args.test:
        test_auth(args.url)
    else:
        # Generate Claude Desktop config
        config = create_claude_desktop_config()
        print(config)