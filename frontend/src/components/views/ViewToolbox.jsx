// Tools · Toolbox Overview — mock layout (.tools-page) wired to the real backend.
//
// Rows merge TWO real sources into the single mock table:
//   1. /tools              → 111 built-in / custom / mcp tools (enable·disable·Test)
//   2. /tools/integrations + /oauth/providers → connectors (Connect / Connected)
//
// Stat cards show real counts. Search + category + status filters all work.
import { useEffect, useMemo, useState } from "react";
import {
  Plus, Search, ChevronDown, Settings, Wrench, Loader2, Play, Globe, FileText,
  Database, Calculator, Brain, Boxes, BookOpen, Code2,
} from "lucide-react";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";
import { BrandLogo } from "./brandLogos.jsx";

const PAGE_SIZE = 10;

// Category → icon for built-in tools (connectors use their real brand logo).
const CAT_ICON = {
  web: Globe, text: FileText, data: Database, files: FileText, math: Calculator,
  knowledge: BookOpen, database: Database, utility: Boxes, ml: Brain, code: Code2,
  custom: Settings, mcp: Boxes,
};

// Human "x min/hours/days ago" from an ISO timestamp.
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
  const d = Math.floor(h / 24);
  return `${d} day${d === 1 ? "" : "s"} ago`;
};

const StatusBadge = ({ status }) => {
  const map = {
    active: ["green", "Active"],
    enabled: ["green", "Active"],
    connected: ["green", "Connected"],
    "not-configured": ["amber", "Not Configured"],
    disabled: ["amber", "Disabled"],
    available: ["amber", "Not Configured"],
  };
  const [tone, label] = map[status] || ["amber", "Not Configured"];
  return (
    <span className={`tools-badge ${tone}`}>
      <span className="tools-badge-dot" /> {label}
    </span>
  );
};

