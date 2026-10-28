// Tools · MCP Servers (ViewMcpServers.jsx) — mock .mcp-card layout wired to the
// real backend: GET /tools/mcp (list), POST /tools/mcp (connect & discover),
// DELETE /tools/mcp/:id (disconnect). Connect Server modal collects URL + name.
import { useEffect, useState } from "react";
import { Plus, Search, ChevronDown, ChevronRight, Server, ShieldCheck, Shield, Loader2, Trash2, Wrench, Link2 } from "lucide-react";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

// Favicon from the server's own domain; falls back to the Server icon for local
// servers or when the domain has no favicon. Uses the registrable root domain
// (e.g. mcp.deepwiki.com -> deepwiki.com) which reliably has the brand favicon.
function _rootDomain(host) {
  const parts = (host || "").split(".");
  if (parts.length <= 2) return host;
  // Keep last two labels (handles mcp.fal.ai -> fal.ai, mcp.deepwiki.com -> deepwiki.com).
  return parts.slice(-2).join(".");
}
function ServerIcon({ url, size = 28 }) {
  const isLocal = String(url || "").startsWith("local://") || String(url || "").startsWith("stdio://");
  let host = null;
  if (!isLocal) {
    try { host = _rootDomain(new URL(url).hostname); } catch { host = null; }
  }
  const [failed, setFailed] = useState(false);
  if (host && !failed) {
    return (
      <img src={`https://icons.duckduckgo.com/ip3/${host}.ico`} alt={host}
        width={size} height={size} style={{ width: size, height: size, objectFit: "contain", borderRadius: 6 }}
        onError={() => setFailed(true)} />
    );
  }
  return <Server size={size} strokeWidth={2} color="#2563eb" />;
}

