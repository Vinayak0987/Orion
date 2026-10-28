"""Local Database (5) + General Utilities (10) built-in tools.

Local DB tools operate on a dedicated sandboxed SQLite file in the workspace
(agents can't touch the app's own DB) plus the shared kv_store table for
key_value_store / local_cache. Utilities are stdlib-only encode/hash/parse/net
helpers.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import socket
import sqlite3
import uuid as _uuid
from urllib.parse import parse_qs, urlparse

import httpx

from app.db.sqlite import _now, connection
from app.tools.base import ToolContext, err, need, ok, tool
from app.tools.sandbox import SandboxError, rel_to_workspace, safe_path, valid_url

# ============================================================================
# Local Database (5)
# ============================================================================

_READONLY_PREFIXES = ("select", "with", "pragma", "explain")


def _agent_db(ti: dict) -> sqlite3.Connection:
    """Open a sandboxed SQLite file in the workspace (default agent.db)."""
    name = ti.get("database") or "agent.db"
    p = safe_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


# --- 181. sqlite_tool --------------------------------------------------------
@tool(
    "sqlite_tool",
    description="Run SQL against a sandboxed SQLite database in the workspace. SELECT returns rows; "
    "write statements require {allow_write: true}. Input: {sql: str, params?: [any], database?: str, "
    "allow_write?: bool}.",
    category="database",
    input_schema={"sql": {"type": "string", "required": True}, "params": {"type": "array"},
                  "database": {"type": "string"}, "allow_write": {"type": "boolean"}},
)
def sqlite_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "sql")):
        return err(m)
    sql = ti["sql"].strip()
    is_read = sql.lower().lstrip("(").startswith(_READONLY_PREFIXES)
    if not is_read and not ti.get("allow_write"):
        return err("write statement blocked — pass allow_write:true to permit it")
    try:
        conn = _agent_db(ti)
    except SandboxError as e:
        return err(f"sandbox: {e}")
    try:
        cur = conn.execute(sql, ti.get("params") or [])
        if is_read:
            rows = [dict(r) for r in cur.fetchall()]
            return ok(rows=rows, count=len(rows))
        conn.commit()
        return ok(rows_affected=cur.rowcount, lastrowid=cur.lastrowid)
    except Exception as e:  # noqa: BLE001
        return err(f"sqlite_tool: {e}")
    finally:
        conn.close()


# --- 182. sqlite_schema_reader -----------------------------------------------
@tool(
    "sqlite_schema_reader",
    description="List tables and columns of a sandboxed workspace SQLite database. Input: {database?: str}.",
    category="database",
    input_schema={"database": {"type": "string"}},
)
def sqlite_schema_reader(ti: dict, ctx: ToolContext) -> dict:
    try:
        conn = _agent_db(ti)
    except SandboxError as e:
        return err(f"sandbox: {e}")
    try:
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        schema = {}
        for t in tables:
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
            schema[t] = [{"name": c["name"], "type": c["type"], "notnull": bool(c["notnull"]),
                          "pk": bool(c["pk"])} for c in cols]
        return ok(tables=tables, schema=schema)
    except Exception as e:  # noqa: BLE001
        return err(f"sqlite_schema_reader: {e}")
    finally:
        conn.close()


# --- 183. database_backup ----------------------------------------------------
@tool(
    "database_backup",
    description="Back up a sandboxed workspace SQLite database to another workspace file. Input: "
    "{database?: str, out: str}.",
    category="database",
    input_schema={"out": {"type": "string", "required": True}, "database": {"type": "string"}},
)
def database_backup(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "out")):
        return err(m)
    try:
        src = _agent_db(ti)
        dst_path = safe_path(ti["out"])
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst = sqlite3.connect(str(dst_path))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        return ok(out=rel_to_workspace(dst_path), backed_up=True)
    except SandboxError as e:
        return err(f"sandbox: {e}")
    except Exception as e:  # noqa: BLE001
        return err(f"database_backup: {e}")


# --- 184. key_value_store ----------------------------------------------------
@tool(
    "key_value_store",
    description="Persistent namespaced key/value store. Input: {action: get|set|delete|list, key?: str, "
    "value?: any, namespace?: str}.",
    category="database",
    input_schema={"action": {"type": "string", "required": True}, "key": {"type": "string"}, "value": {}},
)
def key_value_store(ti: dict, ctx: ToolContext) -> dict:
    import json

    action = (ti.get("action") or "get").lower()
    ns = ti.get("namespace") or f"agent:{ctx.agent_id or 'default'}"
    with connection() as conn:
        if action == "set":
            if (m := need(ti, "key")):
                return err(m)
            conn.execute(
                """INSERT INTO kv_store (namespace, key, value, expires_at, updated_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (ns, ti["key"], json.dumps(ti.get("value"), default=str), None, _now()),
            )
            return ok(stored=True, key=ti["key"])
        if action == "get":
            if (m := need(ti, "key")):
                return err(m)
            row = conn.execute("SELECT value FROM kv_store WHERE namespace=? AND key=?", (ns, ti["key"])).fetchone()
            return ok(found=row is not None, value=(json.loads(row["value"]) if row else None))
        if action == "delete":
            if (m := need(ti, "key")):
                return err(m)
            cur = conn.execute("DELETE FROM kv_store WHERE namespace=? AND key=?", (ns, ti["key"]))
            return ok(deleted=cur.rowcount > 0)
        if action == "list":
            rows = conn.execute("SELECT key FROM kv_store WHERE namespace=? ORDER BY key", (ns,)).fetchall()
            return ok(keys=[r["key"] for r in rows], count=len(rows))
    return err(f"unknown action: {action}")


