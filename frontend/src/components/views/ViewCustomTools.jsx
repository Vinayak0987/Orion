// Tools · Custom Tools (ViewCustomTools.jsx) — mock .ct-card layout wired to the
// real backend: GET /tools?type=custom (list), POST /tools/custom (create),
// DELETE /tools/:name (remove). Create modal registers any HTTP API as a tool.
import { useEffect, useState } from "react";
import { Plus, Search, ChevronDown, Bot, FileText, Loader2, Trash2, Play, Globe, Code2, X } from "lucide-react";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

const BLANK = {
  name: "", display_name: "", description: "", category: "custom",
  endpoint: "", method: "GET", input_schema: "{}", auth_type: "none", auth_value: "",
};

const StatusBadge = ({ enabled }) =>
  enabled ? (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  ) : (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Draft</span>
  );

const Field = ({ label, children }) => (
  <div><label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">{label}</label>{children}</div>
);

export function ViewCustomTools() {
  const toast = useToast();
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState("");
  const [detail, setDetail] = useState(null);       // tool shown in detail modal
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const load = async () => {
    try {
      setTools((await toolApi.list({ type: "custom" })).tools || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    let schema;
    try {
      schema = JSON.parse(form.input_schema || "{}");
    } catch {
      toast.error("Input schema must be valid JSON");
      return;
    }
    setSaving(true);
    try {
      await toolApi.createCustom({
        name: form.name.trim(),
        display_name: form.display_name.trim() || form.name.trim(),
        description: form.description.trim(),
        category: form.category,
        endpoint: form.endpoint.trim(),
        method: form.method,
        input_schema: schema,
        auth_type: form.auth_type === "none" ? null : form.auth_type,
        auth_header: form.auth_type === "bearer" ? "Authorization" : null,
        auth_value: form.auth_type === "bearer" ? form.auth_value : null,
      });
      toast.success(`Custom tool '${form.name}' created`);
      setForm(null);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (name) => {
    setBusy(name);
    try {
      await toolApi.remove(name);
      setTools((t) => t.filter((x) => x.name !== name));
      setDetail((d) => (d && d.name === name ? null : d));
      toast.success(`Deleted '${name}'`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  };

  const openDetail = (t) => { setDetail(t); setTestResult(null); };

  const runTest = async () => {
    if (!detail) return;
    setTesting(true);
    try {
      setTestResult(await toolApi.execute(detail.name, {}));
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTesting(false);
    }
  };

  const filtered = tools.filter((t) => {
    const needle = q.trim().toLowerCase();
    if (!needle) return true;
    return (t.display_name || t.name || "").toLowerCase().includes(needle);
  });

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>Custom Tools</h1>
            <p className="tools-subtitle">Create and manage your own tools.</p>
          </div>
          <button className="tools-primary" onClick={() => setForm({ ...BLANK })}>
            <Plus size={18} strokeWidth={2.6} /> Create Custom Tool
          </button>
        </div>

        {/* Toolbar */}
        <div className="tools-toolbar">
          <div className="tools-search">
            <Search size={18} strokeWidth={2} className="tools-search-icon" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search custom tools..." />
          </div>
        </div>

        {/* Custom tool list */}
        {loading ? (
          <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : filtered.length === 0 ? (
          <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">
            No custom tools yet. Click “Create Custom Tool” to register an HTTP API.
          </div>
        ) : (
          <div className="ct-list">
            {filtered.map((t) => (
              <div key={t.name} className="ct-card card" onClick={() => openDetail(t)} style={{ cursor: "pointer" }}>
                <div className="ct-icon ct-ic-indigo"><Bot size={26} strokeWidth={2} /></div>
                <div className="ct-info">
                  <h3 className="ct-name">{t.display_name || t.name}</h3>
                  <p className="ct-desc">{t.description || t.config?.endpoint}</p>
                  <span className="ct-tag">{(t.config?.method || "GET")} · {t.category}</span>
                </div>
                <div className="ct-status">
                  <StatusBadge enabled={t.enabled} />
                </div>
                <div className="ct-actions" onClick={(e) => e.stopPropagation()}>
                  <button className="ct-del-btn" title="Delete tool" disabled={busy === t.name} onClick={() => remove(t.name)}>
                    {busy === t.name ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={15} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Need ideas callout */}
        <div className="ct-ideas card">
          <div className="ct-ideas-icon"><FileText size={22} strokeWidth={2} /></div>
          <div className="ct-ideas-body">
            <h3>Need ideas?</h3>
            <p>Turn any HTTP API into a tool your agents can call — no code.</p>
          </div>
          <button className="tools-primary ct-ideas-btn" onClick={() => setForm({ ...BLANK })}>
            <Plus size={17} strokeWidth={2} /> Create Custom Tool
          </button>
        </div>
      </section>

      {/* Detail modal */}
      <Modal open={!!detail} onClose={() => setDetail(null)} title={detail?.display_name || detail?.name}
        subtitle={detail?.name} icon={Code2} size="lg"
        footer={
          <>
            <button onClick={() => remove(detail.name)} disabled={busy === detail?.name}
              className="neu-btn-danger inline-flex items-center gap-1.5 h-9 px-4 text-[13px] font-semibold mr-auto">
              <Trash2 size={14} /> Delete
            </button>
            <button onClick={runTest} disabled={testing}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {testing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} Test
            </button>
          </>
        }>
        {detail && (
          <div className="space-y-3">
            <p className="text-[13px] text-[#5b6678]">{detail.description}</p>
            <div className="grid grid-cols-2 gap-2.5">
              <div className="neu-inset rounded-xl px-3 py-2.5">
                <div className="text-[11px] text-[#9aa6b8] mb-0.5">Method</div>
                <div className="text-[13px] font-semibold text-[#334155]">{detail.config?.method || "GET"}</div>
              </div>
              <div className="neu-inset rounded-xl px-3 py-2.5">
                <div className="text-[11px] text-[#9aa6b8] mb-0.5">Status</div>
                <div className="text-[13px] font-semibold text-emerald-600">{detail.enabled ? "Active" : "Disabled"}</div>
              </div>
            </div>
            <div className="neu-inset rounded-xl px-3 py-2.5 flex items-center gap-2">
              <Globe size={14} className="text-[#8792a6]" />
              <code className="text-[12px] text-[#334155] truncate">{detail.config?.endpoint}</code>
            </div>
            {detail.input_schema && Object.keys(detail.input_schema).length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-[#5b6678] mb-1.5">Input Schema</div>
                <pre className="neu-inset rounded-xl p-3 text-[11.5px] font-mono text-[#334155] overflow-auto max-h-40">{JSON.stringify(detail.input_schema, null, 2)}</pre>
              </div>
            )}
            {testResult && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[11px] font-semibold text-[#5b6678]">Test Result</span>
                  <span className={`tools-badge ${testResult.ok ? "green" : "amber"}`}><span className="tools-badge-dot" /> {testResult.ok ? "ok" : "error"} · {testResult.latency_ms}ms</span>
                </div>
                <pre className="neu-inset rounded-xl p-3 text-[11.5px] font-mono text-[#334155] overflow-auto max-h-56">{JSON.stringify(testResult.result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Create modal */}
      <Modal open={!!form} onClose={() => setForm(null)} title="Create Custom Tool" icon={Bot} size="lg"
        footer={
          <>
            <button onClick={() => setForm(null)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
            <button onClick={save} disabled={saving || !form?.name || !form?.endpoint}
              className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
              {saving && <Loader2 size={14} className="animate-spin" />} Save Tool
            </button>
          </>
        }>
        {form && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Name (snake_case)"><input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="inventory_lookup" className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" /></Field>
              <Field label="Display Name"><input value={form.display_name} onChange={(e) => set("display_name", e.target.value)} placeholder="Inventory Lookup" className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" /></Field>
            </div>
            <Field label="Description (the LLM reads this to decide when to call it)">
              <textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={2}
                placeholder="Query the internal inventory system for stock levels by SKU." className="neu-inset w-full px-3 py-2.5 rounded-xl text-[13px] outline-none resize-y" />
            </Field>
            <div className="grid grid-cols-[1fr_120px] gap-3">
              <Field label="Endpoint URL"><input value={form.endpoint} onChange={(e) => set("endpoint", e.target.value)} placeholder="https://api.company.com/inventory" className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" /></Field>
              <Field label="Method">
                <select value={form.method} onChange={(e) => set("method", e.target.value)} className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13px]">
                  {["GET", "POST", "PUT", "DELETE", "PATCH"].map((m) => <option key={m}>{m}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Input Schema (JSON)">
              <textarea value={form.input_schema} onChange={(e) => set("input_schema", e.target.value)} rows={4}
                className="neu-inset w-full px-3 py-2.5 rounded-xl text-[12px] font-mono outline-none resize-y" />
            </Field>
            <div className="grid grid-cols-[160px_1fr] gap-3">
              <Field label="Auth">
                <select value={form.auth_type} onChange={(e) => set("auth_type", e.target.value)} className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13px]">
                  <option value="none">None</option>
                  <option value="bearer">Bearer Token</option>
                </select>
              </Field>
              {form.auth_type === "bearer" && (
                <Field label="Token (stored encrypted)"><input type="password" value={form.auth_value} onChange={(e) => set("auth_value", e.target.value)} className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" /></Field>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
