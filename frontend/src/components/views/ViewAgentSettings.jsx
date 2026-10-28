// Agent Settings — mock layout (agent-settings) wired to the real backend.
// Loads the preset agent (agentApi.get), edits Basic Information
// (agentApi.update), shows real Version History (agentApi.versions), and offers
// Quick Actions (clone/export) + Danger Zone (disable / delete via remove()).
import { useEffect, useState } from "react";
import {
  Bot,
  ChevronDown,
  Play,
  MoreVertical,
  Lock,
  ArrowRight,
  Copy,
  Upload,
  RotateCcw,
  FileText,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Plus,
  Loader2,
  Save,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

const TABS = ["General", "Access & Permissions", "Runtime", "Notifications", "Versions", "Danger Zone"];
const TYPES = ["research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general"];

const Field = ({ label, children }) => (
  <div className="set-field">
    <label className="set-label">{label}</label>
    {children}
  </div>
);

const Select = ({ value, options, onChange }) => (
  <div className="set-select" style={{ position: "relative" }}>
    <select
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      style={{ appearance: "none", border: "none", background: "transparent", font: "inherit", color: "inherit", width: "100%", outline: "none", cursor: "pointer" }}
    >
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
    <ChevronDown size={18} strokeWidth={2} className="set-select-caret" />
  </div>
);

export const ViewAgentSettings = ({ presetAgentId, onDeleted, onEditBuilder }) => {
  const toast = useToast();
  const [agent, setAgent] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("General");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [cloneName, setCloneName] = useState("");

  const [form, setForm] = useState({
    name: "", purpose: "", agent_type: "general", temperature: 0.7, model: "",
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const load = () => {
    if (!presetAgentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([agentApi.get(presetAgentId), agentApi.versions(presetAgentId)])
      .then(([a, v]) => {
        setAgent(a);
        setForm({
          name: a.name || "",
          purpose: a.purpose || "",
          agent_type: a.agent_type || "general",
          temperature: a.temperature ?? 0.7,
          model: a.model || "",
        });
        setVersions(v.versions || []);
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [presetAgentId]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!agent) return;
    setSaving(true);
    try {
      const r = await agentApi.update(agent.id, {
        name: form.name,
        purpose: form.purpose,
        agent_type: form.agent_type,
        temperature: Number(form.temperature),
        model: form.model || null,
      });
      setAgent(r.agent);
      const v = await agentApi.versions(agent.id);
      setVersions(v.versions || []);
      toast.success("Settings saved");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const doClone = async () => {
    try {
      const r = await agentApi.clone(agent.id, cloneName || undefined);
      toast.success(`Cloned as '${r.agent?.name}'`);
      setCloneOpen(false);
      setCloneName("");
    } catch (e) {
      toast.error(e.message);
    }
  };

  const exportConfig = () => {
    const blob = new Blob([JSON.stringify(agent, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${agent.name.replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.info("Configuration exported");
  };

  const doDelete = async () => {
    try {
      await agentApi.remove(agent.id);
      toast.success(`Agent '${agent.name}' deleted`);
      setConfirmDelete(false);
      onDeleted?.();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading) {
    return (
      <div className="agent-settings">
        <div style={{ display: "grid", placeItems: "center", padding: "80px 0", color: "#a1a9b5" }}>
          <Loader2 className="animate-spin" />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="agent-settings">
        <div className="set-panel card" style={{ textAlign: "center", padding: 40, color: "#a1a9b5" }}>
          No agent selected. Open an agent from the Overview to edit its settings.
        </div>
      </div>
    );
  }

  const status = agent.status || "active";
  const QUICK_ACTIONS = [
    { label: "Clone Agent", icon: <Copy size={19} strokeWidth={2} />, onClick: () => { setCloneName(`${agent.name} (copy)`); setCloneOpen(true); } },
    { label: "Export Configuration", icon: <Upload size={19} strokeWidth={2} />, onClick: exportConfig },
    { label: "Reload", icon: <RotateCcw size={19} strokeWidth={2} />, onClick: load },
    { label: "View Versions", icon: <FileText size={19} strokeWidth={2} />, onClick: () => setTab("Versions") },
  ];

  return (
    <div className="agent-settings">
      {/* Header */}
      <div className="set-header">
        <div className="set-header-left">
          <div className="set-header-icon"><Bot size={26} strokeWidth={2} /></div>
          <h1>{agent.name}</h1>
          <span className="set-status"><span className="set-status-dot" /> {status[0].toUpperCase() + status.slice(1)}</span>
          <button className="set-version">{agent.version || "v1.0.0"} <ChevronDown size={15} strokeWidth={2} /></button>
        </div>
        <div className="set-header-actions">
          <button className="set-test-btn" onClick={save} disabled={saving}>
            {saving ? <Loader2 size={16} strokeWidth={2} className="animate-spin" /> : <Save size={16} strokeWidth={2} />} Save
          </button>
          <button className="set-more" aria-label="More"><MoreVertical size={20} strokeWidth={2} /></button>
        </div>
      </div>

      {/* Tabs */}
      <div className="set-tabs">
        {TABS.map((t) => (
          <button key={t} className={`set-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Body */}
      <div className="set-body">
        {/* Left: Basic Information */}
        <div className="set-main card">
          <h2 className="set-section-title">Basic Information</h2>

          <Field label="Agent Name">
            <input className="set-input" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </Field>

          <Field label="Purpose / Description">
            <textarea className="set-textarea" rows={2} value={form.purpose} onChange={(e) => set("purpose", e.target.value)} />
          </Field>

          <div className="set-row">
            <Field label="Agent Type"><Select value={form.agent_type} options={TYPES} onChange={(v) => set("agent_type", v)} /></Field>
            <Field label="Temperature"><input className="set-input" type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => set("temperature", e.target.value)} /></Field>
          </div>

          <div className="set-row">
            <Field label="Default Model"><input className="set-input" value={form.model} onChange={(e) => set("model", e.target.value)} placeholder="groq:llama-3.1-8b-instant" /></Field>
            <Field label="Agent ID"><input className="set-input" value={agent.id} readOnly /></Field>
          </div>

          <Field label="Tags">
            <div className="set-tags">
              {(agent.tools || []).slice(0, 6).map((t) => (
                <span key={t} className="set-tag">{t}</span>
              ))}
              {(agent.tools || []).length === 0 && <span style={{ fontSize: 12.5, color: "#a1a9b5" }}>No tools assigned.</span>}
              <button className="set-addtag" type="button" onClick={() => onEditBuilder?.(agent.id)}><Plus size={16} strokeWidth={2.4} /> Edit in Builder</button>
            </div>
          </Field>

          <div className="set-field">
            <label className="set-label">Agent Icon</label>
            <div className="set-icon-row">
              <div className="set-icon-preview"><Bot size={56} strokeWidth={2} /></div>
              <button className="set-changeicon" type="button" disabled><UploadCloud size={18} strokeWidth={2} /> Change Icon</button>
            </div>
          </div>
        </div>

        {/* Right: Version History + Quick Actions + Danger Zone */}
        <div className="set-side">
          <div className="set-panel card">
            <h2 className="set-section-title">Version History</h2>
            <div className="set-versions">
              {versions.length === 0 && (
                <p style={{ fontSize: 13, color: "#a1a9b5", padding: "4px 0" }}>Current: {agent.version || "v1.0.0"} (no prior versions).</p>
              )}
              {versions.map((ver, i) => (
                <div key={ver.id} className="set-version-item">
                  <span className="set-version-lock"><Lock size={18} strokeWidth={2} /></span>
                  <div className="set-version-body">
                    <div className="set-version-v">{ver.version}</div>
                    <div className="set-version-date">{ver.created_at ? new Date(ver.created_at).toLocaleDateString() : ""}</div>
                    {i === 0 && <span className="set-version-current">Latest snapshot</span>}
                    {ver.note && <div className="set-version-note">{ver.note}</div>}
                  </div>
                  <span className="set-version-avatar">{(ver.created_by || "?").slice(0, 2).toUpperCase()}</span>
                </div>
              ))}
            </div>
            <button className="set-viewall" onClick={() => setTab("Versions")}>View all versions <ArrowRight size={16} strokeWidth={2.2} /></button>
          </div>

          <div className="set-panel card">
            <h2 className="set-section-title">Quick Actions</h2>
            <div className="set-actions">
              {QUICK_ACTIONS.map((a) => (
                <button key={a.label} className="set-action" type="button" onClick={a.onClick}>
                  <span className="set-action-icon">{a.icon}</span>
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          <div className="set-panel card set-danger">
            <h2 className="set-danger-title">Danger Zone</h2>
            <button className="set-danger-btn" type="button" onClick={async () => {
              try {
                const r = await agentApi.update(agent.id, { status: status === "active" ? "paused" : "active" });
                setAgent(r.agent);
                toast.success(status === "active" ? "Agent disabled" : "Agent enabled");
              } catch (e) { toast.error(e.message); }
            }}>
              <ShieldCheck size={19} strokeWidth={2} />
              <span className="set-danger-label">{status === "active" ? "Disable Agent" : "Enable Agent"}</span>
            </button>
            <button className="set-danger-btn" type="button" onClick={() => setConfirmDelete(true)}>
              <Trash2 size={19} strokeWidth={2} />
              <span className="set-danger-body">
                <span className="set-danger-label">Delete Agent</span>
                <span className="set-danger-sub">This action cannot be undone.</span>
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Clone modal */}
      <Modal
        open={cloneOpen}
        onClose={() => setCloneOpen(false)}
        title="Clone Agent"
        icon={Copy}
        size="sm"
        footer={
          <>
            <button className="neu-btn h-9 px-4 text-[13px]" onClick={() => setCloneOpen(false)}>Cancel</button>
            <button className="neu-btn-primary h-9 px-4 text-[13px] font-semibold" onClick={doClone}>Clone</button>
          </>
        }
      >
        <label className="block text-[12.5px] font-semibold text-[#5b6678] mb-1.5">New agent name</label>
        <input className="neu-inset w-full h-10 px-3 rounded-xl text-[13.5px] text-[#334155] outline-none" value={cloneName} onChange={(e) => setCloneName(e.target.value)} />
      </Modal>

      {/* Delete confirm modal */}
      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete Agent"
        subtitle={`'${agent.name}' will be removed. This cannot be undone.`}
        icon={Trash2}
        size="sm"
        footer={
          <>
            <button className="neu-btn h-9 px-4 text-[13px]" onClick={() => setConfirmDelete(false)}>Cancel</button>
            <button className="neu-btn-primary h-9 px-4 text-[13px] font-semibold" style={{ background: "#dc2626" }} onClick={doDelete}>Delete</button>
          </>
        }
      >
        Are you sure you want to delete this agent? Its missions and traces are preserved, but it will no longer be available.
      </Modal>
    </div>
  );
};

export default ViewAgentSettings;