const timeAgo = (iso) => {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hour${h === 1 ? "" : "s"} ago`;
  return `${Math.floor(h / 24)} day${Math.floor(h / 24) === 1 ? "" : "s"} ago`;
};

const StatusBadge = ({ status }) =>
  status === "connected" || status === "active" ? (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  ) : (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Inactive</span>
  );

export function ViewMcpServers() {
  const toast = useToast();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [transport, setTransport] = useState("http"); // http | stdio
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [command, setCommand] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [busy, setBusy] = useState("");
  const [expanded, setExpanded] = useState(null); // server id whose tools are shown

  const load = async () => {
    try {
      setServers((await toolApi.listMcp()).servers || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
    // Read the MCP OAuth callback result (?mcp=oauth&status=connected).
    const p = new URLSearchParams(window.location.search);
    if (p.get("mcp") === "oauth") {
      const st = p.get("status");
      if (st === "connected") toast.success("MCP server connected via OAuth");
      else toast.error("MCP OAuth connection failed");
      window.history.replaceState({}, "", window.location.pathname);
    }
    /* eslint-disable-next-line */
  }, []);

  const connect = async () => {
    const isStdio = transport === "stdio";
    if (isStdio ? !command.trim() : !url.trim()) return;
    setConnecting(true);
    try {
      const body = isStdio
        ? { transport: "stdio", command: command.trim(), name: name.trim() || undefined }
        : { server_url: url.trim(), name: name.trim() || undefined };
      const r = await toolApi.connectMcp(body);
      if (r.needs_oauth && r.authorize_url) {
        toast.info("Redirecting to sign in…");
        window.location.href = r.authorize_url;   // browser OAuth sign-in
        return;
      }
      toast.success(`Connected · discovered ${r.count} tool${r.count === 1 ? "" : "s"}`);
      setOpen(false); setUrl(""); setName(""); setCommand(""); setTransport("http");
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async (id) => {
    setBusy(id);
    try {
      const r = await toolApi.disconnectMcp(id);
      toast.success(`Disconnected · ${r.tools_disabled ?? 0} tools disabled`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  const reconnect = async (id) => {
    setBusy(id);
    try {
      const r = await toolApi.reconnectMcp(id);
      toast.success(`Reconnected · ${r.tools_enabled ?? 0} tools enabled`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  const remove = async (id) => {
    setBusy(id);
    try {
      const r = await toolApi.removeMcp(id);
      toast.success(`Removed · ${r.tools_removed ?? 0} tools deleted`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  const filtered = servers.filter((s) => {
    const needle = q.trim().toLowerCase();
    if (needle && !(s.name || "").toLowerCase().includes(needle)) return false;
    const active = s.status === "connected" || s.status === "active";
    if (statusFilter === "active" && !active) return false;
    if (statusFilter === "inactive" && active) return false;
    return true;
  });

  const activeCount = servers.filter((s) => s.status === "connected" || s.status === "active").length;
  const inactiveCount = servers.length - activeCount;
  const successRate = servers.length ? Math.round((activeCount / servers.length) * 100) : 0;

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>MCP Servers</h1>
            <p className="tools-subtitle">Manage MCP connections to extend Orion's capabilities.</p>
          </div>
          <button className="tools-primary" onClick={() => setOpen(true)}>
            <Plus size={18} strokeWidth={2.6} /> Add MCP Server
          </button>
        </div>

        {/* Stat cards (real counts) */}
        <div className="tools-stats">
          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Server size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Total Servers</div>
              <div className="tools-stat-value">{servers.length}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic green"><span className="tools-stat-dot green" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Active</div>
              <div className="tools-stat-value">{activeCount}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic red"><span className="tools-stat-dot red" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Inactive</div>
              <div className="tools-stat-value">{inactiveCount}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic green"><ShieldCheck size={20} strokeWidth={2} color="#16a34a" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Success Rate</div>
              <div className="tools-stat-value">{successRate}%</div>
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="tools-toolbar mcp-toolbar">
          <div className="tools-search">
            <Search size={18} strokeWidth={2} className="tools-search-icon" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search Servers..." />
          </div>
          <div className="tools-select-wrap">
            <select className="tools-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <ChevronDown size={18} strokeWidth={2} className="tools-select-chev" />
          </div>
        </div>

        {/* Server list */}
        {loading ? (
          <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : filtered.length === 0 ? (
          <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">
            No MCP servers connected. Click “Add MCP Server” to connect one.
          </div>
        ) : (
          <div className="mcp-list">
            {filtered.map((s) => {
              const isOpen = expanded === s.id;
              const tools = s.tools || [];
              return (
                <div key={s.id} className={`mcp-card card ${isOpen ? "is-open" : ""}`}>
                  <div className="mcp-card-row" onClick={() => setExpanded(isOpen ? null : s.id)} style={{ cursor: "pointer" }}>
                    <div className="mcp-icon mcp-ic-blue">
                      <ServerIcon url={s.server_url} size={28} />
                    </div>
                    <div className="mcp-info">
                      <h3 className="mcp-name">{s.name} {s.is_local && <span className="mcp-local-tag">local</span>}</h3>
                      <p className="mcp-desc">{s.description || s.server_url}</p>
                      <div className="mcp-versions">
                        <span className="mcp-version">{s.tool_count ?? tools.length} tools</span>
                        <span className="mcp-version">{isOpen ? "hide tools" : "view tools"}</span>
                      </div>
                    </div>
                    <div className="mcp-status">
                      <StatusBadge status={s.status} />
                      <span className="mcp-last">{timeAgo(s.updated_at || s.created_at)}</span>
                    </div>
                    <div className="mcp-actions" onClick={(e) => e.stopPropagation()}>
                      {!s.is_local && (
                        <>
                          {(s.status === "connected" || s.status === "active") ? (
                            <button className="mcp-test-btn" disabled={busy === s.id} onClick={() => disconnect(s.id)}>
                              {busy === s.id ? <Loader2 size={13} className="animate-spin" /> : "Disconnect"}
                            </button>
                          ) : (
                            <button className="mcp-test-btn is-connect" disabled={busy === s.id} onClick={() => reconnect(s.id)}>
                              {busy === s.id ? <Loader2 size={13} className="animate-spin" /> : <><Link2 size={13} strokeWidth={2.2} /> Connect</>}
                            </button>
                          )}
                          <button className="mcp-remove-btn" title="Remove server" disabled={busy === s.id} onClick={() => remove(s.id)}>
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                      <span className="mcp-chev">{isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}</span>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="mcp-tools-panel">
                      {tools.length === 0 ? (
                        <p className="text-[12.5px] text-[#9aa6b8] px-1 py-2">No tools registered for this server.</p>
                      ) : (
                        <div className="mcp-tools-grid">
                          {tools.map((t) => (
                            <div key={t.name} className="mcp-tool-item">
                              <span className="mcp-tool-ic"><Wrench size={14} /></span>
                              <div className="min-w-0">
                                <div className="mcp-tool-name">{t.display_name || t.name}</div>
                                <div className="mcp-tool-desc">{t.description}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Configuration Help */}
        <h2 className="mcp-help-title">Configuration Help</h2>
        <div className="mcp-help card">
          <div className="mcp-help-icon"><Shield size={22} strokeWidth={2} fill="#bfdbfe" /></div>
          <div className="mcp-help-body">
            <h3>Need help setting up MCP servers?</h3>
            <p>Orion sends a <code>tools/list</code> discovery request and registers each tool it finds.</p>
          </div>
          <button className="tools-primary mcp-help-btn" onClick={() => setOpen(true)}>Add MCP Server</button>
        </div>
      </section>

      {/* Connect Server modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="Connect MCP Server" icon={Server} size="md"
        footer={
          <>
            <button onClick={() => setOpen(false)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
            <button onClick={connect} disabled={connecting || (transport === "stdio" ? !command.trim() : !url.trim())}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {connecting && <Loader2 size={14} className="animate-spin" />} Connect &amp; Discover
            </button>
          </>
        }>
        <div className="space-y-3">
          <div>
            <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Transport</label>
            <div className="neu-inset inline-flex items-center p-1 rounded-xl">
              {[{ v: "http", label: "Remote URL" }, { v: "stdio", label: "Local command" }].map((o) => (
                <button key={o.v} type="button" onClick={() => setTransport(o.v)}
                  className={`h-8 px-3.5 rounded-lg text-[12.5px] font-semibold transition ${transport === o.v ? "neu-raised text-[#4f46e5]" : "text-[#8792a6]"}`}>
                  {o.label}
                </button>
              ))}
            </div>
          </div>
          {transport === "http" ? (
            <div>
              <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Server URL</label>
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://mcp.deepwiki.com/mcp"
                className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
            </div>
          ) : (
            <div>
              <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Command</label>
              <input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="npx -y @modelcontextprotocol/server-filesystem /data"
                className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] font-mono outline-none" />
              <p className="text-[11px] text-amber-600 mt-1.5">⚠ Runs a local command on the server. Must be enabled in backend (MCP_STDIO_ENABLED). Only use trusted commands.</p>
            </div>
          )}
          <div>
            <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Name (optional)</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder={transport === "stdio" ? "Filesystem MCP" : "DeepWiki"}
              className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
          </div>
          <p className="text-[12px] text-[#9aa6b8]">Orion sends a <code>tools/list</code> discovery request and registers each tool it finds.</p>
        </div>
      </Modal>
    </div>
  );
}
