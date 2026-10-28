// AgentConfigModal — configure an agent WITHOUT leaving the Agents overview.
// Opened by clicking an agent card. Fully functional: loads the agent
// (agentApi.get), edits core fields + saves (agentApi.update), runs a quick
// test (agentApi.test), and deletes (agentApi.remove). Nothing is a stub.
import { useEffect, useMemo, useState } from "react";
import { Bot, Loader2, Check, Play, Trash2, Settings2, Send, Wrench, Plug, Plus, X, Search, ArrowRight } from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";
import { Markdown } from "../ui/Markdown.jsx";
import { BrandLogo } from "./brandLogos.jsx";

const TYPES = ["research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general"];
const TABS = ["Configure", "Tools", "Test"];

// Tool chip: BrandLogo for external, wrench badge for builtin.
function ToolChip({ tool, externalById, builtinByName, onRemove }) {
  const ext = externalById.get(tool);
  const builtin = builtinByName.get(tool);
  return (
    <span className="neu-chip inline-flex items-center gap-1.5 px-2.5 py-1 text-[11.5px] font-medium text-[#5b6678]">
      {ext ? <BrandLogo logoKey={ext.logo_key} name={ext.name} size={14} /> : <Wrench size={12} className="text-[#8792a6]" />}
      <span>{ext ? ext.name : builtin ? builtin.name : tool}</span>
      {onRemove && <button type="button" onClick={onRemove} className="text-[#b4bdcc] hover:text-rose-500"><X size={12} /></button>}
    </span>
  );
}

// Add-tool picker popover (builtins by name + externals/custom with logos).
function ToolPicker({ builtins, externals, selected, onAdd, onClose }) {
  const [q, setQ] = useState("");
  const query = q.trim().toLowerCase();
  const sel = new Set(selected);
  const fExternals = externals.filter((e) => !sel.has(e.id) && (!query || e.name.toLowerCase().includes(query) || e.id.toLowerCase().includes(query)));
  const fBuiltins = builtins.filter((b) => !sel.has(b.name) && (!query || b.name.toLowerCase().includes(query) || (b.category || "").toLowerCase().includes(query)));
  return (
    <div className="fixed inset-0 z-[210] bg-slate-900/50 grid place-items-center p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-md bg-[#eef1f6] rounded-2xl shadow-[0_20px_60px_rgba(15,23,42,0.35)] p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[15px] font-semibold text-[#334155]">Add a tool</h3>
          <button onClick={onClose} className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#8792a6]"><X size={17} /></button>
        </div>
        <div className="neu-inset rounded-xl flex items-center gap-2 px-3 h-10 mb-3">
          <Search size={15} className="text-[#9aa6b8]" />
          <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search builtins or integrations…"
            className="bg-transparent outline-none text-[13px] text-[#334155] w-full" />
        </div>
        <div className="max-h-[55vh] overflow-y-auto scrollbar-hide space-y-3">
          {fExternals.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-1.5">Integrations &amp; custom</p>
              <div className="grid gap-1.5">
                {fExternals.map((e) => (
                  <button key={e.id} type="button" onClick={() => onAdd(e.id)} className="neu-card rounded-xl px-3 py-2 flex items-center gap-2.5 text-left">
                    <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center"><BrandLogo logoKey={e.logo_key} name={e.name} size={16} /></span>
                    <span className="flex-1 min-w-0"><span className="block text-[12.5px] font-semibold text-[#334155] truncate">{e.name}</span>
                      <span className="block text-[10.5px] text-[#9aa6b8]">{e.kind === "custom" ? "Custom tool" : e.connected ? "connected" : "not connected"}</span></span>
                    <Plus size={14} className="text-[#4f46e5]" />
                  </button>
                ))}
              </div>
            </div>
          )}
          {fBuiltins.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-1.5">Built-in tools</p>
              <div className="grid gap-1.5">
                {fBuiltins.map((b) => (
                  <button key={b.name} type="button" onClick={() => onAdd(b.name)} className="neu-card rounded-xl px-3 py-2 flex items-center gap-2.5 text-left">
                    <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#8792a6]"><Wrench size={15} /></span>
                    <span className="flex-1 min-w-0"><span className="block text-[12.5px] font-semibold text-[#334155] truncate">{b.name}</span>
                      {b.category && <span className="block text-[10.5px] text-[#9aa6b8]">{b.category}</span>}</span>
                    <Plus size={14} className="text-[#4f46e5]" />
                  </button>
                ))}
              </div>
            </div>
          )}
          {fExternals.length === 0 && fBuiltins.length === 0 && <p className="text-[13px] text-[#9aa6b8] text-center py-6">No matching tools.</p>}
        </div>
      </div>
    </div>
  );
}

