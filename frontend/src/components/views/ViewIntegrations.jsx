// Tools · Integrations (ViewIntegrations.jsx) — mock .intg-grid layout wired to
// BOTH /oauth/providers (OAuth connectors) and /tools/integrations (token/keyless).
//
// Connect/Connected/Disconnect all call the real backend:
//   • OAuth    → oauthAuthorize (redirect to authorize_url) / oauthDisconnect
//   • Token    → connectIntegration(id, credential) / disconnectIntegration(id)
// On return the callback redirects to ?oauth=&status= which we read to toast.
import { useEffect, useState, useCallback } from "react";
import { Plus, Search, ChevronDown, Boxes, ShieldCheck, Loader2 } from "lucide-react";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

// Fallback letter badge when a connector has no brand logo.
// Real brand logo for each connector (falls back to a monogram tile, not a bare letter).
import { BrandLogo } from "./brandLogos.jsx";

const StatusBadge = ({ connected }) =>
  connected ? (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Connected</span>
  ) : (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Disconnected</span>
  );

export function ViewIntegrations() {
  const toast = useToast();
  const [oauth, setOauth] = useState([]);         // /oauth/providers
  const [tokenInt, setTokenInt] = useState([]);   // /tools/integrations
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [tokenModal, setTokenModal] = useState(null);
  const [cred, setCred] = useState("");

  const load = useCallback(async () => {
    try {
      const [op, ti] = await Promise.allSettled([toolApi.oauthProviders(), toolApi.listIntegrations()]);
      if (op.status === "fulfilled") setOauth(op.value.providers || []);
      if (ti.status === "fulfilled") setTokenInt(ti.value.integrations || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  // Read the OAuth callback result on return (?oauth=slack&status=connected).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const prov = p.get("oauth");
    const status = p.get("status");
    if (prov && status) {
      if (status === "connected") toast.success(`${prov} connected`);
      else toast.error(`${prov} connection failed`);
      window.history.replaceState({}, "", window.location.pathname);
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- actions -------------------------------------------------------------
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

  const oauthDisconnect = async (providerId) => {
    setBusy(providerId);
    try {
      await toolApi.oauthDisconnect(providerId);
      toast.success(`${providerId} disconnected`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
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

  const tokenDisconnect = async (id) => {
    setBusy(id);
    try {
      await toolApi.disconnectIntegration(id);
      toast.success("Disconnected");
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  // --- unified cards (catalog is the single source; connect_method drives UI) ---
  // OAuth connection status is merged in from /oauth/providers by provider id.
  const oauthByProvider = Object.fromEntries(oauth.map((p) => [p.id, p]));
  const cards = tokenInt.map((i) => {
    const method = i.connect_method || "api_key";
    if (method === "oauth") {
      const prov = i.oauth_provider;
      const op = oauthByProvider[prov];
      const connected = !!op?.connection?.connected;
      const configured = op ? op.configured !== false : false;
      return {
        key: i.id, kind: "oauth", id: i.id, provider: prov, name: i.name,
        desc: connected ? `Connected as ${op.connection.account_label || "your account"}` : i.description,
        connected, configured, logo_key: i.logo_key || i.id, raw: i,
      };
    }
    // api_key / mcp → token-style connect
    return {
      key: i.id, kind: "token", id: i.id, name: i.name, method,
      desc: i.status === "connected" ? `Connected · ${i.account_label || ""}` : i.description,
      connected: i.status === "connected", configured: true, logo_key: i.logo_key || i.id, raw: i,
    };
  });

  const filtered = cards.filter((c) => {
    const needle = q.trim().toLowerCase();
    if (needle && !c.name.toLowerCase().includes(needle)) return false;
    if (statusFilter === "connected" && !c.connected) return false;
    if (statusFilter === "disconnected" && c.connected) return false;
    return true;
  });

  const total = cards.length;
  const connectedCount = cards.filter((c) => c.connected).length;
  const disconnectedCount = total - connectedCount;
  const successRate = total ? Math.round((connectedCount / total) * 100) : 0;

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>Integrations</h1>
            <p className="tools-subtitle">Connect external systems (Google, Shopify, etc.)</p>
          </div>
        </div>

        {/* Stat cards (real counts) */}
        <div className="tools-stats">
          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Boxes size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Total Integrations</div>
              <div className="tools-stat-value">{total}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic green"><span className="tools-stat-dot green" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Connected</div>
              <div className="tools-stat-value">{connectedCount}</div>
            </div>
          </div>
          <div className="tools-stat card">
            <div className="tools-stat-ic red"><span className="tools-stat-dot red" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Disconnected</div>
              <div className="tools-stat-value">{disconnectedCount}</div>
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
        <div className="tools-toolbar">
          <div className="tools-search">
            <Search size={18} strokeWidth={2} className="tools-search-icon" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search integrations..." />
          </div>
          <div className="tools-select-wrap">
            <select className="tools-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="connected">Connected</option>
              <option value="disconnected">Disconnected</option>
            </select>
            <ChevronDown size={18} strokeWidth={2} className="tools-select-chev" />
          </div>
        </div>

        {/* Integration grid */}
        {loading ? (
          <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="intg-grid">
            {filtered.map((it) => {
              const working = busy === it.id || busy === it.provider;
              return (
                <div key={it.key} className="intg-card card">
                  <div className="intg-logo"><BrandLogo logoKey={it.logo_key} name={it.name} size={30} /></div>
                  <h3 className="intg-name">{it.name}</h3>
                  <p className="intg-desc">{it.desc}</p>
                  <StatusBadge connected={it.connected} />
                  <div className="intg-actions">
                    {it.kind === "oauth" ? (
                      it.connected ? (
                        <button className="intg-btn" disabled={working} onClick={() => oauthDisconnect(it.provider)}>
                          {working ? <Loader2 size={13} className="animate-spin" /> : "Disconnect"}
                        </button>
                      ) : (
                        <button className="intg-btn" disabled={working || !it.configured} onClick={() => startOAuth(it.provider)}>
                          {working ? <Loader2 size={13} className="animate-spin" /> : (it.configured ? "Connect" : "Needs setup")}
                        </button>
                      )
                    ) : it.connected ? (
                      <button className="intg-btn" disabled={working} onClick={() => tokenDisconnect(it.id)}>
                        {working ? <Loader2 size={13} className="animate-spin" /> : "Disconnect"}
                      </button>
                    ) : (
                      <button className="intg-btn" onClick={() => { setTokenModal(it.raw); setCred(""); }}>Connect</button>
                    )}
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px", color: "#8792a6" }}>
                No integrations match your filters.
              </div>
            )}
          </div>
        )}
      </section>

      {/* Token connect modal */}
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
            <p className="text-[11.5px] text-[#9aa6b8]">Validated live against {tokenModal.name}, then stored encrypted. It's never shown again.</p>
          </div>
        )}
      </Modal>
    </div>
  );
}
