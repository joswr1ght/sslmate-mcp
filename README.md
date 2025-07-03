# SSLMate MCP Server

> 2025-07-02 | Joshua Wright | Written with GitHub Copilot and Claude Sonnet 4

A Model Context Protocol (MCP) server that provides SSL/TLS certificate search functionality using the CertSpotter API. Search Certificate Transparency logs to discover certificates for any domain, including comprehensive subdomain discovery.

## What This Tool Does

This MCP server integrates with Claude Desktop to provide powerful certificate discovery capabilities:

- **Certificate Search**: Find SSL/TLS certificates in Certificate Transparency logs by domain name
- **Subdomain Discovery**: Search for certificates issued to all subdomains of a given domain (e.g., find all `*.example.com` certificates)
- **Detailed Information**: Get comprehensive certificate details including DNS names, issuers, validity periods, and more
- **Expired Certificate Filtering**: Option to include or exclude expired certificates from results
- **Real-time Data**: Access live Certificate Transparency log data through the CertSpotter API

## Requirements

- **Python 3.8 or later+**
- **uv** package manager ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **SSLMate API Key** (optional - free tier available at [SSLMate](https://sslmate.com/))
- **MCP CLient** (tested with Claude Desktop)

## MCP Tools

This server provides the following tool for Claude Desktop:

### `search_certificates`

Search for SSL/TLS certificates in Certificate Transparency logs.

**Parameters:**

- `domain` (string, required): The domain to search for (e.g., "example.com")
- `include_subdomains` (boolean, optional, default: false): If true, search for certificates of all subdomains
- `include_expired` (boolean, optional, default: false): If true, include expired certificates in results
- `limit` (integer, optional, default: 100): Maximum number of results to return (1-1000)

## Claude Desktop Integration

### 1. Configure Claude Desktop

Add this server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sslmate": {
      "command": "uv",
      "args": ["run", "/path/to/sslmate-mcp/sslmate_mcp.py"],
      "env": {
        "SSLMATE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 2. Restart Claude Desktop

Close and reopen Claude Desktop to load the new server.

### 3. Verify Integration

In Claude Desktop, you should now be able to ask questions like:
- "Search for certificates for example.com"
- "Find all subdomain certificates for github.com"
- "Show me expired certificates for my-domain.com"

## Troubleshooting and Logging

### Common Issues

**Server not appearing in Claude Desktop:**

1. Check the file path in `claude_desktop_config.json`
2. Ensure uv is installed and accessible
3. Verify the server starts manually: `uv run sslmate_mcp.py`

**API rate limiting:**

- Add your SSLMate API key to increase rate limits
- The free tier allows reasonable usage for most needs

**No results returned:**

- Try including subdomains: `include_subdomains=true`
- Try including expired certificates: `include_expired=true`
- Verify the domain name is correct

### Logging

The server logs to stderr by default to maintain MCP protocol compliance. To enable file logging:

```bash
export LOG_TO_FILE=1
uv run sslmate_mcp.py
```

This creates a `sslmate-mcp.log` file in the current directory.

### Testing the Server

Test the MCP protocol directly:

```bash
# Test basic functionality
python test_mcp_protocol.py

# Manual protocol test
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | uv run sslmate_mcp.py
```

## License

MIT. See LICENSE file for details.

## SSLMate API

This project uses the SSLMate API. You'll need to obtain an API key from [SSLMate](https://sslmate.com) to use this server.

For more information about the SSLMate API, visit: https://sslmate.com/api/
