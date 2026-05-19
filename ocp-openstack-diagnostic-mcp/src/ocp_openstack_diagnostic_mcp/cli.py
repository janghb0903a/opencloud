from __future__ import annotations

import argparse
import logging

from .server import run_http, run_stdio


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only OpenStack diagnostic MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(message)s")
    if args.transport == "stdio":
        run_stdio()
    else:
        run_http(host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    main()

