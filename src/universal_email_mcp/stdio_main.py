"""STDIO entry point for Universal Email MCP Server."""

import asyncio

from .server import create_server


async def main():
    """Main entry point for STDIO transport."""
    try:
        server = create_server()
        await server.run_stdio()
    except KeyboardInterrupt:
        pass
    except Exception:
        raise


if __name__ == "__main__":
    asyncio.run(main())