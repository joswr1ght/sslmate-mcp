sslmate-mcp will use the [SSLMate](https://sslmate.com) API to identify certificates for matching search terms.
As an MCP server, it will integrate using SSE to provide search tools to MCP clients to identify certificates that match search terms.

The Python script will be run in the foreground or as a daemon.
The Python script will be a single file for ease of deployment.
The Python script will use uv for Python package management and running the server.
