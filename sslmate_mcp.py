#!/usr/bin/env python3
"""
SSLMate MCP Server

A Model Context Protocol (MCP) server that provides certificate search functionality
using the SSLMate API. This server communicates via stdio as per MCP protocol.

Usage:
    uv run sslmate_mcp.py [--config CONFIG_FILE]
    python sslmate_mcp.py [--config CONFIG_FILE]

Environment Variables:
    SSLMATE_API_KEY: Your SSLMate API key (required)
    LOG_LEVEL: Logging level (default: INFO)
"""
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "mcp>=1.0.0",
#     "httpx>=0.24.0",
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

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


# Load environment variables
load_dotenv()

# Configuration
SSLMATE_API_BASE = "https://api.certspotter.com/v1"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Setup logging - IMPORTANT: Never log to stdout as it interferes with JSON-RPC
handlers = [logging.StreamHandler(sys.stderr)]  # Always use stderr

# Only add file handler if explicitly requested and possible
if os.getenv("LOG_TO_FILE"):
    try:
        # Try to create log file in a writable location
        log_file = os.path.expanduser("~/sslmate-mcp.log") if os.path.expanduser("~") != "~" else "/tmp/sslmate-mcp.log"
        handlers.append(logging.FileHandler(log_file))
    except (OSError, PermissionError):
        # If file logging fails, just continue with stderr only
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers
)
logger = logging.getLogger(__name__)


class SSLMateCertificate(BaseModel):
    """Model for SSLMate certificate issuance data"""
    id: str
    tbs_sha256: str
    cert_sha256: Optional[str] = None
    dns_names: Optional[List[str]] = Field(default_factory=list)
    pubkey_sha256: str
    not_before: str
    not_after: str
    revoked: Optional[bool] = None
    issuer: Optional[Dict[str, Any]] = None

    # For backward compatibility with expected interface
    @property
    def common_name(self) -> str:
        """Get the primary domain name"""
        if self.dns_names:
            return self.dns_names[0]
        return "unknown"

    @property
    def subject_alt_names(self) -> List[str]:
        """Get subject alternative names"""
        return self.dns_names or []

    @property
    def issuer_name(self) -> str:
        """Get issuer friendly name"""
        if self.issuer and "friendly_name" in self.issuer:
            return self.issuer["friendly_name"]
        return "unknown"

    @property
    def fingerprint_sha256(self) -> str:
        """Get SHA256 fingerprint"""
        return self.cert_sha256 or "unknown"

    @property
    def status(self) -> str:
        """Get certificate status"""
        if self.revoked is True:
            return "revoked"
        elif self.revoked is False:
            return "valid"
        else:
            return "unknown"


