// Agents · Create (ViewCreateAgent.jsx)
//
// NEW FLOW — AI-derived multi-agent pipeline:
//   1. The user DESCRIBES the goal in natural language, picks a Department and
//      an Agent Type, then clicks "Design Pipeline".
//   2. agentApi.architect(...) returns a MASTER agent + an ordered list of
//      structured SUB-AGENTS (each with role/input/output/tools/system_prompt).
//   3. The pipeline renders as an ordered list of EDITABLE sub-agent cards:
//      the user can edit text fields, add/remove tools per sub-agent, reorder,
//      delete, and add blank sub-agents.
//   4. On "Create Agent" we POST /agents with the master fields, the edited
//      sub_agents (order reindexed 1..n) and tools = UNION of all sub-agent
//      tools (recomputed fresh, never trusting a stale union).
import { useEffect, useMemo, useState } from "react";
import {
  Sparkles, Loader2, Plus, Check, ArrowRight, RefreshCw, Wrench,
  Bot, X, Search, Pen, LineChart, Megaphone, DollarSign, Users, Cog,
  ChevronUp, ChevronDown, Trash2, GitBranch, ArrowDown,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { NeuChip } from "./settings/SettingsShared.jsx";
import { BrandLogo } from "./brandLogos.jsx";

const AGENT_TYPES = ["research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general"];
const DEPARTMENTS = ["Marketing", "Finance", "Research", "Operations", "HR", "Sales", "Support", "General"];
const MEMORY_OPTIONS = [
  { label: "Long-term (90 days)", days: 90 },
  { label: "Standard (30 days)", days: 30 },
  { label: "Short-term (7 days)", days: 7 },
  { label: "Disabled", days: 0 },
];

const TYPE_ICON = {
  research: Search, marketing: Megaphone, finance: DollarSign, operations: Cog,
  hr: Users, analysis: LineChart, writing: Pen, general: Bot,
};

const inputCls = "neu-inset w-full h-10 px-3 rounded-xl text-[13.5px] text-[#334155] outline-none";
const areaCls = "neu-inset w-full px-3 py-2.5 rounded-xl text-[13.5px] text-[#334155] outline-none resize-y";
const Label = ({ children }) => (
  <label className="block text-[12.5px] font-semibold text-[#5b6678] mb-1.5 mt-4 first:mt-0">{children}</label>
);

// -----------------------------------------------------------------------------
// Shared tool catalog hook: builtins (by name) + external integrations/custom
// (with logos). Used to resolve chips and to power the add-tool picker.
// -----------------------------------------------------------------------------
function useToolCatalog() {
  const [builtins, setBuiltins] = useState([]);   // [{ name, description, category }]
  const [externals, setExternals] = useState([]); // [{ id, name, logo_key, kind, connected }]

  useEffect(() => {
    toolApi.list({ type: "builtin" })
      .then((d) => setBuiltins((d.tools || []).map((t) => ({ name: t.name, description: t.description || "", category: t.category || "" }))))
      .catch(() => {});
    toolApi.listIntegrations()
      .then((d) => setExternals((prev) => [
        ...prev,
        ...(d.integrations || []).map((i) => ({ id: i.id, name: i.name, logo_key: i.logo_key || i.id, kind: "integration", connected: i.status === "connected" })),
      ]))
      .catch(() => {});
    toolApi.list({ type: "custom" })
      .then((d) => setExternals((prev) => [
        ...prev,
        ...(d.tools || []).map((t) => ({ id: t.name, name: t.display_name || t.name, logo_key: t.name, kind: "custom", connected: true })),
      ]))
      .catch(() => {});
  }, []);

  const externalById = useMemo(() => {
    const m = new Map();
    for (const e of externals) m.set(e.id, e);
    return m;
  }, [externals]);
  const builtinByName = useMemo(() => {
    const m = new Map();
    for (const b of builtins) m.set(b.name, b);
    return m;
  }, [builtins]);

  return { builtins, externals, externalById, builtinByName };
}

// A single tool chip: BrandLogo for external, wrench/category badge for builtin.
function ToolChip({ tool, externalById, builtinByName, onRemove }) {
  const ext = externalById.get(tool);
  const builtin = builtinByName.get(tool);
  return (
    <span className="neu-chip inline-flex items-center gap-1.5 px-2.5 py-1 text-[11.5px] font-medium text-[#5b6678]">
      {ext ? (
        <BrandLogo logoKey={ext.logo_key} name={ext.name} size={14} />
      ) : (
        <Wrench size={12} className="text-[#8792a6]" />
      )}
      <span>{ext ? ext.name : builtin ? builtin.name : tool}</span>
      {onRemove && (
        <button type="button" onClick={onRemove} className="text-[#b4bdcc] hover:text-rose-500"><X size={12} /></button>
      )}
    </span>
  );
}

// Add-tool picker popover: builtins listed by name + externals/custom with logos.
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
                  <button key={e.id} type="button" onClick={() => onAdd(e.id)}
                    className="neu-card rounded-xl px-3 py-2 flex items-center gap-2.5 text-left">
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
                  <button key={b.name} type="button" onClick={() => onAdd(b.name)}
                    className="neu-card rounded-xl px-3 py-2 flex items-center gap-2.5 text-left">
                    <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#8792a6]"><Wrench size={15} /></span>
                    <span className="flex-1 min-w-0"><span className="block text-[12.5px] font-semibold text-[#334155] truncate">{b.name}</span>
                      {b.category && <span className="block text-[10.5px] text-[#9aa6b8]">{b.category}</span>}</span>
                    <Plus size={14} className="text-[#4f46e5]" />
                  </button>
                ))}
              </div>
            </div>
          )}
          {fExternals.length === 0 && fBuiltins.length === 0 && (
            <p className="text-[13px] text-[#9aa6b8] text-center py-6">No matching tools.</p>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Sub-agent card (editable).
// -----------------------------------------------------------------------------
function SubAgentCard({ sa, index, total, catalog, onChange, onRemove, onMoveUp, onMoveDown }) {
  const [picking, setPicking] = useState(false);
  const field = (k, v) => onChange({ ...sa, [k]: v });
  const tools = sa.tools || [];

  const removeTool = (t) => field("tools", tools.filter((x) => x !== t));
  const addTool = (t) => { if (!tools.includes(t)) field("tools", [...tools, t]); setPicking(false); };

  return (
    <div className="neu-card rounded-2xl p-4">
      <div className="flex items-start gap-3">
        <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[13px] font-bold text-[#4f46e5] shrink-0 mt-0.5">{index + 1}</span>
        <div className="flex-1 min-w-0">
          <input value={sa.name || ""} onChange={(e) => field("name", e.target.value)} placeholder="Sub-agent name"
            className="neu-inset w-full h-9 px-3 rounded-lg text-[13.5px] font-semibold text-[#334155] outline-none" />
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button type="button" onClick={onMoveUp} disabled={index === 0}
            className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#8792a6] disabled:opacity-30" title="Move up"><ChevronUp size={15} /></button>
          <button type="button" onClick={onMoveDown} disabled={index === total - 1}
            className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#8792a6] disabled:opacity-30" title="Move down"><ChevronDown size={15} /></button>
          <button type="button" onClick={onRemove}
            className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#8792a6] hover:text-rose-500" title="Delete step"><Trash2 size={14} /></button>
        </div>
      </div>

      <div className="mt-3 grid gap-2.5">
        <div>
          <label className="block text-[11px] font-semibold text-[#8792a6] mb-1">Role</label>
          <input value={sa.role || ""} onChange={(e) => field("role", e.target.value)} placeholder="What this step does"
            className="neu-inset w-full h-9 px-3 rounded-lg text-[13px] text-[#334155] outline-none" />
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="block text-[11px] font-semibold text-[#8792a6] mb-1">Input</label>
            <input value={sa.input || ""} onChange={(e) => field("input", e.target.value)} placeholder="Expected input"
              className="neu-inset w-full h-9 px-3 rounded-lg text-[13px] text-[#334155] outline-none" />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-[#8792a6] mb-1">Output</label>
            <input value={sa.output || ""} onChange={(e) => field("output", e.target.value)} placeholder="Produced output"
              className="neu-inset w-full h-9 px-3 rounded-lg text-[13px] text-[#334155] outline-none" />
          </div>
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-[11px] font-semibold text-[#8792a6]">Tools</label>
          <button type="button" onClick={() => setPicking(true)}
            className="neu-btn-ghost inline-flex items-center gap-1 h-7 px-2.5 text-[11px] font-semibold"><Plus size={12} /> Add tool</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {tools.length === 0 && <span className="text-[11.5px] text-[#9aa6b8]">No tools yet.</span>}
          {tools.map((t) => (
            <ToolChip key={t} tool={t} externalById={catalog.externalById} builtinByName={catalog.builtinByName} onRemove={() => removeTool(t)} />
          ))}
        </div>
      </div>

      {picking && (
        <ToolPicker builtins={catalog.builtins} externals={catalog.externals} selected={tools} onAdd={addTool} onClose={() => setPicking(false)} />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Main view.
// -----------------------------------------------------------------------------
export const ViewCreateAgent = ({ onCreated }) => {
  const toast = useToast();
  const catalog = useToolCatalog();

  // Design inputs.
  const [description, setDescription] = useState("");
  const [department, setDepartment] = useState("General");
  const [agentType, setAgentType] = useState("general");
  const [designing, setDesigning] = useState(false);

  // Master agent (editable after design).
  const [master, setMaster] = useState(null); // { name, agent_type, purpose, system_prompt, department }
  const [subAgents, setSubAgents] = useState([]); // structured editable array
  const [memoryTtl, setMemoryTtl] = useState(30);
  const [temperature, setTemperature] = useState(0.7);
  const [saving, setSaving] = useState(false);

  const AgentIcon = TYPE_ICON[master?.agent_type || agentType] || Bot;

  // Union of all sub-agent tools (always recomputed, never stale).
  const unionTools = useMemo(() => {
    const s = new Set();
    for (const sa of subAgents) for (const t of sa.tools || []) s.add(t);
    return [...s];
  }, [subAgents]);

  const designPipeline = async () => {
    if (!description.trim()) { toast.error("Describe what the agent should do first"); return; }
    setDesigning(true);
    try {
      const r = await agentApi.architect({ description: description.trim(), department, agent_type: agentType });
      setMaster({
        name: r.name || "",
        agent_type: r.agent_type || agentType,
        purpose: r.purpose || "",
        system_prompt: r.system_prompt || "",
        department: r.department || department,
      });
      const subs = Array.isArray(r.sub_agents) ? r.sub_agents : [];
      setSubAgents(subs
        .slice()
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
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
      toast.success(`Pipeline designed · ${subs.length} sub-agent${subs.length === 1 ? "" : "s"}`);
    } catch (e) {
      if (/503/.test(e.message)) toast.error("No LLM key configured — add one to design pipelines.");
      else toast.error(e.message);
    } finally { setDesigning(false); }
  };

  const setSub = (idx, next) => setSubAgents((arr) => arr.map((s, i) => (i === idx ? next : s)));
  const removeSub = (idx) => setSubAgents((arr) => arr.filter((_, i) => i !== idx));
  const move = (idx, dir) => setSubAgents((arr) => {
    const j = idx + dir;
    if (j < 0 || j >= arr.length) return arr;
    const next = arr.slice();
    [next[idx], next[j]] = [next[j], next[idx]];
    return next;
  });
  const addBlank = () => setSubAgents((arr) => [...arr, { name: "", role: "", input: "", output: "", tools: [], system_prompt: "", order: arr.length + 1 }]);

  const create = async () => {
    if (!master) return;
    if (!master.name.trim()) { toast.error("Agent name is required"); return; }
    setSaving(true);
    try {
      const sub_agents = subAgents.map((sa, i) => ({
        ...(sa.id ? { id: sa.id } : {}),
        name: sa.name,
        role: sa.role,
        input: sa.input,
        output: sa.output,
        tools: sa.tools || [],
        system_prompt: sa.system_prompt || "",
        order: i + 1,
      }));
      const r = await agentApi.create({
        name: master.name.trim(),
        agent_type: master.agent_type,
        purpose: master.purpose,
        system_prompt: master.system_prompt,
        tools: unionTools,
        sub_agents,
        department_id: master.department,
        temperature,
        memory_enabled: memoryTtl > 0,
        memory_ttl_days: memoryTtl || 30,
        permissions: { knowledge_docs: [] },
      });
      toast.success(`'${master.name}' created · ${sub_agents.length} steps · ${unionTools.length} tools`);
      onCreated?.(r.agent_id);
    } catch (e) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const reset = () => { setMaster(null); setSubAgents([]); setDescription(""); };

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-8">
      <div className="max-w-[1120px] mx-auto">
        <div className="mb-5">
          <h1 className="text-[23px] font-semibold text-[#334155]">Create Agent</h1>
          <p className="text-[14px] text-[#8792a6] mt-1">Describe your goal and AI designs a multi-agent pipeline you can edit.</p>
        </div>

        {/* DESIGN PANEL */}
        <div className="neu-card rounded-2xl p-5 mb-4">
          <h2 className="text-[14px] font-semibold text-[#334155] mb-1 flex items-center gap-1.5"><GitBranch size={15} className="text-[#4f46e5]" /> Describe the goal</h2>
          <p className="text-[12.5px] text-[#8792a6] mb-3">In plain language, say what this agent should accomplish. The architect breaks it into an ordered sub-agent pipeline.</p>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            placeholder="e.g. Research competitor pricing weekly, summarize the findings, and draft an email to the sales team."
            className={`${areaCls} min-h-[80px]`} />
          <div className="grid sm:grid-cols-[1fr_1fr_auto] gap-3 mt-3 items-end">
            <div>
              <Label>Department</Label>
              <select value={department} onChange={(e) => setDepartment(e.target.value)} className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13.5px]">
                {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <Label>Agent Type</Label>
              <select value={agentType} onChange={(e) => setAgentType(e.target.value)} className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13.5px]">
                {AGENT_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <button onClick={designPipeline} disabled={designing || !description.trim()}
              className="neu-btn-primary inline-flex items-center justify-center gap-2 h-10 px-5 text-[14px] font-semibold">
              {designing ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Design Pipeline
            </button>
          </div>
        </div>

        {/* EMPTY STATE */}
        {!master && (
          <div className="neu-inset rounded-2xl py-14 px-6 text-center">
            <span className="w-14 h-14 mx-auto rounded-2xl grid place-items-center text-[#4f46e5] neu-circle mb-4"><GitBranch size={26} /></span>
            <h3 className="text-[15px] font-semibold text-[#334155]">No pipeline yet</h3>
            <p className="text-[13px] text-[#8792a6] mt-1.5 max-w-md mx-auto">
              Describe your goal above and click <b className="text-[#5b6678]">Design Pipeline</b>. The AI architect will design an ordered
              list of specialized sub-agents — each with its own role, inputs, outputs, and tools — that you can fully edit before creating the agent.
            </p>
          </div>
        )}

        {/* DESIGNED PIPELINE */}
        {master && (
          <>
            {/* Master header */}
            <div className="neu-card rounded-2xl p-5 mb-4">
              <div className="flex items-start gap-4">
                <span className="w-14 h-14 rounded-2xl grid place-items-center text-white bg-gradient-to-br from-[#6366f1] to-[#4338ca] shrink-0"><AgentIcon size={26} /></span>
                <div className="flex-1 min-w-0">
                  <input value={master.name} onChange={(e) => setMaster((m) => ({ ...m, name: e.target.value }))} placeholder="Agent name"
                    className="neu-inset w-full h-10 px-3 rounded-xl text-[15px] font-bold text-[#334155] outline-none" />
                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    <NeuChip>{master.agent_type}</NeuChip>
                    <NeuChip>{master.department}</NeuChip>
                    <NeuChip>{subAgents.length} steps</NeuChip>
                    <NeuChip>{unionTools.length} tools</NeuChip>
                  </div>
                </div>
              </div>
              <Label>Purpose</Label>
              <textarea className={`${areaCls} min-h-[56px]`} value={master.purpose} onChange={(e) => setMaster((m) => ({ ...m, purpose: e.target.value }))} placeholder="What this agent is responsible for." />
              <Label>System Prompt (optional, editable)</Label>
              <textarea className={`${areaCls} min-h-[72px] font-mono`} value={master.system_prompt} onChange={(e) => setMaster((m) => ({ ...m, system_prompt: e.target.value }))} placeholder="Behavioral instructions." />
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <Label>Memory</Label>
                  <select value={memoryTtl} onChange={(e) => setMemoryTtl(Number(e.target.value))} className="neu-input neu-select w-full h-10 px-3 rounded-xl text-[13.5px]">
                    {MEMORY_OPTIONS.map((m) => <option key={m.days} value={m.days}>{m.label}</option>)}
                  </select>
                </div>
                <div>
                  <Label>Temperature · {temperature}</Label>
                  <input type="range" min="0" max="1" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full accent-[#4f46e5] mt-3" />
                </div>
              </div>
            </div>

            {/* Sub-agent pipeline */}
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-[14px] font-semibold text-[#334155]">Pipeline · {subAgents.length} sub-agent{subAgents.length === 1 ? "" : "s"}</h2>
              <button onClick={addBlank} className="neu-btn-ghost inline-flex items-center gap-1.5 h-8 px-3 text-[12px] font-semibold"><Plus size={13} /> Add step</button>
            </div>
            <div className="space-y-3">
              {subAgents.length === 0 && (
                <div className="neu-inset rounded-xl py-8 text-center text-[13px] text-[#8792a6]">No sub-agents. Add a step to build the pipeline.</div>
              )}
              {subAgents.map((sa, i) => (
                <div key={sa.id || i}>
                  <SubAgentCard sa={sa} index={i} total={subAgents.length} catalog={catalog}
                    onChange={(next) => setSub(i, next)} onRemove={() => removeSub(i)}
                    onMoveUp={() => move(i, -1)} onMoveDown={() => move(i, 1)} />
                  {i < subAgents.length - 1 && (
                    <div className="flex justify-center py-1 text-[#c3cbda]"><ArrowDown size={16} /></div>
                  )}
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2.5 mt-5">
              <button onClick={reset} className="neu-btn-ghost inline-flex items-center gap-1.5 h-10 px-4 text-[13px] font-semibold"><RefreshCw size={15} /> Reset</button>
              <button onClick={create} disabled={saving || !master.name.trim()}
                className="neu-btn-primary inline-flex items-center gap-2 h-10 px-5 text-[14px] font-semibold">
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />} Create Agent <ArrowRight size={16} />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ViewCreateAgent;
