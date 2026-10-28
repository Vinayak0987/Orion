"""A minimal mock MCP server speaking JSON-RPC 2.0 over stdio — for tests.

Handles: initialize, notifications/initialized (no reply), tools/list, tools/call.
Reads newline-delimited JSON from stdin, writes newline-delimited JSON to stdout.
"""

import json
import sys


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get("method")
        mid = msg.get("id")
        if method == "notifications/initialized":
            continue  # notification — no response
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {}}
        elif method == "tools/list":
            result = {"tools": [
                {"name": "echo", "description": "Echo the input text", "inputSchema": {}},
                {"name": "add", "description": "Add two numbers", "inputSchema": {}},
            ]}
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "echo":
                text = str(args.get("text", ""))
            elif name == "add":
                text = str((args.get("a", 0)) + (args.get("b", 0)))
            else:
                text = "unknown tool"
            result = {"content": [{"type": "text", "text": text}]}
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
