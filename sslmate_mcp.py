#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "mcp>=1.0.0",
#     "httpx>=0.24.0",
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "fastapi>=0.104.0",
#     "uvicorn>=0.24.0",
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
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn


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


class MCPRequest(BaseModel):
    """Model for MCP requests"""
    method: str
    params: dict = Field(default_factory=dict)


class MCPResponse(BaseModel):
    """Model for MCP responses"""
    result: dict = Field(default_factory=dict)
    error: Optional[dict] = None


class SSLMateMCPServer:
    """MCP Server for SSLMate certificate search functionality"""

    def __init__(self, api_key: str, port: int = DEFAULT_PORT):
        self.api_key = api_key
        self.port = port
        self.sslmate_client = SSLMateClient(api_key)
        self.app = FastAPI(title="SSLMate MCP Server", version="0.1.0")
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes for MCP protocol"""

        @self.app.get("/")
        async def root():
            """Root endpoint with server information"""
            return {
                "name": "sslmate-mcp",
                "version": "0.1.0",
                "description": "SSLMate MCP Server for certificate search",
                "tools": [
                    {
                        "name": "search_certificates",
                        "description": "Search for SSL/TLS certificates",
                        "parameters": {
                            "query": {"type": "string", "description": "Search term"},
                            "limit": {"type": "integer", "default": 100},
                            "include_expired": {"type": "boolean", "default": False}
                        }
                    },
                    {
                        "name": "get_certificate_details",
                        "description": "Get certificate details",
                        "parameters": {
                            "cert_id": {"type": "string", "description": "Certificate ID"}
                        }
                    }
                ],
                "resources": [
                    {
                        "uri": "sslmate://search/{query}",
                        "description": "Certificate search results"
                    }
                ]
            }

        @self.app.post("/tools/search_certificates")
        async def search_certificates_tool(request: dict):
            """Tool endpoint for certificate search"""
            try:
                query = request.get("query", "")
                limit = request.get("limit", 100)
                include_expired = request.get("include_expired", False)

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
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/tools/get_certificate_details")
        async def get_certificate_details_tool(request: dict):
            """Tool endpoint for certificate details"""
            try:
                cert_id = request.get("cert_id", "")
                if not cert_id:
                    raise HTTPException(status_code=400, detail="cert_id is required")

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

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in get_certificate_details tool: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/resources/sslmate/search/{query}")
        async def search_resource(query: str):
            """Resource endpoint for certificate search"""
            try:
                certificates = await self.sslmate_client.search_certificates(query)

                result = {
                    "query": query,
                    "total_results": len(certificates),
                    "certificates": [cert.model_dump() for cert in certificates]
                }

                return result

            except Exception as e:
                logger.error(f"Error in search resource: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def start(self):
        """Start the MCP server"""
        logger.info(f"Starting SSLMate MCP Server on port {self.port}")

        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level=LOG_LEVEL.lower()
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
            logger.info("SSLMate MCP Server started successfully")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping SSLMate MCP Server")

        try:
            await self.sslmate_client.close()
            logger.info("SSLMate MCP Server stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")


class DaemonRunner:
    """Handle daemon mode operations"""

    def __init__(self, server: SSLMateMCPServer, pid_file: str = "/tmp/sslmate-mcp.pid"):
        self.server = server
        self.pid_file = pid_file
        self.running = True
        self.server_task = None

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
        if self.server_task:
            self.server_task.cancel()

    async def run_daemon(self):
        """Run the server in daemon mode"""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Write PID file
        self._write_pid_file()

        try:
            # Start the server as a background task
            self.server_task = asyncio.create_task(self.server.start())

            # Keep running until shutdown signal
            while self.running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Server task cancelled")
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
            server_task = asyncio.create_task(server.start())

            # Wait for interrupt
            try:
                await server_task
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
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
