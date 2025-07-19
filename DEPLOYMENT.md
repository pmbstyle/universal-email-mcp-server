# Authentication & Deployment Guide

This guide provides comprehensive instructions for setting up authentication for the Universal Email MCP Server across different deployment scenarios.

## 🔐 Authentication Overview

The server now requires Bearer token authentication for all HTTP/SSE endpoints. Tokens are automatically generated when not provided via environment variables, with persistent storage across container restarts.

## 🚀 Quick Setup Scenarios

### 1. Claude Desktop (Local Development)

**Using Docker volume mount:**

1. Create token directory:
```bash
mkdir -p ~/.claude-email-mcp
docker run -d \
  -v ~/.claude-email-mcp:/data \
  -p 8000:8000 \
  universal-email-mcp:latest
```

2. **Automated setup:**
```bash
poetry run universal-email-cli deploy claude-desktop
```

3. **Manual configuration - add to `~/.claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "universal-email": {
      "type": "mcp",
      "server_label": "secure-email",
      "transport": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer $(cat ~/.claude-email-mcp/token.txt)"
      }
    }
  }
}
```

### 2. VPS/Server Deployment

**Direct Docker run:**
```bash
# Run container
docker run -d \
  --name email-mcp \
  -v email-data:/data \
  -p 8000:8000 \
  universal-email-mcp:latest

# Get token
docker logs email-mcp | grep "🔑"
```

**With custom token:**
```bash
docker run -d \
  --name email-mcp \
  -e AUTH_TOKEN="your-secure-token" \
  -p 8000:8000 \
  universal-email-mcp:latest
```

### 3. Heroku Deployment

**1. Deploy with Heroku CLI:**
```bash
git clone <repo-url>
cd universal-email-mcp-server

# Create Heroku app
heroku create your-email-mcp

# Set authentication token
heroku config:set AUTH_TOKEN=$(openssl rand -hex 32)

# Deploy
git push heroku main

# Get deployed token
heroku config:get AUTH_TOKEN
```

**2. Configure environment variables:**
```bash
heroku config:set HEROKU_DEPLOYMENT=true
heroku config:set AUTH_TOKEN=your-secure-random-token
```

**3. Client usage:**
```json
{
  "type": "mcp",
  "server_label": "heroku-email-mcp",
  "transport": "http",
  "url": "https://your-email-mcp.herokuapp.com",
  "headers": {
    "Authorization": "Bearer $HEROKU_TOKEN"
  }
}
```

## 🛠️ Manual Token Management

### Command Line Interface

The server provides comprehensive CLI tools for all auth scenarios:

```bash
# Check current token
poetry run universal-email-cli token status

# Rotate token
poetry run universal-email-cli token rotate

# Display current token
poetry run universal-email-cli token show

# Setup specific environments
poetry run universal-email-cli deploy docker
poetry run universal-email-cli deploy heroku
poetry run universal-email-cli deploy claude-desktop
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_TOKEN` | Pre-defined authentication token | Auto-generated |
| `TOKEN_DATA_DIR` | Directory for token persistence | Varies by deployment |
| `DOCKER_DEPLOYMENT` | Enables Docker-specific setup | `false` |
| `HEROKU_DEPLOYMENT` | Enables Heroku-specific setup | `false` |

### Token Security Features

- **64-character secure tokens** using UUID + random bytes
- **File permissions**: 600 (owner-readable only)
- **Persistent storage** via Docker volumes and local filesystem
- **Backward compatibility** - tokens survive container restarts
- **Flexible rotation** via CLI or environment changes

## 🔧 API Endpoints

### Public Endpoints (No Auth)
- `GET /health` - Health check
- `GET /` - Server info (if implemented)

### Protected Endpoints (Require Bearer Token)
- `GET /sse` - SSE transport endpoint
- `POST /messages` - Message handling
- `GET /get-token` - Token retrieval (internal auth)

