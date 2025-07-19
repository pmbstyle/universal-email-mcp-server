"""HTTP entry point for Universal Email MCP Server."""

import argparse
import asyncio

from .server import create_server


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Universal Email MCP Server - HTTP/SSE Transport"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind the server to (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )

    return parser.parse_args()


async def main():
    """Main entry point for HTTP/SSE transport."""
    args = parse_args()

    try:
        server = create_server()
        await server.run_sse(host=args.host, port=args.port)
    except KeyboardInterrupt:
        pass
    except Exception:
        raise


if __name__ == "__main__":
    asyncio.run(main())
