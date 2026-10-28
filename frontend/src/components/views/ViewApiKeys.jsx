// Tools · API Keys & Credentials (ViewApiKeys.jsx) — mock .tools-panel table
// layout wired to the real backend: GET/PUT /settings/api-keys, DELETE
// /settings/api-keys/:provider. Keys agents use for LLM + tool calls. Stored
// encrypted; only the last-4 is ever returned.
import { useEffect, useState } from "react";
import { Plus, Search, ChevronDown, Lock, Loader2, Check, Trash2 } from "lucide-react";
import { missionApi } from "../../missionApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

const TABS = ["API Keys"];

const PROVIDERS = [
  { id: "groq", name: "Groq", field: "groq_api_key", service: "Groq", domain: "groq.com", use: "LLM calls (llama models)" },
  { id: "gemini", name: "Gemini", field: "gemini_api_key", service: "Google Gemini", icon: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg", use: "LLM fallback (Gemini)" },
  { id: "openai", name: "OpenAI", field: "openai_api_key", service: "OpenAI", domain: "openai.com", use: "LLM calls (GPT-4o)" },
  { id: "serper", name: "Serper", field: "serper_api_key", service: "Serper", domain: "serper.dev", use: "web_search tool" },
  { id: "google_places", name: "Google Places", field: "google_places_api_key", service: "Google Maps", icon: "https://maps.gstatic.com/favicon3.ico", use: "maps_api tool" },
];

// Real provider favicon (direct icon URL if given, else DuckDuckGo by domain),
// with a monogram fallback.
function ProviderLogo({ domain, icon, name, size = 22 }) {
  const [failed, setFailed] = useState(false);
  const src = icon || (domain ? `https://icons.duckduckgo.com/ip3/${domain}.ico` : null);
  if (src && !failed) {
    return (
      <img src={src} alt={name}
        width={size} height={size} style={{ width: size, height: size, objectFit: "contain", borderRadius: 5 }}
        onError={() => setFailed(true)} />
    );
  }
  return (
    <span style={{ width: size, height: size }} className="rounded-md bg-[#e7ebf3] text-[#4f46e5] inline-grid place-items-center text-[11px] font-bold">
      {(name || "?").charAt(0).toUpperCase()}
    </span>
  );
}

const StatusBadge = ({ isSet }) =>
  isSet ? (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  ) : (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Inactive</span>
  );

export function ViewApiKeys() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("API Keys");
  const [masked, setMasked] = useState({});
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  const [modal, setModal] = useState(null); // provider being added/updated (preset)
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState("");
  const [customKeys, setCustomKeys] = useState([]);
  const [customModal, setCustomModal] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customValue, setCustomValue] = useState("");

  const load = async () => {
    try {
      const [m, ck] = await Promise.allSettled([missionApi.apiKeys(), missionApi.customKeys()]);
      if (m.status === "fulfilled") setMasked(m.value);
      if (ck.status === "fulfilled") setCustomKeys(ck.value.keys || []);
    }
    catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const saveCustom = async () => {
    if (!customName.trim() || !customValue.trim()) { toast.error("Name and value are required"); return; }
    setSaving("__custom__");
    try {
      await missionApi.addCustomKey(customName.trim(), customValue.trim());
      toast.success(`Key '${customName.trim()}' added`);
      setCustomModal(false); setCustomName(""); setCustomValue("");
      load();
    } catch (e) { toast.error(e.message); }
    finally { setSaving(""); }
  };

  const removeCustom = async (slug) => {
    try { await missionApi.deleteCustomKey(slug); toast.success("Key removed"); load(); }
    catch (e) { toast.error(e.message); }
  };

  const save = async () => {
    if (!modal) return;
    const val = value.trim();
    if (!val) return;
    setSaving(modal.id);
    try {
      await missionApi.saveApiKeys({ [modal.field]: val });
      toast.success(`${modal.name} key saved`);
      setModal(null);
      setValue("");
      load();
    } catch (e) { toast.error(e.message); }
    finally { setSaving(""); }
  };

  const remove = async (p) => {
    try {
      await missionApi.deleteApiKey(p.id);
      toast.success(`${p.name} key removed`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const rows = PROVIDERS
    .map((p, i) => ({ ...p, n: i + 1, current: masked[p.id], isSet: !!masked[p.id] }))
    .filter((p) => {
      const needle = q.trim().toLowerCase();
      if (!needle) return true;
      return p.name.toLowerCase().includes(needle) || p.service.toLowerCase().includes(needle);
    });

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>API Keys &amp; Credentials</h1>
            <p className="tools-subtitle">Manage API tokens securely.</p>
          </div>
          <button className="tools-primary" onClick={() => { setCustomModal(true); setCustomName(""); setCustomValue(""); }}>
            <Plus size={18} strokeWidth={2.6} /> Add API Key
          </button>
        </div>

        {/* Panel: tabs + toolbar + table */}
        <div className="tools-panel card">
          <div className="tools-tabs">
            {TABS.map((t) => (
              <button key={t} className={`tools-tab ${activeTab === t ? "active" : ""}`} onClick={() => setActiveTab(t)}>
                {t}
              </button>
            ))}
          </div>

          <div className="tools-toolbar">
            <div className="tools-search">
              <Search size={18} strokeWidth={2} className="tools-search-icon" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search API keys..." />
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
                    <th>Name</th>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Key</th>
                    <th className="tcol-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((k) => (
                    <tr key={k.id}>
                      <td className="tcol-num">{k.n}</td>
                      <td><span className="tools-name">{k.name} Key</span></td>
                      <td>
                        <div className="ak-service">
                          <span className="ak-logo"><ProviderLogo domain={k.domain} icon={k.icon} name={k.service} size={22} /></span>
                          <span className="ak-service-name">{k.service}</span>
                        </div>
                      </td>
                      <td><StatusBadge isSet={k.isSet} /></td>
                      <td className="tools-last">{k.isSet ? `••••••${k.current}` : "—"}</td>
                      <td className="tcol-actions">
                        <div className="tools-actions">
                          <button className="tools-open-btn" onClick={() => { setModal(k); setValue(""); }}>
                            {k.isSet ? "Update" : "Add"}
                          </button>
                          {k.isSet && (
                            <button className="tools-more-btn" aria-label="Delete key" title="Delete key" onClick={() => remove(k)}>
                              <Trash2 size={15} strokeWidth={2} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {customKeys.map((c, i) => (
                    <tr key={`custom-${c.id}`}>
                      <td className="tcol-num">{rows.length + i + 1}</td>
                      <td><span className="tools-name">{c.name}</span></td>
                      <td>
                        <div className="ak-service">
                          <span className="ak-logo"><ProviderLogo name={c.name} size={22} /></span>
                          <span className="ak-service-name">Custom</span>
                        </div>
                      </td>
                      <td><StatusBadge isSet={true} /></td>
                      <td className="tools-last">{c.masked ? `••••••${c.masked.replace(/^\.+/, "")}` : "set"}</td>
                      <td className="tcol-actions">
                        <div className="tools-actions">
                          <button className="tools-more-btn" aria-label="Delete key" title="Delete key" onClick={() => removeCustom(c.id)}>
                            <Trash2 size={15} strokeWidth={2} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Keep your keys secure callout */}
        <div className="ak-secure card">
          <div className="ak-secure-icon"><Lock size={24} strokeWidth={2} /></div>
          <div className="ak-secure-body">
            <h3>Keep your keys secure</h3>
            <p>API keys are encrypted at rest — only the last 4 characters are ever shown. Never share your keys in public repositories.</p>
          </div>
        </div>
      </section>

      {/* Add custom key modal (arbitrary name + value, usable by tools) */}
      <Modal open={customModal} onClose={() => setCustomModal(false)} title="Add API Key"
        subtitle="A named credential your custom tools can use" icon={Plus} size="md"
        footer={
          <>
            <button onClick={() => setCustomModal(false)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
            <button onClick={saveCustom} disabled={saving === "__custom__" || !customName.trim() || !customValue.trim()}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {saving === "__custom__" ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Save Key
            </button>
          </>
        }>
        <div className="space-y-2.5">
          <div>
            <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Key Name</label>
            <input autoFocus value={customName} onChange={(e) => setCustomName(e.target.value)}
              placeholder="e.g. WEATHER_API_KEY" className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Key Value</label>
            <input value={customValue} onChange={(e) => setCustomValue(e.target.value)} type="password"
              placeholder="Paste the API key" className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
          </div>
          <p className="text-[11.5px] text-[#9aa6b8]">Stored encrypted. Reference it by name in a Custom Tool's auth, or let agents use it.</p>
        </div>
      </Modal>

      {/* Add / update preset provider key modal */}
      <Modal open={!!modal} onClose={() => setModal(null)} title={modal ? `${modal.isSet ? "Update" : "Add"} ${modal.name} Key` : ""}
        subtitle={modal?.use} icon={Lock} size="md"
        footer={
          <>
            <button onClick={() => setModal(null)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
            <button onClick={save} disabled={saving === modal?.id || !value.trim()}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {saving === modal?.id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Save
            </button>
          </>
        }>
        {modal && (
          <div className="space-y-2.5">
            <p className="text-[12.5px] text-[#8792a6]">Enter the {modal.name} API key. It is validated and stored encrypted.</p>
            <input autoFocus value={value} onChange={(e) => setValue(e.target.value)} type="password"
              placeholder={`Enter ${modal.name} key`} className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
          </div>
        )}
      </Modal>
    </div>
  );
}