# --- 185. local_cache --------------------------------------------------------
@tool(
    "local_cache",
    description="TTL cache backed by the kv store. Input: {action: get|set, key: str, value?: any, "
    "ttl_seconds?: int=300}.",
    category="database",
    input_schema={"action": {"type": "string", "required": True}, "key": {"type": "string", "required": True}},
)
def local_cache(ti: dict, ctx: ToolContext) -> dict:
    import datetime as dt
    import json

    if (m := need(ti, "action", "key")):
        return err(m)
    ns = f"cache:{ctx.agent_id or 'default'}"
    action = ti["action"].lower()
    with connection() as conn:
        if action == "set":
            exp = (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=int(ti.get("ttl_seconds") or 300))).isoformat()
            conn.execute(
                """INSERT INTO kv_store (namespace, key, value, expires_at, updated_at) VALUES (?,?,?,?,?)
                   ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value,
                   expires_at=excluded.expires_at, updated_at=excluded.updated_at""",
                (ns, ti["key"], json.dumps(ti.get("value"), default=str), exp, _now()),
            )
            return ok(cached=True, expires_at=exp)
        if action == "get":
            row = conn.execute("SELECT value, expires_at FROM kv_store WHERE namespace=? AND key=?",
                               (ns, ti["key"])).fetchone()
            if not row:
                return ok(hit=False, value=None)
            if row["expires_at"] and row["expires_at"] <= _now():
                conn.execute("DELETE FROM kv_store WHERE namespace=? AND key=?", (ns, ti["key"]))
                return ok(hit=False, value=None, expired=True)
            return ok(hit=True, value=json.loads(row["value"]))
    return err(f"unknown action: {action}")


# ============================================================================
# General Utilities (10)
# ============================================================================

# --- 230. uuid_generator -----------------------------------------------------
@tool(
    "uuid_generator",
    description="Generate one or more UUID4 strings. Input: {count?: int=1}.",
    category="utility",
    input_schema={"count": {"type": "integer"}},
)
def uuid_generator(ti: dict, ctx: ToolContext) -> dict:
    n = min(int(ti.get("count") or 1), 1000)
    ids = [str(_uuid.uuid4()) for _ in range(n)]
    return ok(uuids=ids, count=n) if n > 1 else ok(uuid=ids[0])


# --- 231. hash_tool ----------------------------------------------------------
@tool(
    "hash_tool",
    description="Hash a string. Input: {text: str, algo?: md5|sha1|sha256|sha512}.",
    category="utility",
    input_schema={"text": {"type": "string", "required": True}, "algo": {"type": "string"}},
)
def hash_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    algo = (ti.get("algo") or "sha256").lower()
    if algo not in {"md5", "sha1", "sha256", "sha512"}:
        return err(f"unsupported algo: {algo}")
    h = hashlib.new(algo)
    h.update(ti["text"].encode("utf-8"))
    return ok(algo=algo, hash=h.hexdigest())


# --- 232. base64_tool --------------------------------------------------------
@tool(
    "base64_tool",
    description="Base64 encode or decode a string. Input: {text: str, mode?: encode|decode}.",
    category="utility",
    input_schema={"text": {"type": "string", "required": True}, "mode": {"type": "string"}},
)
def base64_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    mode = (ti.get("mode") or "encode").lower()
    try:
        if mode == "encode":
            return ok(result=base64.b64encode(ti["text"].encode("utf-8")).decode("ascii"))
        if mode == "decode":
            return ok(result=base64.b64decode(ti["text"]).decode("utf-8", errors="replace"))
        return err(f"unknown mode: {mode}")
    except Exception as e:  # noqa: BLE001
        return err(f"base64_tool: {e}")