class SSLMateClient:
    """Client for interacting with the SSLMate API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        headers = {"User-Agent": "sslmate-mcp/0.1.0"}

        # Only add authorization if API key is provided and not a test key
        if api_key and api_key != "test" and not api_key.startswith("test_"):
            headers["Authorization"] = f"Bearer {api_key}"

        self.client = httpx.AsyncClient(
            base_url=SSLMATE_API_BASE,
            headers=headers,
            timeout=30.0
        )

    async def search_certificates(
        self,
        query: str,
        limit: int = 100,
        include_expired: bool = False,
        include_subdomains: bool = False
    ) -> List[SSLMateCertificate]:
        """Search for certificate issuances matching the given domain"""
        try:
            # Build params with multiple expand parameters
            params = [
                ("domain", query),
                ("expand", "dns_names"),
                ("expand", "issuer")
            ]

            # Add include_subdomains parameter if requested
            if include_subdomains:
                params.append(("include_subdomains", "true"))

            # Note: The CertSpotter API doesn't have a direct limit parameter
            # We'll fetch results and limit them client-side

            response = await self.client.get("/issuances", params=params)
            response.raise_for_status()

            data = response.json()
            certificates = []

            # data is a list of issuance objects
            for cert_data in data:
                try:
                    # Skip expired certificates if requested
                    if not include_expired:
                        from datetime import datetime, timezone
                        not_after = datetime.fromisoformat(cert_data.get("not_after", "").replace("Z", "+00:00"))
                        if not_after < datetime.now(timezone.utc):
                            continue

                    cert = SSLMateCertificate(**cert_data)
                    certificates.append(cert)

                    # Apply client-side limit
                    if len(certificates) >= limit:
                        break

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
        """Get detailed information about a specific certificate issuance by ID"""
        try:
            # The CertSpotter API doesn't have a direct "get by ID" endpoint
            # We'll need to search and filter by the ID
            # This is a limitation of the current implementation
            # For now, we'll return an error indicating this functionality isn't available
            logger.warning(f"Certificate details by ID not supported by CertSpotter API: {cert_id}")
            return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting certificate details: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting certificate details: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class MCPServer:
    """Simple MCP server implementation using stdio"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools = {}
        self.resources = {}
        self.running = False

    def add_tool(self, name: str, description: str, parameters: dict, handler):
        """Add a tool to the server"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": parameters,
                "required": list(parameters.keys())
            },
            "handler": handler
        }

    def add_resource(self, uri_template: str, description: str, handler):
        """Add a resource to the server"""
        self.resources[uri_template] = {
            "uri": uri_template,
            "description": description,
            "handler": handler
        }

    async def handle_request(self, request: dict) -> dict:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Check if this is a notification (no id field)
        is_notification = "id" not in request

        try:
            if method == "initialize":
                result = {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": self.version
                        }
                    }
                }
                # Only include id for non-notifications
                if not is_notification:
                    result["id"] = request_id
                return result

            elif method == "notifications/initialized":
                # This is a notification, no response needed
                return None

            elif method == "tools/list":
                tools_list = []
                for tool_name, tool_info in self.tools.items():
                    tools_list.append({
                        "name": tool_info["name"],
                        "description": tool_info["description"],
                        "inputSchema": tool_info["inputSchema"]
                    })

                result = {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": tools_list
                    }
                }
                if not is_notification:
                    result["id"] = request_id
                return result

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name in self.tools:
                    handler = self.tools[tool_name]["handler"]
                    result = await handler(**arguments)

                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Tool not found: {tool_name}"
                        }
                    }

            elif method == "resources/list":
                resources_list = []
                for resource_uri, resource_info in self.resources.items():
                    resources_list.append({
                        "uri": resource_info["uri"],
                        "description": resource_info["description"]
                    })

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "resources": resources_list
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

    async def run_stdio(self):
        """Run the server using stdio for communication"""
        self.running = True
        logger.info(f"Starting {self.name} MCP server")

        try:
            while self.running:
                try:
                    # Read a line from stdin (blocking)
                    line = input()
                    if not line.strip():
                        continue

                    # Parse JSON request
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Only send response if not None (notifications don't get responses)
                    if response is not None:
                        response_json = json.dumps(response, separators=(',', ':'))
                        print(response_json, flush=True)

                except EOFError:
                    # stdin closed
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    response_json = json.dumps(error_response, separators=(',', ':'))
                    print(response_json, flush=True)

                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": "Internal error"
                        }
                    }
                    response_json = json.dumps(error_response, separators=(',', ':'))
                    print(response_json, flush=True)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error in stdio loop: {e}")
        finally:
            self.running = False
            logger.info("MCP server stopped")


class SSLMateMCPServer:
    """MCP Server for SSLMate certificate search functionality"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.sslmate_client = SSLMateClient(api_key)
        self.mcp_server = MCPServer("sslmate-mcp", "0.1.0")
        self._setup_tools()
        self._setup_resources()

    def _setup_tools(self):
        """Setup MCP tools"""

        async def search_certificates_handler(query: str, limit: int = 100, include_expired: bool = False, include_subdomains: bool = False):
            """Handler for certificate search tool"""
            try:
                certificates = await self.sslmate_client.search_certificates(
                    query, limit, include_expired, include_subdomains
                )

                return {
                    "query": query,
                    "total_results": len(certificates),
                    "certificates": [cert.model_dump() for cert in certificates],
                    "search_parameters": {
                        "limit": limit,
                        "include_expired": include_expired,
                        "include_subdomains": include_subdomains
                    }
                }

            except Exception as e:
                logger.error(f"Error in search_certificates tool: {e}")
                return {
                    "error": str(e),
                    "query": query
                }

        async def get_certificate_details_handler(cert_id: str):
            """Handler for certificate details tool"""
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

        # Add tools to the MCP server
        self.mcp_server.add_tool(
            "search_certificates",
            "Search for SSL/TLS certificates using SSLMate Certificate Transparency API",
            {
                "query": {"type": "string", "description": "Domain name to search for certificates"},
                "limit": {"type": "integer", "description": "Maximum number of results (default: 100)", "default": 100},
                "include_expired": {"type": "boolean", "description": "Include expired certificates (default: false)", "default": False},
                "include_subdomains": {"type": "boolean", "description": "Include certificates for subdomains (default: false)", "default": False}
            },
            search_certificates_handler
        )

        self.mcp_server.add_tool(
            "get_certificate_details",
            "Get detailed information about a specific certificate",
            {
                "cert_id": {"type": "string", "description": "Certificate ID from SSLMate"}
            },
            get_certificate_details_handler
        )

    def _setup_resources(self):
        """Setup MCP resources"""

        async def search_resource_handler(query: str, include_subdomains: bool = False):
            """Handler for certificate search resource"""
            try:
                certificates = await self.sslmate_client.search_certificates(
                    query, include_subdomains=include_subdomains
                )

                result = {
                    "query": query,
                    "total_results": len(certificates),
                    "certificates": [cert.model_dump() for cert in certificates],
                    "search_parameters": {
                        "include_subdomains": include_subdomains
                    }
                }

                return json.dumps(result, indent=2)

            except Exception as e:
                return json.dumps({"error": str(e), "query": query}, indent=2)

        self.mcp_server.add_resource(
            "sslmate://search/{query}",
            "Certificate search results",
            search_resource_handler
        )

    async def start(self):
        """Start the MCP server"""
        logger.info("Starting SSLMate MCP Server")

        try:
            await self.mcp_server.run_stdio()

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping SSLMate MCP Server")

        try:
            await self.sslmate_client.close()
            self.mcp_server.running = False
            logger.info("SSLMate MCP Server stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SSLMate MCP Server")
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file path"
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
    server = SSLMateMCPServer(api_key)

    try:
        # Run the MCP server
        await server.start()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
