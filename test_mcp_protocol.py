#!/usr/bin/env python3
"""
Test script for MCP protocol compliance
"""
import json
import subprocess
import sys
import time
import asyncio
from pathlib import Path

async def test_mcp_server():
    """Test the MCP server with basic protocol messages"""
    print("Testing MCP Server Protocol Compliance...")

    # Set a dummy API key for testing
    import os
    env = os.environ.copy()
    env["SSLMATE_API_KEY"] = "test_key_for_protocol_testing"

    # Start the server process
    try:
        process = subprocess.Popen(
            ["uv", "run", "sslmate_mcp.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            cwd=Path.cwd()
        )

        # Test messages
        test_messages = [
            # Initialize
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            },
            # Initialized notification
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            },
            # List tools
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            },
            # List resources
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list",
                "params": {}
            }
        ]

        responses = []

        for i, message in enumerate(test_messages):
            print(f"Sending message {i+1}: {message['method']}")

            # Send message
            message_json = json.dumps(message) + '\n'
            process.stdin.write(message_json)
            process.stdin.flush()

            # Check if process is still running
            if process.poll() is not None:
                print(f"Process exited with code: {process.returncode}")
                stderr_output = process.stderr.read()
                print(f"Stderr: {stderr_output}")
                break

            # Read response (skip for notifications)
            if "id" in message:  # Not a notification
                try:
                    # Set a timeout for reading
                    import select
                    ready, _, _ = select.select([process.stdout], [], [], 2.0)
                    if ready:
                        response_line = process.stdout.readline()
                        if response_line:
                            response = json.loads(response_line.strip())
                            responses.append(response)
                            print(f"  Response: {response}")
                        else:
                            print("  No response received")
                    else:
                        print("  Timeout waiting for response")
                except json.JSONDecodeError as e:
                    print(f"  Invalid JSON response: {e}")
                    print(f"  Raw response: {response_line}")
            else:
                print("  (notification - no response expected)")

            # Small delay between messages
            await asyncio.sleep(0.1)

        # Terminate the process
        process.terminate()
        process.wait(timeout=5)

        print(f"\nTest completed. Received {len(responses)} responses.")

        # Check stderr for any errors
        stderr_output = process.stderr.read()
        if stderr_output:
            print(f"\nServer stderr output:\n{stderr_output}")

        return len(responses) == 3  # Should get 3 responses (not 4, since one is a notification)

    except Exception as e:
        print(f"Test failed with error: {e}")
        if 'process' in locals():
            process.terminate()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
