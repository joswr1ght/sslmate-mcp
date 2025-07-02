#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "mcp>=1.0.0",
#     "httpx>=0.24.0",
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
SSLMate MCP Server

A Model Context Protocol (MCP) server that provides certificate search functionality
using the SSLMate API. This server can be run in the foreground or as a daemon.

Usage:
    uv run sslmate_mcp.py [--daemon] [--config CONFIG_FILE]
    python sslmate_mcp.py [--daemon] [--config CONFIG_FILE]

Environment Variables:
    SSLMATE_API_KEY: Your SSLMate API key (required)
    MCP_PORT: Port to run the MCP server on (default: 8080)
    LOG_LEVEL: Logging level (default: INFO)
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

import httpx
from mcp import MCPServer
from mcp.types import Resource, Tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configuration
SSLMATE_API_BASE = "https://api.sslmate.com/v1"
DEFAULT_PORT = int(os.getenv("MCP_PORT", "8080"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sslmate-mcp.log") if os.getenv("LOG_TO_FILE") else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


class SSLMateCertificate(BaseModel):
    """Model for SSLMate certificate data"""
    id: str
    common_name: str
    subject_alt_names: List[str] = Field(default_factory=list)
    issuer: str
    serial_number: str
    not_before: str
    not_after: str
    fingerprint_sha1: str
    fingerprint_sha256: str
    status: str


class SSLMateClient:
    """Client for interacting with the SSLMate API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=SSLMATE_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "sslmate-mcp/0.1.0"
            },
            timeout=30.0
        )

    async def search_certificates(
        self,
        query: str,
        limit: int = 100,
        include_expired: bool = False
    ) -> List[SSLMateCertificate]:
        """Search for certificates matching the given query"""
        try:
            params = {
                "q": query,
                "limit": limit,
                "include_expired": include_expired
            }

            response = await self.client.get("/certificates/search", params=params)
            response.raise_for_status()

            data = response.json()
            certificates = []

            for cert_data in data.get("certificates", []):
                try:
                    cert = SSLMateCertificate(**cert_data)
                    certificates.append(cert)
                except Exception as e:
                    logger.warning(f"Failed to parse certificate data: {e}")
                    continue

            return certificates

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during certificate search: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during certificate search: {e}")
            raise

    async def get_certificate_details(self, cert_id: str) -> Optional[SSLMateCertificate]:
        """Get detailed information about a specific certificate"""
        try:
            response = await self.client.get(f"/certificates/{cert_id}")
            response.raise_for_status()

            data = response.json()
            return SSLMateCertificate(**data)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting certificate details: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting certificate details: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class SSLMateMCPServer:
    """MCP Server for SSLMate certificate search functionality"""

    def __init__(self, api_key: str, port: int = DEFAULT_PORT):
        self.api_key = api_key
        self.port = port
        self.sslmate_client = SSLMateClient(api_key)
        self.mcp_server = MCPServer("sslmate-mcp")
        self._setup_tools()
        self._setup_resources()

    def _setup_tools(self):
        """Setup MCP tools"""

        @self.mcp_server.tool("search_certificates")
        async def search_certificates(
            query: str,
            limit: int = 100,
            include_expired: bool = False
        ) -> Dict[str, Any]:
            """
            Search for SSL/TLS certificates using SSLMate API

            Args:
                query: Search term (domain name, organization, etc.)
                limit: Maximum number of results to return (default: 100)
                include_expired: Whether to include expired certificates (default: False)

            Returns:
                Dictionary containing search results and metadata
            """
            try:
                certificates = await self.sslmate_client.search_certificates(
                    query, limit, include_expired
                )

                return {
                    "query": query,
                    "total_results": len(certificates),
                    "certificates": [cert.model_dump() for cert in certificates],
                    "search_parameters": {
                        "limit": limit,
                        "include_expired": include_expired
                    }
                }

            except Exception as e:
                logger.error(f"Error in search_certificates tool: {e}")
                return {
                    "error": str(e),
                    "query": query
                }

        @self.mcp_server.tool("get_certificate_details")
        async def get_certificate_details(cert_id: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific certificate

            Args:
                cert_id: The certificate ID from SSLMate

            Returns:
                Dictionary containing certificate details
            """
            try:
                certificate = await self.sslmate_client.get_certificate_details(cert_id)

                if certificate:
                    return {
                        "certificate_id": cert_id,
                        "certificate": certificate.model_dump()
                    }
                else:
                    return {
                        "error": "Certificate not found",
                        "certificate_id": cert_id
                    }

            except Exception as e:
                logger.error(f"Error in get_certificate_details tool: {e}")
                return {
                    "error": str(e),
                    "certificate_id": cert_id
                }

    def _setup_resources(self):
        """Setup MCP resources"""

        @self.mcp_server.resource("sslmate://search/{query}")
        async def search_resource(query: str) -> str:
            """Resource for certificate search results"""
            try:
                certificates = await self.sslmate_client.search_certificates(query)

                result = {
                    "query": query,
                    "total_results": len(certificates),
                    "certificates": [cert.model_dump() for cert in certificates]
                }

                return json.dumps(result, indent=2)

            except Exception as e:
                return json.dumps({"error": str(e), "query": query}, indent=2)

    async def start(self):
        """Start the MCP server"""
        logger.info(f"Starting SSLMate MCP Server on port {self.port}")

        try:
            await self.mcp_server.start(port=self.port)
            logger.info("SSLMate MCP Server started successfully")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping SSLMate MCP Server")

        try:
            await self.sslmate_client.close()
            await self.mcp_server.stop()
            logger.info("SSLMate MCP Server stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")


class DaemonRunner:
    """Handle daemon mode operations"""

    def __init__(self, server: SSLMateMCPServer, pid_file: str = "/tmp/sslmate-mcp.pid"):
        self.server = server
        self.pid_file = pid_file
        self.running = True

    def _write_pid_file(self):
        """Write the current process ID to the PID file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"PID file written: {self.pid_file}")
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")

    def _remove_pid_file(self):
        """Remove the PID file"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                logger.info(f"PID file removed: {self.pid_file}")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def run_daemon(self):
        """Run the server in daemon mode"""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Write PID file
        self._write_pid_file()

        try:
            # Start the server
            await self.server.start()

            # Keep running until shutdown signal
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in daemon mode: {e}")

        finally:
            await self.server.stop()
            self._remove_pid_file()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SSLMate MCP Server")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file path"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to run server on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="SSLMate API key (overrides environment variable)"
    )

    args = parser.parse_args()

    # Load additional config if specified
    if args.config and Path(args.config).exists():
        load_dotenv(args.config)

    # Get API key
    api_key = args.api_key or os.getenv("SSLMATE_API_KEY")
    if not api_key:
        logger.error("SSLMate API key is required. Set SSLMATE_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Create server instance
    server = SSLMateMCPServer(api_key, args.port)

    try:
        if args.daemon:
            # Run in daemon mode
            daemon = DaemonRunner(server)
            await daemon.run_daemon()
        else:
            # Run in foreground
            await server.start()

            # Wait for interrupt
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
            finally:
                await server.stop()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
