# SSLMate MCP Server

An MCP (Model Context Protocol) server that provides certificate search fu```bash
export SSLMATE_API_KEY="your-sslmate-api-key"
export LOG_LEVEL="INFO"  # Optional, defaults to INFO
```

Alternatively, create a `.env` file:

```env
SSLMATE_API_KEY=your-sslmate-api-key
LOG_LEVEL=INFO
```sing the SSLMate API.

## Features

- Search SSL/TLS certificates by domain name, organizati# Set your API key
export SSLMATE      ],
      "env": {
        "SSLMATE_API_KEY": "your-sslmate-api-key",
        "LOG_LEVEL": "INFO"
      }E#### Server Not Starting
- Check th2. **Run the server manually first:**
   ```bash
   uv run sslmate_mcp.py
   # The server will wait for JSON-RPC input via stdio
   ```

3. **Check Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%LOCALAPPDATA%\Claude\logs\`

4. **Test MCP protocol manually (advanced):**
   ```bash
   echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}},"id":1}' | uv run sslmate_mcp.py
   ```API key is correct
- Verify the script path in Claude Desktop configuration is correct
- Check the logs in the Claude Desktop developer tools

#### Tools Not Appearing in Claude
- Verify the path in the configuration file is absolute and correct
- Check that `uv` is installed and available in your PATH
- Restart Claude Desktop after making configuration changes
- Check Claude Desktop's MCP logs for error messageslmate-api-key"

# Test the server (it will communicate via stdio)
uv run sslmate_mcp.py
```

**Note**: The MCP server uses stdio for communication, so when you run it directly, it will wait for JSON-RPC input. To test it properly, use it through Claude Desktop or another MCP client.ther criteria
- Get detailed certificate information
- Run in foreground or daemon mode
- Single file deployment for easy management
- Built with modern Python async/await patterns
- Comprehensive logging and error handling

## Requirements

- Python 3.8+
- SSLMate API key
- uv (for package management)

## Installation

### Option 1: Quick Start with uv (Automatic Dependencies)

The Python script includes inline dependency metadata, so you can run it directly with uv and it will automatically install dependencies:

    ```bash
    # Clone the repository
    git clone <repository-url>
    cd sslmate-mcp

    # Run directly - uv will automatically install dependencies
    uv run sslmate_mcp.py
    ```

This is the easiest way to get started! uv will create an isolated environment and install all required dependencies automatically.

### Option 2: Manual Installation with Virtual Environment

1. Clone this repository:
    ```bash
    git clone <repository-url>
    cd sslmate-mcp
    ```

2. Set up the environment and install dependencies using uv:

   ```bash
   # Create a virtual environment
   uv venv

   # Activate the virtual environment
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows

   # Install the project and dependencies
   uv pip install -e .
   ```

## Configuration

Set up your environment variables:

```bash
export SSLMATE_API_KEY="your-sslmate-api-key"
export MCP_PORT="3010"  # Optional, defaults to 3010
export LOG_LEVEL="INFO"  # Optional, defaults to INFO
```

Alternatively, create a `.env` file:

```env
SSLMATE_API_KEY=your-sslmate-api-key
MCP_PORT=3010
LOG_LEVEL=INFO
```

## Usage

### Quick Start with uv (Recommended):
```bash
# Run the MCP server - it will communicate via stdio
uv run sslmate_mcp.py

# Use custom configuration file
uv run sslmate_mcp.py --config /path/to/config.env
```

### Traditional Python execution:
```bash
# Run the MCP server (requires manual dependency installation)
python sslmate_mcp.py

# Use custom configuration file
python sslmate_mcp.py --config /path/to/config.env
```

**Note**: This MCP server communicates via standard input/output (stdio) as per the MCP protocol specification. It is designed to be used with MCP clients like Claude Desktop rather than accessed directly via HTTP.

## MCP Tools

The server provides the following MCP tools via the standard MCP protocol:

### `search_certificates`
Search for SSL/TLS certificates using various criteria.

**Parameters:**
- `query` (string): Search term (domain name, organization, etc.)
- `limit` (int, optional): Maximum number of results (default: 100)
- `include_expired` (bool, optional): Include expired certificates (default: false)

### `get_certificate_details`
Get detailed information about a specific certificate.

**Parameters:**
- `cert_id` (string): The certificate ID from SSLMate

## MCP Resources

### `sslmate://search/{query}`
Resource endpoint for certificate search results.

## Development

### Install development dependencies:
```bash
# If using virtual environment (recommended)
source .venv/bin/activate  # Activate if not already active
uv pip install -e ".[dev]"

# Or install system-wide
uv pip install -e ".[dev]" --system
```

### Run tests:
```bash
pytest
```

### Code formatting:
```bash
black sslmate_mcp.py
ruff check sslmate_mcp.py
```

### Type checking:
```bash
mypy sslmate_mcp.py
```

## Logging

Logs are written to stdout by default. To enable file logging, set the `LOG_TO_FILE` environment variable:

```bash
export LOG_TO_FILE=1
```

This will create a `sslmate-mcp.log` file in the current directory.

## Daemon Mode

When running in daemon mode:
- A PID file is created at `/tmp/sslmate-mcp.pid`
- The process responds to SIGTERM and SIGINT for graceful shutdown
- Logs are essential for monitoring since there's no interactive output

