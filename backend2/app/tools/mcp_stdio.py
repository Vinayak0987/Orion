"""stdio (local command) MCP transport.

Spawns a local MCP server as a subprocess and speaks JSON-RPC 2.0 over its
stdin/stdout (newline-delimited messages, the standard MCP stdio framing).

SECURITY: launching an arbitrary command is local code execution, so this whole
transport is gated behind settings.mcp_stdio_enabled (default OFF). Callers must
check the flag before using it.

Each operation spawns the process, does the initialize handshake, runs the
method, and terminates the process. (A short-lived process per operation keeps
lifecycle simple and avoids leaking long-running children; discovery + calls are
infrequent.) All failures raise MCPError — never a bare exception.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import uuid

from app.config import settings
from app.tools.mcp import MCPError

MCP_PROTOCOL_VERSION = "2025-06-18"
_START_TIMEOUT = 20.0
_RPC_TIMEOUT = 30.0


def _parse_command(command: str, args: list[str] | None) -> list[str]:
    """Build the argv. `command` may be a bare program or a full string; `args`
    is an optional explicit list."""
    if args:
        return [command, *args]
    # Split a full command string safely (handles quotes), posix off on Windows.
    return shlex.split(command, posix=(os.name != "nt"))


class _StdioClient:
    def __init__(self, argv: list[str], env: dict | None):
        self.argv = argv
        self.env = {**os.environ, **(env or {})}
        self.proc: asyncio.subprocess.Process | None = None

    async def __aenter__(self):
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *self.argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )
        except FileNotFoundError as e:
            raise MCPError(f"command not found: {self.argv[0]}") from e
        except Exception as e:  # noqa: BLE001
            raise MCPError(f"could not start command: {e}") from e
        return self

    async def __aexit__(self, *exc):
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.terminate()
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    self.proc.kill()
                except Exception:  # noqa: BLE001
                    pass

    async def _send(self, msg: dict) -> None:
        line = (json.dumps(msg) + "\n").encode()
        self.proc.stdin.write(line)
        await self.proc.stdin.drain()

    async def _recv_response(self, want_id: str) -> dict:
        """Read stdout lines until we get the JSON-RPC response with want_id."""
        while True:
            try:
                raw = await asyncio.wait_for(self.proc.stdout.readline(), timeout=_RPC_TIMEOUT)
            except asyncio.TimeoutError as e:
                raise MCPError("stdio MCP server timed out") from e
            if not raw:
                err = (await self.proc.stderr.read())[:300].decode("utf-8", "replace") if self.proc.stderr else ""
                raise MCPError(f"stdio MCP server closed the stream. {err}".strip())
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:  # noqa: BLE001 — ignore non-JSON log lines
                continue
            if isinstance(obj, dict) and obj.get("id") == want_id:
                if "error" in obj:
                    raise MCPError(str(obj["error"]))
                return obj.get("result", {})

    async def call(self, method: str, params: dict | None = None, *, notification: bool = False) -> dict | None:
        msg = {"jsonrpc": "2.0", "method": method}
        rid = None
        if not notification:
            rid = uuid.uuid4().hex[:8]
            msg["id"] = rid
        if params is not None:
            msg["params"] = params
        await self._send(msg)
        if notification:
            return None
        return await self._recv_response(rid)

    async def handshake(self) -> None:
        await self.call("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "Orion", "version": "2.0.0"},
        })
        try:
            await self.call("notifications/initialized", None, notification=True)
        except MCPError:
            pass


def _ensure_enabled() -> None:
    # Read the LIVE settings object (tests replace app.config.settings per-test),
    # so this reflects the current MCP_STDIO_ENABLED rather than an import-time copy.
    import app.config as _cfg

    if not _cfg.settings.mcp_stdio_enabled:
        raise MCPError("stdio MCP servers are disabled. Set MCP_STDIO_ENABLED=true to allow local command servers.")


async def discover_stdio(command: str, args: list[str] | None = None, env: dict | None = None) -> list[dict]:
    _ensure_enabled()
    argv = _parse_command(command, args)
    async with _StdioClient(argv, env) as c:
        await asyncio.wait_for(c.handshake(), timeout=_START_TIMEOUT)
        result = await c.call("tools/list")
    tools = (result or {}).get("tools")
    if not isinstance(tools, list):
        raise MCPError("stdio MCP server did not return a tools list")
    return tools


async def call_stdio(command: str, remote_name: str, arguments: dict,
                     args: list[str] | None = None, env: dict | None = None) -> dict:
    _ensure_enabled()
    argv = _parse_command(command, args)
    async with _StdioClient(argv, env) as c:
        await asyncio.wait_for(c.handshake(), timeout=_START_TIMEOUT)
        result = await c.call("tools/call", {"name": remote_name, "arguments": arguments or {}})
    content = (result or {}).get("content")
    if isinstance(content, list):
        texts = [x.get("text") for x in content if isinstance(x, dict) and x.get("type") == "text"]
        return {"content": content, "text": "\n".join(t for t in texts if t), "is_error": (result or {}).get("isError", False)}
    return {"result": result}