// Compact editable sub-agent card for the pipeline Tools tab.
function PipelineStep({ sa, index, builtins, externals, externalById, builtinByName, onChange }) {
  const [picking, setPicking] = useState(false);
  const tools = sa.tools || [];
  const removeTool = (t) => onChange({ ...sa, tools: tools.filter((x) => x !== t) });
  const addTool = (t) => { if (!tools.includes(t)) onChange({ ...sa, tools: [...tools, t] }); setPicking(false); };
  return (
    <div className="neu-card rounded-xl p-3.5">
      <div className="flex items-center gap-2.5">
        <span className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[12px] font-bold text-[#4f46e5] shrink-0">{index + 1}</span>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-[#334155] truncate">{sa.name || `Step ${index + 1}`}</p>
          {sa.role && <p className="text-[11px] text-[#8792a6] truncate">{sa.role}</p>}
        </div>
      </div>
      {(sa.input || sa.output) && (
        <div className="flex items-center gap-1.5 mt-2 text-[11px] text-[#9aa6b8]">
          <span className="truncate">{sa.input || "—"}</span>
          <ArrowRight size={11} className="shrink-0" />
          <span className="truncate">{sa.output || "—"}</span>
        </div>
      )}
      <div className="flex items-center justify-between mt-2.5 mb-1.5">
        <span className="text-[11px] font-semibold text-[#8792a6]">Tools</span>
        <button type="button" onClick={() => setPicking(true)} className="neu-btn-ghost inline-flex items-center gap-1 h-7 px-2 text-[10.5px] font-semibold"><Plus size={11} /> Add</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {tools.length === 0 && <span className="text-[11px] text-[#9aa6b8]">No tools.</span>}
        {tools.map((t) => <ToolChip key={t} tool={t} externalById={externalById} builtinByName={builtinByName} onRemove={() => removeTool(t)} />)}
      </div>
      {picking && <ToolPicker builtins={builtins} externals={externals} selected={tools} onAdd={addTool} onClose={() => setPicking(false)} />}
    </div>
  );
}

export function AgentConfigModal({ open, agentId, onClose, onSaved, onDeleted }) {
  const toast = useToast();
  const [tab, setTab] = useState("Configure");
  const [loading, setLoading] = useState(true);
  const [agent, setAgent] = useState(null);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Tools
  const [extTools, setExtTools] = useState([]);   // available external tools (integrations + custom)
  const [attached, setAttached] = useState([]);    // tool ids attached to this agent (legacy path)
  const [builtins, setBuiltins] = useState([]);    // [{ name, description, category }]
  const [builtinCount, setBuiltinCount] = useState(0);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [savingTools, setSavingTools] = useState(false);
  const [pipeline, setPipeline] = useState([]); // editable structured sub_agents

  // Quick-test state
  const [msg, setMsg] = useState("");
  const [testing, setTesting] = useState(false);
  const [reply, setReply] = useState("");

  useEffect(() => {
    if (!open || !agentId) return;
    setTab("Configure"); setLoading(true); setReply(""); setMsg("");
    agentApi.get(agentId)
      .then((a) => {
        setAgent(a);
        setAttached(a.tools || []);
        const subs = Array.isArray(a.sub_agents) ? a.sub_agents : [];
        setPipeline(subs
          .slice()
          .sort((x, y) => (x.order ?? 0) - (y.order ?? 0))
          .map((sa, i) => ({
            id: sa.id,
            name: sa.name || "",
            role: sa.role || "",
            input: sa.input || "",
            output: sa.output || "",
            tools: Array.isArray(sa.tools) ? sa.tools : [],
            system_prompt: sa.system_prompt || "",
            order: i + 1,
          })));
        setForm({
          name: a.name || "",
          purpose: a.purpose || "",
          agent_type: a.agent_type || "general",
          model: a.model || "",
          temperature: a.temperature ?? 0.7,
          system_prompt: a.system_prompt || "",
        });
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));

    // Load available external tools (integrations + custom) + built-in count.
    setToolsLoading(true);
    Promise.allSettled([
      toolApi.listIntegrations(),
      toolApi.list({ type: "custom" }),
      toolApi.list({ type: "builtin" }),
    ]).then(([ints, custom, builtin]) => {
      const list = [];
      if (ints.status === "fulfilled") {
        for (const i of ints.value.integrations || [])
          list.push({ id: i.id, name: i.name, connected: i.status === "connected", kind: "integration", logo_key: i.logo_key || i.id });
      }
      if (custom.status === "fulfilled") {
        for (const t of custom.value.tools || [])
          list.push({ id: t.name, name: t.display_name || t.name, connected: true, kind: "custom", logo_key: t.name });
      }
      setExtTools(list);
      if (builtin.status === "fulfilled") {
        const bt = builtin.value.tools || [];
        setBuiltins(bt.map((t) => ({ name: t.name, description: t.description || "", category: t.category || "" })));
        setBuiltinCount(bt.length);
      }
    }).finally(() => setToolsLoading(false));
    // eslint-disable-next-line
  }, [open, agentId]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    if (!form.name.trim()) { toast.error("Agent name is required"); return; }
    setSaving(true);
    try {
      await agentApi.update(agentId, {
        name: form.name.trim(),
        purpose: form.purpose,
        agent_type: form.agent_type,
        model: form.model.trim(),
        temperature: Number(form.temperature),
        system_prompt: form.system_prompt,
      });
      toast.success("Agent saved");
      onSaved?.();
      onClose?.();
    } catch (e) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const del = async () => {
    if (!window.confirm(`Delete agent "${form?.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await agentApi.remove(agentId);
      toast.success("Agent deleted");
      onDeleted?.();
      onClose?.();
    } catch (e) { toast.error(e.message); }
    finally { setDeleting(false); }
  };

  const runTest = async () => {
    if (!msg.trim()) return;
    setTesting(true); setReply("");
    try {
      const r = await agentApi.test(agentId, msg.trim());
      setReply(r.reply || r.output || r.result || JSON.stringify(r, null, 2));
    } catch (e) { setReply(`Error: ${e.message}`); toast.error(e.message); }
    finally { setTesting(false); }
  };

  const toggleTool = (id) =>
    setAttached((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));

  const hasPipeline = pipeline.length > 0;

  const externalById = useMemo(() => {
    const m = new Map();
    for (const e of extTools) m.set(e.id, e);
    return m;
  }, [extTools]);
  const builtinByName = useMemo(() => {
    const m = new Map();
    for (const b of builtins) m.set(b.name, b);
    return m;
  }, [builtins]);

  const unionTools = useMemo(() => {
    const s = new Set();
    for (const sa of pipeline) for (const t of sa.tools || []) s.add(t);
    return [...s];
  }, [pipeline]);

  const setStep = (idx, next) => setPipeline((arr) => arr.map((s, i) => (i === idx ? next : s)));

  const saveTools = async () => {
    setSavingTools(true);
    try {
      if (hasPipeline) {
        const sub_agents = pipeline.map((sa, i) => ({
          ...(sa.id ? { id: sa.id } : {}),
          name: sa.name,
          role: sa.role,
          input: sa.input,
          output: sa.output,
          tools: sa.tools || [],
          system_prompt: sa.system_prompt || "",
          order: i + 1,
        }));
        await agentApi.update(agentId, { tools: unionTools, sub_agents });
      } else {
        await agentApi.update(agentId, { tools: attached });
      }
      toast.success("Tools updated");
      onSaved?.();
    } catch (e) { toast.error(e.message); }
    finally { setSavingTools(false); }
  };

  const extAttachedCount = useMemo(() => {
    const extIds = new Set(extTools.map((t) => t.id));
    return attached.filter((id) => extIds.has(id)).length;
  }, [attached, extTools]);

  const footer = tab === "Configure" ? (
    <>
      <button onClick={del} disabled={deleting}
        className="neu-btn-ghost inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold text-rose-600 mr-auto">
        {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />} Delete
      </button>
      <button onClick={onClose} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
      <button onClick={save} disabled={saving || loading}
        className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
        {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Save Changes
      </button>
    </>
  ) : tab === "Tools" ? (
    <>
      <button onClick={onClose} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Cancel</button>
      <button onClick={saveTools} disabled={savingTools || toolsLoading}
        className="neu-btn-primary inline-flex items-center gap-2 h-9 px-4 text-[13px] font-semibold">
        {savingTools ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Save Tools
      </button>
    </>
  ) : (
    <button onClick={onClose} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold">Close</button>
  );

  return (
    <Modal open={open} onClose={onClose} icon={Settings2} size="xl"
      title={form ? `Configure · ${form.name}` : "Configure Agent"}
      subtitle={agent ? `${agent.agent_type} agent · ${(agent.tools || []).length} tools` : ""}
      footer={footer}>
      {loading || !form ? (
        <div className="grid place-items-center py-14 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
      ) : (
        <div>
          {/* Tabs */}
          <div className="neu-inset inline-flex p-1 rounded-xl mb-4">
            {TABS.map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={`h-8 px-4 rounded-lg text-[12.5px] font-semibold ${tab === t ? "neu-raised text-[#4f46e5]" : "text-[#8792a6]"}`}>
                {t}
              </button>
            ))}
          </div>

          {tab === "Configure" ? (
            <div className="space-y-3">
              <div>
                <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Agent Name</label>
                <input value={form.name} onChange={(e) => set("name", e.target.value)}
                  className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Purpose / Description</label>
                <textarea rows={2} value={form.purpose} onChange={(e) => set("purpose", e.target.value)}
                  className="neu-inset w-full px-3 py-2 rounded-xl text-[13px] outline-none resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Type</label>
                  <select value={form.agent_type} onChange={(e) => set("agent_type", e.target.value)}
                    className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13px]">
                    {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Temperature</label>
                  <input type="number" step="0.1" min="0" max="2" value={form.temperature}
                    onChange={(e) => set("temperature", e.target.value)}
                    className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Default Model</label>
                <input value={form.model} onChange={(e) => set("model", e.target.value)}
                  placeholder="groq:llama-3.1-8b-instant"
                  className="neu-inset w-full h-10 px-3 rounded-xl text-[13px] outline-none" />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-[#5b6678] mb-1.5">Instructions (System Prompt)</label>
                <textarea rows={5} value={form.system_prompt} onChange={(e) => set("system_prompt", e.target.value)}
                  className="neu-inset w-full px-3 py-2 rounded-xl text-[13px] outline-none resize-none font-mono" />
              </div>
              <p className="text-[11.5px] text-[#9aa6b8]">
                Built-in tools are auto-attached. External tools are managed from the agent's Builder.
              </p>
            </div>
          ) : tab === "Tools" ? (
            <div className="space-y-3">
              {toolsLoading ? (
                <div className="grid place-items-center py-10 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
              ) : hasPipeline ? (
                <>
                  <div className="neu-inset rounded-xl px-3.5 py-2.5 flex items-center gap-2.5 text-[12.5px] text-[#5b6678]">
                    <Wrench size={15} className="text-[#4f46e5]" />
                    <span>This agent runs a <b className="text-[#334155]">{pipeline.length}-step</b> sub-agent pipeline. Edit each step's tools below — the master agent's tools are the union of all steps.</span>
                  </div>
                  <div className="space-y-2.5 max-h-[380px] overflow-y-auto scrollbar-hide pr-0.5">
                    {pipeline.map((sa, i) => (
                      <PipelineStep key={sa.id || i} sa={sa} index={i}
                        builtins={builtins} externals={extTools} externalById={externalById} builtinByName={builtinByName}
                        onChange={(next) => setStep(i, next)} />
                    ))}
                  </div>
                  <p className="text-[11.5px] text-[#9aa6b8] inline-flex items-center gap-1.5">
                    <Plug size={12} /> {unionTools.length} tool{unionTools.length === 1 ? "" : "s"} across all steps. Click Save Tools to apply.
                  </p>
                </>
              ) : (
                <>
                  <div className="neu-inset rounded-xl px-3.5 py-2.5 flex items-center gap-2.5 text-[12.5px] text-[#5b6678]">
                    <Wrench size={15} className="text-[#4f46e5]" />
                    <span><b className="text-[#334155]">{builtinCount}</b> built-in tools are auto-attached to every agent. Select which <b className="text-[#334155]">external</b> tools (integrations &amp; custom) this agent can use.</span>
                  </div>
                  {extTools.length === 0 ? (
                    <div className="neu-inset rounded-xl py-10 text-center text-[13px] text-[#8792a6]">
                      No external tools yet. Connect integrations or create custom tools in the Tools section.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[340px] overflow-y-auto scrollbar-hide pr-0.5">
                      {extTools.map((t) => {
                        const on = attached.includes(t.id);
                        return (
                          <button key={t.id} type="button" onClick={() => toggleTool(t.id)}
                            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all ${on ? "neu-raised" : "neu-inset"}`}>
                            <span className="w-6 h-6 grid place-items-center shrink-0">
                              <BrandLogo logoKey={t.logo_key} name={t.name} size={20} />
                            </span>
                            <span className="flex-1 min-w-0">
                              <span className="block text-[13px] font-semibold text-[#334155] truncate">{t.name}</span>
                              <span className="block text-[11px] text-[#9aa6b8]">
                                {t.kind === "custom" ? "Custom tool" : t.connected ? "Integration · connected" : "Integration · not connected"}
                              </span>
                            </span>
                            <span className={`w-5 h-5 rounded-md grid place-items-center shrink-0 ${on ? "bg-[#4f46e5] text-white" : "neu-circle text-transparent"}`}>
                              <Check size={13} strokeWidth={3} />
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                  <p className="text-[11.5px] text-[#9aa6b8] inline-flex items-center gap-1.5">
                    <Plug size={12} /> {extAttachedCount} external tool{extAttachedCount === 1 ? "" : "s"} attached. Click Save Tools to apply.
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input value={msg} onChange={(e) => setMsg(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !testing && runTest()}
                  placeholder="Send a test message to this agent…"
                  className="neu-inset flex-1 h-10 px-3 rounded-xl text-[13px] outline-none" />
                <button onClick={runTest} disabled={testing || !msg.trim()}
                  className="neu-btn-primary inline-flex items-center gap-2 h-10 px-4 text-[13px] font-semibold">
                  {testing ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Run
                </button>
              </div>
              <div className="neu-inset rounded-xl p-3.5 min-h-[160px] text-[13px] text-[#334155]">
                {testing ? (
                  <span className="text-[#9aa6b8] inline-flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Running the agent…</span>
                ) : reply ? (
                  <Markdown>{reply}</Markdown>
                ) : (
                  <span className="text-[#9aa6b8]">The agent's response will appear here.</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default AgentConfigModal;
