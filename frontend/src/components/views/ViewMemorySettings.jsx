// Knowledge · Memory Settings (ViewMemorySettings.jsx)
// Full redesign: a tabbed settings surface wired to the real backend.
//   GET/PUT /knowledge/memory/settings  (getMemorySettings / updateMemorySettings)
//   per-agent list from agentApi.list(); counts from listMemory().by_agent
//   per-agent clear via clearAgentMemory(agentId) behind a confirm Modal
// Tabs: General · Retention · Privacy · Access Control · Advanced
import { useEffect, useMemo, useState } from "react";
import {
  Loader2, Save, Trash2, Brain, Sliders, Clock, ShieldCheck, Users, AlertTriangle,
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";
import { knowledgeApi } from "../../knowledgeApi.js";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";
import { NeuToggle } from "./settings/SettingsShared.jsx";

const TABS = [
  { label: "General", Icon: Sliders },
  { label: "Retention", Icon: Clock },
  { label: "Privacy", Icon: ShieldCheck },
  { label: "Access Control", Icon: Users },
  { label: "Advanced", Icon: AlertTriangle },
];

/* A compact number field with a label + helper line. */
const NumberField = ({ label, value, onChange, suffix, help }) => (
  <div>
    <label className="block text-[14px] font-semibold text-[#334155] mb-2">{label}</label>
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value) || 0)}
        className="neu-input w-44 h-11 px-4 rounded-xl text-[14px] text-[#334155]"
      />
      {suffix && <span className="text-[14px] text-[#8792a6]">{suffix}</span>}
    </div>
    {help && <p className="text-[12.5px] text-[#8792a6] mt-2">{help}</p>}
  </div>
);

