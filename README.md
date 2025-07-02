# SSLMate MCP Server

An MCP (Model Context Protocol) server that provides certificate search functionality using the SSLMate API.

## Features

- Search SSL/TLS certificates by domain name, organization, or other criteria
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
export MCP_PORT="8080"  # Optional, defaults to 8080
export LOG_LEVEL="INFO"  # Optional, defaults to INFO
```

Alternatively, create a `.env` file:

```env
SSLMATE_API_KEY=your-sslmate-api-key
MCP_PORT=8080
LOG_LEVEL=INFO
```

## Usage

### Quick Start with uv (Recommended):
```bash
# Run in foreground with automatic dependency management
uv run sslmate_mcp.py

# Run as daemon
uv run sslmate_mcp.py --daemon

# Specify custom port
uv run sslmate_mcp.py --port 9000

# Use custom configuration file
uv run sslmate_mcp.py --config /path/to/config.env
```

### Traditional Python execution:
```bash
# Run in foreground (requires manual dependency installation)
python sslmate_mcp.py

# Run as daemon
python sslmate_mcp.py --daemon

# Specify custom port
python sslmate_mcp.py --port 9000

# Use custom configuration file
python sslmate_mcp.py --config /path/to/config.env
```

## MCP Tools

The server provides the following MCP tools:

### `search_certificates`
Search for SSL/TLS certificates using various criteria.

**Parameters:**
- `query` (string): Search term (domain name, organization, etc.)
- `limit` (int, optional): Maximum number of results (default: 100)
- `include_expired` (bool, optional): Include expired certificates (default: false)

**Example:**
```json
{
  "tool": "search_certificates",
  "arguments": {
    "query": "example.com",
    "limit": 50,
    "include_expired": false
  }
}
```

### `get_certificate_details`
Get detailed information about a specific certificate.

**Parameters:**
- `cert_id` (string): The certificate ID from SSLMate

**Example:**
```json
{
  "tool": "get_certificate_details",
  "arguments": {
    "cert_id": "cert-12345"
  }
}
```

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
