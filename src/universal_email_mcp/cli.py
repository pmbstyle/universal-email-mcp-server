"""
Command-line interface for managing the Universal Email MCP Server.

Provides utilities for token management, configuration, and deployment setup.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .auth import AuthTokenManager, initialize_auth
from .server import create_server


def setup_docker():
    """Setup for Docker deployment."""
    token_manager = AuthTokenManager(Path("/data"))
    token = token_manager.get_or_create_token("docker")
    
    print("🐳 Docker-ready setup complete!")
    print(f"🔐 Token: {token}")
    print(f"📁 Token file: /data/{token_manager.TOKEN_FILE_NAME}")
    
    # Generate Docker Compose example
    compose_example = {
        "version": "3.8",
        "services": {
            "email-mcp": {
                "image": "universal-email-mcp:latest",
                "ports": ["8000:8000"],
                "volumes": [
                    "email-data:/data",
                    "~/.claude-email-mcp:/data"  # Also mount for Claude Desktop
                ],
                "environment": {
                    "TOKEN_DATA_DIR": "/data"
                }
            }
        },
        "volumes": {
            "email-data": None
        }
    }
    
    with open("docker-compose.custom.yml", "w") as f:
        json.dump(compose_example, f, indent=2)
    
    print("📄 Docker compose file created: docker-compose.custom.yml")


def setup_heroku():
    """Setup for Heroku deployment."""
    print("🌿 Heroku deployment setup:")
    print(
        """
    # 1. Set up Heroku config
    heroku create your-email-mcp
    
    # 2. Generate token and set as config var
    heroku config:set AUTH_TOKEN=$(openssl rand -hex 32)
    
    # 3. Deploy (see heroku.yml)
    git push heroku main
    
    # 4. Get token after deployment
    heroku config:get AUTH_TOKEN
        """
    )
    
    # Create heroku.yml
    heroku_yml = {
        "build": {"docker": {"web": "Dockerfile"}},
        "run": {
            "web": "python -m universal_email_mcp.http_main --host 0.0.0.0 --port $PORT"
        }
    }
    
    with open("heroku.yml", "w") as f:
        json.dump(heroku_yml, f, indent=2)
    
    # Create .env.example
    env_example = {
        "AUTH_TOKEN": "your-secure-token-here",
        "HEROKU_DEPLOYMENT": "true"
    }
    
    with open(".env.example", "w") as f:
        for key, value in env_example.items():
            f.write(f"{key}={value}\n")
    
    print("📄 Created deployment files: heroku.yml, .env.example")


def setup_claude_desktop():
    """Setup for Claude Desktop integration."""
    token_manager = AuthTokenManager()
    token = token_manager.get_or_create_token("claude-desktop")
    
    # Get the token file path relative to home
    token_file_path = os.path.expanduser("~/.config/universal_email_mcp/tokens/token.txt")
    
    claude_config = {
        "mcpServers": {
            "secure-email": {
                "command": "docker",
                "args": [
                    "run", 
                    "-v", f"{os.path.expanduser('~/.claude-email-mcp')}:/data",
                    "-v", f"{os.path.expanduser('~/.config/universal_email_mcp')}:/home/mcpuser/.config/universal_email_mcp",
                    "universal-email-mcp:latest",
                    "python", "-m", "universal_email_mcp.http_main", 
                    "--host", "0.0.0.0", 
                    "--port", "8000"
                ],
                "env": {
                    "TOKEN_DATA_DIR": "/data"
                },
                "headers": {
                    "Authorization": f"Bearer {token}"
                }
            }
        }
    }
    
    print("🖥️  Claude Desktop configuration:")
    print("Add this to ~/.claude_desktop_config.json:")
    print(json.dumps(claude_config, indent=2))
    
    # Save local integration file
    integration = {
        "token": token,
        "token_file": str(token_manager.token_path),
        "claude_json_path": "~/.claude_desktop_config.json"
    }
    
    with open("claude-desktop-setup.json", "w") as f:
        json.dump(integration, f, indent=2)
        
    print("\n📄 Local integration file: claude-desktop-setup.json")


def cli_main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Universal Email MCP Server CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s token status              - Check token status
  %(prog)s token rotate              - Generate new token
  %(prog)s deploy docker             - Setup Docker deployment
  %(prog)s deploy heroku             - Setup Heroku deployment
  %(prog)s deploy claude-desktop     - Setup Claude Desktop integration
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Token management
    token_parser = subparsers.add_parser("token", help="Token management")
    token_subparsers = token_parser.add_subparsers(dest="token_action")
    
    token_subparsers.add_parser("status", help="Show token status")
    token_subparsers.add_parser("rotate", help="Generate new token")
    token_subparsers.add_parser("show", help="Display current token")
    
    # Deployment setup
    deploy_parser = subparsers.add_parser("deploy", help="Deployment setup")
    deploy_subparsers = deploy_parser.add_subparsers(dest="deploy_target")
    
    deploy_subparsers.add_parser("docker", help="Setup Docker deployment")
    deploy_subparsers.add_parser("heroku", help="Setup Heroku deployment")
    deploy_subparsers.add_parser("claude-desktop", help="Setup Claude Desktop integration")
    
    # Server commands
    run_parser = subparsers.add_parser("run", help="Run MCP server")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--stdio", action="store_true", help="Run with stdio transport")
    run_group.add_argument("--http", action="store_true", help="Run with HTTP transport")
    
    run_parser.add_argument("--host", default="localhost", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--token", help="Override authentication token")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "token":
            token_manager = AuthTokenManager()
            
            if args.token_action == "status":
                info = token_manager.get_token_info()
                print(json.dumps(info, indent=2))
                
            elif args.token_action == "rotate":
                new_token = token_manager.rotate_token("cli")
                print(f"🔄 New token: {new_token}")
                
            elif args.token_action == "show":
                token = token_manager.load_token()
                if token:
                    print(f"🔐 Token: {token}")
                    print(f"📁 File: {token_manager.token_path}")
                else:
                    print("❌ No token found")
                    
        elif args.command == "deploy":
            if args.deploy_target == "docker":
                setup_docker()
            elif args.deploy_target == "heroku":
                setup_heroku()
            elif args.deploy_target == "claude-desktop":
                setup_claude_desktop()
                
        elif args.command == "run":
            # Set token if provided
            if args.token:
                os.environ["AUTH_TOKEN"] = args.token
                print(f"🔑 Using provided token: {args.token}")
            
            # Initialize auth
            initialize_auth("cli")
            
            server = create_server()
            
            if args.stdio:
                asyncio.run(server.run_stdio())
            elif args.http:
                asyncio.run(server.run_sse(args.host, args.port))
    
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()