## Error Handling

The server includes comprehensive error handling:
- API rate limiting and retry logic
- Graceful degradation when SSLMate API is unavailable
- Input validation for all parameters
- Detailed logging for debugging

## Security Considerations

- API keys are loaded from environment variables or config files
- No sensitive information is logged
- Input validation prevents injection attacks
- HTTPS is used for all SSLMate API communications

## Claude Desktop Integration

This SSLMate MCP server can be integrated with Claude Desktop to provide certificate search functionality directly within your Claude conversations.

### Prerequisites

1. **Claude Desktop** - Download and install from [Claude.ai](https://claude.ai/download)
2. **SSLMate API Key** - Obtain from [SSLMate](https://sslmate.com)
3. **uv** - Install from [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup Steps

#### 1. Clone and Test the Server

```bash
# Clone the repository
git clone <repository-url>
cd sslmate-mcp

# Set your API key
export SSLMATE_API_KEY="your-sslmate-api-key"

# Test the server (it should start on port 3010)
uv run sslmate_mcp.py
```

Verify the server is working by visiting `http://localhost:3010` in your browser.

#### 2. Configure Claude Desktop

Claude Desktop uses a configuration file to connect to MCP servers. The location depends on your operating system:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Create or edit this file with the following configuration:

```json
{
  "mcpServers": {
    "sslmate": {
      "command": "uv",
      "args": [
        "run",
        "/full/path/to/sslmate-mcp/sslmate_mcp.py"
      ],
      "env": {
        "SSLMATE_API_KEY": "your-sslmate-api-key",
        "MCP_PORT": "3010",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Important**: Replace `/full/path/to/sslmate-mcp/sslmate_mcp.py` with the actual absolute path to your script.

#### 3. Alternative Configuration Options

**Option A: Using environment variables from shell**
```json
{
  "mcpServers": {
    "sslmate": {
      "command": "uv",
      "args": [
        "run",
        "/full/path/to/sslmate-mcp/sslmate_mcp.py"
      ]
    }
  }
}
```
*Note: This requires setting `SSLMATE_API_KEY` in your system environment.*

**Option B: Using a config file**
```json
{
  "mcpServers": {
    "sslmate": {
      "command": "uv",
      "args": [
        "run",
        "/full/path/to/sslmate-mcp/sslmate_mcp.py",
        "--config",
        "/full/path/to/sslmate-mcp/.env"
      ]
    }
  }
}
```

**Option C: Using system Python (if dependencies are installed)**
```json
{
  "mcpServers": {
    "sslmate": {
      "command": "python3",
      "args": ["/full/path/to/sslmate-mcp/sslmate_mcp.py"],
      "env": {
        "SSLMATE_API_KEY": "your-sslmate-api-key"
      }
    }
  }
}
```

#### 4. Restart Claude Desktop

After updating the configuration file, restart Claude Desktop completely:

1. Quit Claude Desktop
2. Wait a few seconds
3. Relaunch Claude Desktop

#### 5. Verify Integration

Once Claude Desktop restarts, you should see the SSLMate MCP server tools available. You can test the integration by asking Claude questions like:

- "Search for certificates for example.com"
- "Find SSL certificates issued to Google"
- "Show me certificates for *.github.com"

### Usage in Claude Desktop

Once integrated, you can use natural language to interact with the certificate search functionality:

#### Example Queries

**Basic Certificate Search:**
```
Search for SSL certificates for "example.com"
```

**Advanced Search with Filters:**
```
Find certificates for "google.com" including expired ones, limit to 25 results
```

**Get Certificate Details:**
```
Get details for certificate ID "cert-12345"
```

**Domain Wildcard Search:**
```
Search for certificates for "*.github.com"
```

### Troubleshooting

#### Server Not Starting
- Check that your SSLMate API key is correct
- Verify that port 3010 is not in use by another application
- Check the logs in the Claude Desktop developer tools

#### Tools Not Appearing in Claude
- Verify the path in the configuration file is absolute and correct
- Check that `uv` is installed and available in your PATH
- Restart Claude Desktop after making configuration changes
- Check Claude Desktop's MCP logs for error messages

#### API Errors
- Verify your SSLMate API key is valid and has sufficient quota
- Check your internet connection
- Review the server logs for specific error messages

### Development and Debugging

To debug MCP integration issues:

1. **Enable file logging:**
   ```bash
   export LOG_TO_FILE=1
   uv run sslmate_mcp.py
   ```

2. **Run the server manually first:**
   ```bash
   uv run sslmate_mcp.py
   # Test at http://localhost:3010
   ```

3. **Check Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%LOCALAPPDATA%\Claude\logs\`

4. **Test server endpoints directly:**
   ```bash
   curl -X POST http://localhost:3010/tools/search_certificates \
     -H "Content-Type: application/json" \
     -d '{"query": "example.com"}'
   ```

### Security Notes

- Store your SSLMate API key securely
- Consider using environment variables instead of hardcoding keys in config files
- The server runs locally and does not expose your API key to external services
- All communication with SSLMate API uses HTTPS

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite and linting
6. Submit a pull request

## License

See LICENSE file for details.

## SSLMate API

This project uses the SSLMate API. You'll need to obtain an API key from [SSLMate](https://sslmate.com) to use this server.

For more information about the SSLMate API, visit: https://sslmate.com/api/