# --- 233. encoding_converter -------------------------------------------------
@tool(
    "encoding_converter",
    description="Convert a string's text encoding (e.g. utf-8 <-> latin-1) or to/from hex. Input: "
    "{text: str, to: str (utf-8|latin-1|ascii|hex), from?: str}.",
    category="utility",
    input_schema={"text": {"type": "string", "required": True}, "to": {"type": "string", "required": True}},
)
def encoding_converter(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text", "to")):
        return err(m)
    to = ti["to"].lower()
    try:
        if to == "hex":
            return ok(result=ti["text"].encode("utf-8").hex())
        if (ti.get("from") or "").lower() == "hex":
            return ok(result=bytes.fromhex(ti["text"]).decode(to, errors="replace"))
        return ok(result=ti["text"].encode(ti.get("from") or "utf-8").decode(to, errors="replace"))
    except Exception as e:  # noqa: BLE001
        return err(f"encoding_converter: {e}")


# --- 234. mime_type_lookup ---------------------------------------------------
@tool(
    "mime_type_lookup",
    description="Guess the MIME type for a filename or extension. Input: {filename: str}.",
    category="utility",
    input_schema={"filename": {"type": "string", "required": True}},
)
def mime_type_lookup(ti: dict, ctx: ToolContext) -> dict:
    import mimetypes

    if (m := need(ti, "filename")):
        return err(m)
    mt, enc = mimetypes.guess_type(ti["filename"])
    return ok(mime_type=mt or "application/octet-stream", encoding=enc)


# --- 174. url_parser ---------------------------------------------------------
@tool(
    "url_parser",
    description="Parse a URL into components (scheme, host, path, query params, fragment). Input: {url: str}.",
    category="utility",
    input_schema={"url": {"type": "string", "required": True}},
)
def url_parser(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "url")):
        return err(m)
    p = urlparse(ti["url"])
    return ok(scheme=p.scheme, host=p.hostname, port=p.port, path=p.path,
              query=parse_qs(p.query), fragment=p.fragment)


# --- 171. dns_lookup ---------------------------------------------------------
@tool(
    "dns_lookup",
    description="Resolve a hostname to IP addresses. Input: {host: str}.",
    category="utility",
    input_schema={"host": {"type": "string", "required": True}},
)
def dns_lookup(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "host")):
        return err(m)
    host = ti["host"].replace("https://", "").replace("http://", "").split("/")[0]
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({i[4][0] for i in infos})
        return ok(host=host, addresses=ips, count=len(ips))
    except Exception as e:  # noqa: BLE001
        return err(f"dns_lookup failed: {e}", degraded=True)


# --- 173. ip_address_parser --------------------------------------------------
@tool(
    "ip_address_parser",
    description="Validate and classify an IP address (version, private/global, reverse pointer). "
    "Input: {ip: str}.",
    category="utility",
    input_schema={"ip": {"type": "string", "required": True}},
)
def ip_address_parser(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "ip")):
        return err(m)
    try:
        ip = ipaddress.ip_address(ti["ip"])
        return ok(valid=True, version=ip.version, is_private=ip.is_private,
                  is_global=ip.is_global, reverse_pointer=ip.reverse_pointer)
    except ValueError as e:
        return err(f"invalid ip: {e}", valid=False)


# --- 240. checksum_verifier --------------------------------------------------
@tool(
    "checksum_verifier",
    description="Verify a string/text against an expected checksum. Input: {text: str, expected: str, "
    "algo?: md5|sha1|sha256}.",
    category="utility",
    input_schema={"text": {"type": "string", "required": True}, "expected": {"type": "string", "required": True}},
)
def checksum_verifier(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text", "expected")):
        return err(m)
    algo = (ti.get("algo") or "sha256").lower()
    if algo not in {"md5", "sha1", "sha256"}:
        return err(f"unsupported algo: {algo}")
    h = hashlib.new(algo)
    h.update(ti["text"].encode("utf-8"))
    actual = h.hexdigest()
    return ok(match=actual.lower() == ti["expected"].strip().lower(), actual=actual, algo=algo)


# --- 244. webhook_sender -----------------------------------------------------
@tool(
    "webhook_sender",
    description="POST a JSON payload to a webhook URL. Input: {url: str, payload?: object, headers?: object}.",
    category="utility",
    input_schema={"url": {"type": "string", "required": True}, "payload": {"type": "object"}},
)
async def webhook_sender(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json=ti.get("payload") or {}, headers=ti.get("headers") or {})
        return ok(status_code=r.status_code, ok=r.status_code < 400, response=r.text[:1000])
    except Exception as e:  # noqa: BLE001
        return err(f"webhook_sender failed: {e}", degraded=True)