export function ViewMemorySettings() {
  const toast = useToast();
  const [tab, setTab] = useState(0);
  const [settings, setSettings] = useState(null);
  const [agents, setAgents] = useState([]);
  const [counts, setCounts] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmClear, setConfirmClear] = useState(null); // agent id
  const [perAgent, setPerAgent] = useState({});           // {agentId: bool}

  const refreshCounts = () =>
    knowledgeApi.listMemory().then((d) => setCounts(d.by_agent || {})).catch(() => {});

  useEffect(() => {
    knowledgeApi.getMemorySettings()
      .then((s) => { setSettings(s); setPerAgent(s.per_agent || {}); })
      .catch((e) => toast.error(e.message));
    agentApi.list().then((d) => setAgents(d.agents || [])).catch(() => {});
    refreshCounts();
    // eslint-disable-next-line
  }, []);

  const set = (k, v) => setSettings((s) => ({ ...s, [k]: v }));
  const totalEntries = useMemo(() => Object.values(counts).reduce((a, b) => a + b, 0), [counts]);

  const save = async () => {
    setSaving(true);
    try {
      await knowledgeApi.updateMemorySettings({
        global_enabled: settings.global_enabled,
        default_ttl_days: settings.default_ttl_days,
        max_global_entries: settings.max_global_entries,
        per_agent: perAgent,
      });
      toast.success("Memory settings saved");
    } catch (e) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const clearAgent = async () => {
    try {
      const r = await knowledgeApi.clearAgentMemory(confirmClear);
      toast.success(`Cleared ${r.entries_removed} entries`);
      setConfirmClear(null);
      refreshCounts();
    } catch (e) { toast.error(e.message); }
  };

  if (!settings) {
    return <div className="neu-surface h-full grid place-items-center text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>;
  }

  const clearAgentName = agents.find((a) => a.id === confirmClear)?.name || confirmClear;

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-6 sm:px-7 sm:py-7">
      <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Memory Settings" }]} />

      {/* Header */}
      <div className="flex items-start gap-4 mb-5">
        <span className="neu-circle w-11 h-11 rounded-xl text-[#4f46e5] grid place-items-center shrink-0">
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="3" width="16" height="18" rx="2.5"/><path d="M9 3v18" strokeLinecap="round"/><circle cx="14.5" cy="12" r="2.2"/></svg>
        </span>
        <div className="flex-1 pt-0.5">
          <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">Memory Settings</h1>
          <p className="text-[13px] text-[#8792a6] mt-1">Retention, privacy, and usage controls</p>
        </div>
        <button onClick={save} disabled={saving} className="neu-btn-primary h-11 px-5 text-[14px] font-semibold flex items-center gap-2 disabled:opacity-55">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save Changes
        </button>
      </div>

      {/* Two-pane: vertical tab rail + content */}
      <div className="grid grid-cols-[210px_1fr] gap-6">
        {/* Tab rail */}
        <div className="neu-card rounded-2xl p-2 h-fit">
          {TABS.map((t, i) => (
            <button
              key={t.label}
              onClick={() => setTab(i)}
              className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-[14px] font-semibold transition-colors mb-1 last:mb-0 ${
                i === tab ? "neu-inset text-[#4f46e5]" : "text-[#8792a6] hover:text-[#5b6678]"
              }`}
            >
              <t.Icon size={17} /> {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="min-w-0">
          {/* General */}
          {tab === 0 && (
            <section className="neu-card rounded-2xl p-6 space-y-5">
              <h2 className="text-[15px] font-semibold text-[#334155]">General</h2>
              <div className="flex items-start justify-between py-1">
                <div>
                  <p className="text-[14px] font-semibold text-[#334155]">Enable Memory (global)</p>
                  <p className="text-[12.5px] text-[#8792a6] mt-0.5">Master switch. When off, no agent learns from or recalls past runs.</p>
                </div>
                <NeuToggle on={settings.global_enabled} onChange={(v) => set("global_enabled", v)} />
              </div>
              <div className="pt-4 border-t border-[#e2e6ee]">
                <NumberField
                  label="Default TTL (days)"
                  value={settings.default_ttl_days}
                  onChange={(v) => set("default_ttl_days", v)}
                  suffix="days"
                  help="How long new memories are retained before they expire automatically."
                />
              </div>
            </section>
          )}

          {/* Retention */}
          {tab === 1 && (
            <section className="neu-card rounded-2xl p-6 space-y-6">
              <h2 className="text-[15px] font-semibold text-[#334155]">Retention & Limits</h2>
              <NumberField
                label="Default TTL (days)"
                value={settings.default_ttl_days}
                onChange={(v) => set("default_ttl_days", v)}
                suffix="days"
                help="Time-to-live for each memory. Expired memories are purged."
              />
              <div className="pt-5 border-t border-[#e2e6ee]">
                <NumberField
                  label="Maximum stored memories"
                  value={settings.max_global_entries}
                  onChange={(v) => set("max_global_entries", v)}
                  suffix="memories"
                  help="Global cap. The oldest memories are evicted once this limit is reached."
                />
              </div>
              <div className="neu-inset rounded-xl px-4 py-3 flex items-center justify-between">
                <span className="text-[13px] text-[#8792a6]">Currently stored</span>
                <span className="text-[14px] font-semibold text-[#334155]">{totalEntries} / {settings.max_global_entries}</span>
              </div>
            </section>
          )}

          {/* Privacy — per-agent enable toggles */}
          {tab === 2 && (
            <section className="neu-card rounded-2xl p-6">
              <h2 className="text-[15px] font-semibold text-[#334155] mb-1">Privacy — Per-agent Memory</h2>
              <p className="text-[12.5px] text-[#8792a6] mb-5">Control which agents are allowed to keep memory. Changes save with the Save button.</p>
              {agents.length === 0 ? (
                <p className="text-[13px] text-[#9aa6b8] py-8 text-center">No agents found.</p>
              ) : (
                <div className="grid gap-2.5 max-h-[420px] overflow-y-auto pr-1">
                  {agents.map((a) => {
                    const on = perAgent[a.id] ?? a.memory_enabled ?? true;
                    return (
                      <div key={a.id} className="neu-inset rounded-xl px-4 py-3 flex items-center gap-3">
                        <span className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-violet-600 shrink-0"><Brain size={16} /></span>
                        <div className="flex-1 min-w-0">
                          <div className="text-[14px] font-semibold text-[#334155] truncate">{a.name}</div>
                          <p className="text-[12px] text-[#8792a6]">{counts[a.id] || 0} memories</p>
                        </div>
                        <NeuToggle on={on} onChange={(v) => setPerAgent((p) => ({ ...p, [a.id]: v }))} />
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {/* Access Control — per-agent clear */}
          {tab === 3 && (
            <section className="neu-card rounded-2xl p-6">
              <h2 className="text-[15px] font-semibold text-[#334155] mb-1">Access Control</h2>
              <p className="text-[12.5px] text-[#8792a6] mb-5">Clear what a specific agent remembers. This is immediate and cannot be undone.</p>
              {agents.length === 0 ? (
                <p className="text-[13px] text-[#9aa6b8] py-8 text-center">No agents found.</p>
              ) : (
                <div className="grid gap-2.5 max-h-[420px] overflow-y-auto pr-1">
                  {agents.map((a) => (
                    <div key={a.id} className="neu-inset rounded-xl px-4 py-3 flex items-center gap-3">
                      <span className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-violet-600 shrink-0"><Brain size={16} /></span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[14px] font-semibold text-[#334155] truncate">{a.name}</div>
                        <p className="text-[12px] text-[#8792a6]">{counts[a.id] || 0} memories</p>
                      </div>
                      <button onClick={() => setConfirmClear(a.id)} disabled={!counts[a.id]}
                        className="neu-btn-danger inline-flex items-center gap-1.5 h-9 px-3 text-[12.5px] font-semibold text-rose-500 disabled:opacity-40">
                        <Trash2 size={13} /> Clear
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Advanced — danger zone + global stats */}
          {tab === 4 && (
            <section className="space-y-5">
              <div className="neu-card rounded-2xl p-6">
                <h2 className="text-[15px] font-semibold text-[#334155] mb-4">Overview</h2>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "Total memories", value: totalEntries },
                    { label: "Agents w/ memory", value: Object.values(counts).filter((n) => n > 0).length },
                    { label: "Global limit", value: settings.max_global_entries },
                  ].map((s) => (
                    <div key={s.label} className="neu-inset rounded-xl p-4">
                      <p className="text-[12.5px] font-medium text-[#8792a6]">{s.label}</p>
                      <p className="text-[20px] font-semibold text-[#334155] leading-none mt-1.5">{s.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="neu-card rounded-2xl p-6 ring-1 ring-rose-200">
                <h2 className="text-[15px] font-semibold text-rose-500 mb-2 flex items-center gap-2"><AlertTriangle size={18} /> Danger Zone</h2>
                <p className="text-[13px] text-[#8792a6] max-w-[460px]">
                  To wipe an individual agent's memory, use the Access Control tab. Clearing memory permanently
                  deletes remembered facts and cannot be undone.
                </p>
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Confirm clear modal */}
      <Modal open={!!confirmClear} onClose={() => setConfirmClear(null)} title="Clear agent memory?" icon={Trash2} size="sm"
        footer={<>
          <button onClick={() => setConfirmClear(null)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
          <button onClick={clearAgent} className="neu-btn-danger h-9 px-4 text-[13px] font-semibold text-rose-500">Clear All</button>
        </>}>
        <p>This permanently removes all remembered facts for <strong>{clearAgentName}</strong>. It cannot be undone.</p>
      </Modal>
    </div>
  );
}