### Authentication Headers
```http
Authorization: Bearer your-secure-token-here
```

## 📋 Development Workflow

### 1. Local Development
```bash
# Clone and setup
git clone <repo-url>
cd universal-email-mcp-server
poetry install

# Run with CLI
poetry run universal-email-cli run --http

# Check auth setup
poetry run universal-email-cli token status
```

### 2. Testing Authentication
```bash
# In one terminal, start server
poetry run universal-email-cli run --http --port 8000

# In another terminal, test client
python -c "
from src.universal_email_mcp.client import test_auth
test_auth('http://localhost:8000')
"
```

### 3. Streaming with Authentication
```bash
echo 'your-token-from-logs' > ~/.claude-email-mcp/token.txt
```

## 🐳 Docker Deployment Variants

### Standard Docker Compose
```yaml
# docker-compose.yml
services:
  email-mcp:
    image: universal-email-mcp:latest
    ports:
      - "8000:8000"
    volumes:
      - ./dev-data:/data:rw
    environment:
      - TOKEN_DATA_DIR=/data
```

### Production Docker Compose with Volume
```yaml
services:
  email-mcp-prod:
    image: universal-email-mcp:latest
    ports:
      - "8000:8000"
    volumes:
      - email-tokens:/data:rw
      - ./logs:/app/logs:rw
    environment:
      - TOKEN_DATA_DIR=/data
      - UNIVERSAL_EMAIL_MCP_LOG_LEVEL=WARN
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

volumes:
  email-tokens:
    driver: local
```

## 🎯 Testing Authentication

### Manual Testing with curl
```bash
# Test health endpoint (no auth)
curl http://localhost:8000/health

# Test authenticated endpoint
curl -H "Authorization: Bearer $(cat ~/.claude-email-mcp/token.txt)" \
     http://localhost:8000/messages

# Test invalid token
curl -H "Authorization: Bearer invalid-token" \
     http://localhost:8000/messages
```

### Testing with Python client
```python
from src.universal_email_mcp.client import MCPClient, test_auth

# Test authentication
test_auth()

# Generate configurations
client = MCPClient()
config = client.generate_config("claude-json")
print(json.dumps(config, indent=2))
```

## 🔧 Troubleshooting

### Common Issues

**1. "Missing Authorization header"**
- Ensure your client includes the Bearer token
- Check token file exists: `ls -la ~/.claude-email-mcp/token.txt`

**2. "Invalid or expired token"**
- Token may have been rotated
- Use `poetry run universal-email-cli token show` to verify
- Regenerate with `poetry run universal-email-cli token rotate`

**3. "Permission denied: token.txt"**
- File permissions should be 600: `chmod 600 ~/.claude-email-mcp/token.txt`
- Docker volume mount may have permission issues on some systems

**4. Docker volume not persisting**
- Ensure volume is mounted correctly: `docker volume ls`
- Check container logs: `docker logs <container-id>`

### Debug Commands
```bash
# Check token existence
test -f ~/.claude-email-mcp/token.txt && echo "Token exists" || echo "Token missing"

# Display current token
cat ~/.claude-email-mcp/token.txt

# Verify Docker permissions
docker exec -it email-mcp ls -la /data/
```

## 🔄 Security Rotation

### Automated Rotation
```bash
# CLI rotation
poetry run universal-email-cli token rotate

# Docker container rotation
docker exec email-mcp sh -c "python -c 'from src.universal_email_mcp.auth import AuthTokenManager, initialize_auth; initialize_auth().rotate_token()'"
```

### Manual Rotation
```bash
# Generate new token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update environment
docker run -e AUTH_TOKEN="new-token-here" ...
```

## 📊 Monitoring

### Token Usage Monitoring
```bash
# Check token access logs
grep "MCP Auth" /var/log/docker.log

# Monitor health endpoints
curl -H "Authorization: Bearer $(cat ~/.claude-email-mcp/token.txt)" \
     http://localhost:8000/health | jq .
```