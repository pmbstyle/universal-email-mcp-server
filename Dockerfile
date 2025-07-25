FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    mcp>=1.2.0 \
    pydantic>=2.8.2 \
    starlette>=0.39.0 \
    uvicorn>=0.32.0 \
    aioimaplib>=2.0.1 \
    aiosmtplib>=4.0.0 \
    pydantic-settings[toml]>=2.8.0 \
    tomli-w>=1.2.0 \
    cryptography>=42.0.0 \
    keyring>=25.0.0 \
    loguru>=0.7.3

COPY src/ ./src/

RUN chown -R mcpuser:mcpuser /app

RUN mkdir -p /home/mcpuser/.config/universal_email_mcp && \
    chown -R mcpuser:mcpuser /home/mcpuser/.config

ENV PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create data directory for token persistence (as root)
RUN mkdir -p /data && \
    chown -R mcpuser:mcpuser /data && \
    chmod 755 /data

USER mcpuser

EXPOSE 8000

# Environment variables for auth
ENV TOKEN_DATA_DIR="/data" \
    DOCKER_DEPLOYMENT="true" \
    AUTH_TOKEN=""

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import universal_email_mcp; print('OK')" || exit 1

CMD ["python", "-m", "universal_email_mcp.http_main", "--host", "0.0.0.0", "--port", "8000"]