export function ViewToolbox({ onNavigate }) {
  const toast = useToast();
  const [tools, setTools] = useState([]);
  const [facets, setFacets] = useState({ category: {}, type: {}, total: 0 });
  const [integrations, setIntegrations] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  // Token-connector connect modal.
  const [tokenModal, setTokenModal] = useState(null);
  const [cred, setCred] = useState("");

  // Built-in tool test modal.
  const [testing, setTesting] = useState(null);
  const [testInput, setTestInput] = useState("{}");
  const [testResult, setTestResult] = useState(null);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const [tRes, iRes, pRes] = await Promise.allSettled([
        toolApi.list(),
        toolApi.listIntegrations(),
        toolApi.oauthProviders(),
      ]);
      if (tRes.status === "fulfilled") {
        setTools(tRes.value.tools || []);
        setFacets(tRes.value.facets || { category: {}, type: {}, total: 0 });
      }
      if (iRes.status === "fulfilled") setIntegrations(iRes.value.integrations || []);
      if (pRes.status === "fulfilled") setProviders(pRes.value.providers || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // Toast OAuth callback results (?oauth=slack&status=connected).
    const p = new URLSearchParams(window.location.search);
    const prov = p.get("oauth");
    const st = p.get("status");
    if (prov && st) {
      if (st === "connected") toast.success(`${prov} connected`);
      else toast.error(`${prov} connection failed`);
      window.history.replaceState({}, "", window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- actions -------------------------------------------------------------
  const toggleTool = async (t) => {
    try {
      await toolApi.setEnabled(t.name, !t.enabled);
      setTools((prev) => prev.map((x) => (x.name === t.name ? { ...x, enabled: !x.enabled } : x)));
      toast.success(`${t.display_name} ${t.enabled ? "disabled" : "enabled"}`);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const startOAuth = async (providerId) => {
    setBusy(providerId);
    try {
      const { authorize_url } = await toolApi.oauthAuthorize(providerId);
      window.location.href = authorize_url;
    } catch (e) {
      toast.error(e.message);
      setBusy("");
    }
  };

  const connectToken = async () => {
    if (!tokenModal) return;
    setBusy(tokenModal.id);
    try {
      await toolApi.connectIntegration(tokenModal.id, cred.trim());
      toast.success(`${tokenModal.name} connected`);
      setTokenModal(null);
      setCred("");
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  const openTest = (t) => {
    setTesting(t);
    setTestResult(null);
    const schema = t.input_schema || {};
    const skeleton = {};
    Object.entries(schema).forEach(([k, v]) => {
      if (v?.required) skeleton[k] = "";
    });
    setTestInput(JSON.stringify(skeleton, null, 2));
  };

  const runTest = async () => {
    let input;
    try {
      input = JSON.parse(testInput || "{}");
    } catch {
      toast.error("Input must be valid JSON");
      return;
    }
    setRunning(true);
    try {
      setTestResult(await toolApi.execute(testing.name, input));
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRunning(false);
    }
  };

  // --- build the unified row list -----------------------------------------
  // Each row: {key, kind:'tool'|'oauth'|'token', name, category, status, last, raw}
  const allRows = useMemo(() => {
    const toolRows = tools.map((t) => ({
      key: `tool:${t.name}`,
      kind: "tool",
      name: t.display_name || t.name,
      category: t.category,
      logoKey: null,
      status: t.enabled ? "active" : "disabled",
      last: timeAgo(t.last_used),
      raw: t,
    }));
    const oauthRows = providers.map((p) => ({
      key: `oauth:${p.id}`,
      kind: "oauth",
      name: p.name,
      category: p.category || "Integration",
      logoKey: p.connection?.logo_key || p.id,
      status: p.connection?.connected ? "connected" : "not-configured",
      last: timeAgo(p.connection?.connected_at),
      raw: p,
    }));
    const tokenRows = integrations.map((i) => ({
      key: `token:${i.id}`,
      kind: "token",
      name: i.name,
      category: i.category || "Integration",
      logoKey: i.logo_key || i.id,
      status: i.status === "connected" ? "connected" : "not-configured",
      last: timeAgo(i.connected_at),
      raw: i,
    }));
    return [...toolRows, ...oauthRows, ...tokenRows];
  }, [tools, providers, integrations]);

  const categories = useMemo(() => {
    const set = new Set();
    allRows.forEach((r) => r.category && set.add(r.category));
    return [...set].sort();
  }, [allRows]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return allRows.filter((r) => {
      if (needle && !r.name.toLowerCase().includes(needle)) return false;
      if (cat && r.category !== cat) return false;
      if (status === "active" && !(r.status === "active" || r.status === "connected")) return false;
      if (status === "not-configured" && !(r.status === "not-configured" || r.status === "disabled")) return false;
      return true;
    });
  }, [allRows, q, cat, status]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  // Reset to page 1 whenever filters change.
  useEffect(() => setPage(1), [q, cat, status]);

  // --- real stat counts ----------------------------------------------------
  const totalTools = facets.total || tools.length;
  const connectorsConnected =
    providers.filter((p) => p.connection?.connected).length +
    integrations.filter((i) => i.status === "connected").length;
  const activeCount = tools.filter((t) => t.enabled).length + connectorsConnected;
  const notConfigured =
    tools.filter((t) => t.degraded && !t.enabled).length +
    providers.filter((p) => !p.connection?.connected).length +
    integrations.filter((i) => i.status !== "connected").length;
  const customCount = (facets.type?.custom || 0) + (facets.type?.mcp || 0);

  const windowStart = filtered.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const windowEnd = Math.min(safePage * PAGE_SIZE, filtered.length);

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>Toolbox Overview</h1>
            <p className="tools-subtitle">All available tools (search, maps, APIs, etc.)</p>
          </div>
          <button className="tools-primary" onClick={() => onNavigate?.("custom")} title="Create a custom tool">
            <Plus size={18} strokeWidth={2.6} /> Add Tool
          </button>
        </div>

        {/* Stat cards (real counts) */}
        <div className="tools-stats">
          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Settings size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Total Tools</div>
              <div className="tools-stat-value">{totalTools + providers.length + integrations.length}</div>
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
            <div className="tools-stat-ic amber"><span className="tools-stat-dot amber" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Not Configured</div>
              <div className="tools-stat-value">{notConfigured}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Wrench size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Custom Tools</div>
              <div className="tools-stat-value">{customCount}</div>
            </div>
          </div>
        </div>

        {/* Toolbar + table panel */}
        <div className="tools-panel card">
          <div className="tools-toolbar">
            <div className="tools-search">
              <Search size={18} strokeWidth={2} className="tools-search-icon" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tools..." />
            </div>
            <div className="tools-select-wrap">
              <select className="tools-select" value={cat} onChange={(e) => setCat(e.target.value)}>
                <option value="">All Categories</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <ChevronDown size={18} strokeWidth={2} className="tools-select-chev" />
            </div>
            <div className="tools-select-wrap">
              <select className="tools-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">All Status</option>
                <option value="active">Active / Connected</option>
                <option value="not-configured">Not Configured</option>
              </select>
              <ChevronDown size={18} strokeWidth={2} className="tools-select-chev" />
            </div>
          </div>

          <div className="tools-table-wrap">
            {loading ? (
              <div className="grid place-items-center py-16 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
            ) : (
              <table className="tools-table">
                <thead>
                  <tr>
                    <th className="tcol-num">#</th>
                    <th>Tool / Integration</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Last Used</th>
                    <th className="tcol-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", padding: "32px", color: "#8792a6" }}>No tools match your filters.</td></tr>
                  ) : pageRows.map((row, idx) => (
                    <tr key={row.key}>
                      <td className="tcol-num">{windowStart + idx}</td>
                      <td>
                        <div className="tools-name-cell">
                          <span className="tools-logo">
                            {row.kind === "tool"
                              ? (() => { const Ic = CAT_ICON[row.category] || Wrench; return <Ic size={18} className="text-[#4f46e5]" />; })()
                              : <BrandLogo logoKey={row.logoKey} name={row.name} size={22} />}
                          </span>
                          <span className="tools-name">{row.name}</span>
                        </div>
                      </td>
                      <td className="tools-category">{row.category}</td>
                      <td><StatusBadge status={row.status} /></td>
                      <td className="tools-last">{row.last}</td>
                      <td className="tcol-actions">
                        <div className="tools-actions">
                          {row.kind === "tool" ? (
                            <>
                              <button className="tools-open-btn" onClick={() => openTest(row.raw)}>
                                <Play size={13} strokeWidth={2.4} style={{ marginRight: 4 }} /> Test
                              </button>
                              <button
                                type="button"
                                role="switch"
                                aria-checked={row.raw.enabled}
                                onClick={() => toggleTool(row.raw)}
                                title={row.raw.enabled ? "Enabled — click to disable" : "Disabled — click to enable"}
                                className={`neu-toggle ${row.raw.enabled ? "neu-toggle-on" : ""} w-[42px] h-[24px] relative shrink-0`}
                              >
                                <span className={`neu-toggle-knob absolute top-[3px] w-[18px] h-[18px] rounded-full ${row.raw.enabled ? "left-[21px]" : "left-[3px]"}`} />
                              </button>
                            </>
                          ) : row.kind === "oauth" ? (
                            row.raw.connection?.connected ? (
                              <button className="tools-open-btn" disabled>Connected</button>
                            ) : (
                              <button className="tools-open-btn" disabled={busy === row.raw.id} onClick={() => startOAuth(row.raw.id)}>
                                {busy === row.raw.id ? <Loader2 size={13} className="animate-spin" /> : "Connect"}
                              </button>
                            )
                          ) : (
                            row.raw.status === "connected" ? (
                              <button className="tools-open-btn" disabled>Connected</button>
                            ) : (
                              <button className="tools-open-btn" onClick={() => { setTokenModal(row.raw); setCred(""); }}>
                                Connect
                              </button>
                            )
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Footer: count + pagination */}
        <div className="tools-footer">
          <div className="tools-count">
            {filtered.length === 0 ? "No tools" : `Showing ${windowStart}–${windowEnd} of ${filtered.length} tools`}
          </div>
          <div className="tools-pager">
            <button className="tools-page-btn" aria-label="Previous" onClick={() => setPage((p) => Math.max(1, p - 1))}>
              <ChevronDown size={16} strokeWidth={2.4} style={{ transform: "rotate(90deg)" }} />
            </button>
            {Array.from({ length: pageCount }, (_, i) => i + 1).slice(0, 7).map((p) => (
              <button key={p} className={`tools-page-btn ${safePage === p ? "active" : ""}`} onClick={() => setPage(p)}>{p}</button>
            ))}
            <button className="tools-page-btn" aria-label="Next" onClick={() => setPage((p) => Math.min(pageCount, p + 1))}>
              <ChevronDown size={16} strokeWidth={2.4} style={{ transform: "rotate(-90deg)" }} />
            </button>
          </div>
        </div>
      </section>

      {/* Token connector connect modal */}
      <Modal open={!!tokenModal} onClose={() => setTokenModal(null)} title={tokenModal ? `Connect ${tokenModal.name}` : ""}
        subtitle={tokenModal?.token_label} icon={Plus} size="md"
        footer={
          <>
            <button onClick={() => setTokenModal(null)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
            <button onClick={connectToken} disabled={busy === tokenModal?.id || !cred.trim()}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {busy === tokenModal?.id && <Loader2 size={14} className="animate-spin" />} Connect
            </button>
          </>
        }>
        {tokenModal && (
          <div className="space-y-2.5">
            <p className="text-[12.5px] text-[#8792a6]">{tokenModal.token_hint}</p>
            <input value={cred} onChange={(e) => setCred(e.target.value)} type="password"
              placeholder={tokenModal.token_label} className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
            <p className="text-[11.5px] text-[#9aa6b8]">Validated live against {tokenModal.name}, then stored encrypted.</p>
          </div>
        )}
      </Modal>

      {/* Built-in tool test modal */}
      <Modal open={!!testing} onClose={() => setTesting(null)} title={testing ? `Test · ${testing.display_name}` : ""}
        subtitle={testing?.name} icon={Play} size="lg">
        {testing && (
          <div className="space-y-3">
            <p className="text-[12.5px] text-[#8792a6]">{testing.description}</p>
            <div>
              <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Input (JSON)</label>
              <textarea value={testInput} onChange={(e) => setTestInput(e.target.value)} rows={5}
                className="neu-inset w-full rounded-xl px-3.5 py-3 text-[13px] font-mono text-[#334155] outline-none resize-y" />
            </div>
            <button onClick={runTest} disabled={running}
              className="neu-btn-primary inline-flex items-center gap-2 h-10 px-5 text-[14px] font-semibold">
              {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} Run
            </button>
            {testResult && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[12px] font-semibold text-[#5b6678]">Result</span>
                  <span className={`tools-badge ${testResult.ok ? "green" : "amber"}`}>
                    <span className="tools-badge-dot" /> {testResult.ok ? "ok" : "error"} · {testResult.latency_ms}ms
                  </span>
                </div>
                <pre className="neu-inset rounded-xl p-3.5 text-[12px] font-mono text-[#334155] overflow-auto max-h-72">
                  {JSON.stringify(testResult.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
