// Agent Builder — mock layout (agent-builder) wired to the real backend.
// Loads the preset agent, renders the orchestrator node graph (orchestrator ->
// sub-agents -> tools), lets you edit the tools[] and sub_agents[] lists, and
// saves via agentApi.update(id, {tools, sub_agents}).
import { useEffect, useMemo, useState } from "react";
import {
  Play,
  ChevronDown,
  Plus,
  Minus,
  Maximize2,
  Layers,
  Bot,
  FileText,
  Search,
  Send,
  CheckCircle2,
  RefreshCw,
  Save,
  ArrowRight,
  Loader2,
  X,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { toolApi } from "../../toolApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";
import { Markdown } from "../ui/Markdown.jsx";

const TOP_TABS = ["Overview", "Instructions", "Tools", "Memory", "Permissions", "Model"];
const CFG_TABS = ["General", "Instructions", "Tools", "Memory", "Permissions"];
const TINTS = ["ab-ic-dark", "ab-ic-light", "ab-ic-indigo"];

export const ViewAgentBuilder = ({ presetAgentId }) => {
  const toast = useToast();
  const [topTab, setTopTab] = useState("Overview");
  const [cfgTab, setCfgTab] = useState("General");

  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [allAgents, setAllAgents] = useState([]);
  const [allTools, setAllTools] = useState([]);
  const [tools, setTools] = useState([]);
  const [subAgents, setSubAgents] = useState([]);
  const [saving, setSaving] = useState(false);

  const [toolPicker, setToolPicker] = useState(false);
  const [subPicker, setSubPicker] = useState(false);

  // Test panel
  const [testMsg, setTestMsg] = useState("");
  const [testing, setTesting] = useState(false);
  const [recentTests, setRecentTests] = useState([]);

  useEffect(() => {
    toolApi.list({ enabled: true }).then((d) => setAllTools(d.tools || [])).catch(() => {});
    agentApi.list().then((d) => setAllAgents(d.agents || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!presetAgentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    agentApi
      .get(presetAgentId)
      .then((a) => {
        setAgent(a);
        setTools(a.tools || []);
        setSubAgents(a.sub_agents || []);
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetAgentId]);

  const toolLabel = (name) => allTools.find((t) => t.name === name)?.display_name || name;
  const agentName = (id) => allAgents.find((a) => a.id === id)?.name || id;

  const toggleTool = (name) =>
    setTools((t) => (t.includes(name) ? t.filter((x) => x !== name) : [...t, name]));
  const toggleSub = (id) =>
    setSubAgents((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const dirty = useMemo(() => {
    if (!agent) return false;
    const a = (agent.tools || []).slice().sort().join(",");
    const b = tools.slice().sort().join(",");
    const c = (agent.sub_agents || []).slice().sort().join(",");
    const d = subAgents.slice().sort().join(",");
    return a !== b || c !== d;
  }, [agent, tools, subAgents]);

  const save = async () => {
    if (!agent) return;
    setSaving(true);
    try {
      const r = await agentApi.update(agent.id, { tools, sub_agents: subAgents });
      setAgent(r.agent);
      toast.success("Agent updated");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    if (!agent || !testMsg.trim()) return;
    setTesting(true);
    const msg = testMsg;
    try {
      const r = await agentApi.test(agent.id, msg);
      setRecentTests((prev) => [{ title: msg, ok: r.ok, output: r.output, trace: r.trace, time: "just now" }, ...prev].slice(0, 6));
      setTestMsg("");
      toast[r.ok ? "success" : "error"](r.ok ? "Test completed" : "Test failed");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="agent-builder">
        <div className="ab-canvas card" style={{ display: "grid", placeItems: "center", minHeight: 240 }}>
          <Loader2 className="animate-spin" />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="agent-builder">
        <div className="ab-header card">
          <div className="ab-header-info">
            <h2>No agent selected</h2>
            <p>Open an agent from the Overview to edit its graph.</p>
          </div>
        </div>
      </div>
    );
  }

  const status = agent.status || "active";

  return (
    <div className="agent-builder">
      {/* Top tabs */}
      <div className="ab-toptabs">
        {TOP_TABS.map((t) => (
          <button key={t} className={`ab-toptab ${topTab === t ? "active" : ""}`} onClick={() => setTopTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Agent header */}
      <div className="ab-header card">
        <div className="ab-header-icon">
          <Bot size={26} strokeWidth={2} />
        </div>
        <div className="ab-header-info">
          <div className="ab-header-titlerow">
            <h2>{agent.name}</h2>
            <span className="ab-status">
              <span className="ab-status-dot" /> {status[0].toUpperCase() + status.slice(1)}
            </span>
            <button className="ab-version">
              {agent.version || "v1.0.0"} <ChevronDown size={15} strokeWidth={2} />
            </button>
          </div>
          <p>{agent.purpose || agent.system_prompt?.slice(0, 120)}</p>
        </div>
        <button className="ab-test-btn" onClick={runTest} disabled={testing || !testMsg.trim()}>
          <Play size={16} strokeWidth={2} fill="currentColor" /> Test
        </button>
      </div>

      {/* Node graph canvas */}
      <div className="ab-canvas card">
        <div className="ab-canvas-controls">
          <button aria-label="Zoom in"><Plus size={18} strokeWidth={2.4} /></button>
          <button aria-label="Zoom out"><Minus size={18} strokeWidth={2.4} /></button>
        </div>
        <div className="ab-canvas-controls ab-canvas-controls-2">
          <button aria-label="Fit"><Maximize2 size={17} strokeWidth={2} /></button>
        </div>
        <div className="ab-canvas-controls ab-canvas-controls-3">
          <button aria-label="Layers"><Layers size={17} strokeWidth={2} /></button>
        </div>

        {/* Orchestrator */}
        <div className="ab-graph">
          <div className="ab-orch">
            <div className="ab-orch-ring">
              <div className="ab-orch-icon">
                <Bot size={30} strokeWidth={2} />
              </div>
            </div>
            <h3>{agent.name}</h3>
            <span className="ab-node-role">(Orchestration)</span>
          </div>

          {/* Connectors: orchestrator -> specialists */}
          <svg className="ab-lines ab-lines-1" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true">
            <path d="M450 4 L450 30" />
            <path d="M150 116 L150 60 Q150 44 166 44 L734 44 Q750 44 750 60 L750 116" />
            <path d="M450 44 L450 116" />
            <circle cx="150" cy="116" r="4" className="ab-dot" />
            <circle cx="450" cy="116" r="4" className="ab-dot" />
            <circle cx="750" cy="116" r="4" className="ab-dot" />
          </svg>

          {/* Specialists row (real sub_agents) */}
          <div className="ab-row">
            {subAgents.length === 0 ? (
              <div className="ab-node" onClick={() => setSubPicker(true)} style={{ cursor: "pointer", opacity: 0.7 }}>
                <div className="ab-node-icon ab-ic-light"><Plus size={20} strokeWidth={2} /></div>
                <h4>Add Sub-Agent</h4>
                <span className="ab-node-role">(none)</span>
              </div>
            ) : (
              subAgents.map((id, i) => (
                <div key={id} className="ab-node">
                  <div className={`ab-node-icon ${TINTS[i % TINTS.length]}`}><Bot size={20} strokeWidth={2} /></div>
                  <h4>{agentName(id)}</h4>
                  <span className="ab-node-role">(Specialist)</span>
                </div>
              ))
            )}
          </div>

          {/* Connectors: specialists -> tools */}
          <svg className="ab-lines ab-lines-2" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true">
            <path d="M150 4 L150 30" />
            <path d="M150 30 L150 44 Q150 60 166 60 L734 60 Q750 60 750 44 L750 30" />
            <path d="M150 60 L150 116" />
            <path d="M450 60 L450 116" />
            <path d="M750 60 L750 116" />
            <circle cx="150" cy="116" r="4" className="ab-dot" />
            <circle cx="450" cy="116" r="4" className="ab-dot" />
            <circle cx="750" cy="116" r="4" className="ab-dot" />
          </svg>

          {/* Tools row (real tools) */}
          <div className="ab-row">
            {tools.length === 0 ? (
              <div className="ab-node" onClick={() => setToolPicker(true)} style={{ cursor: "pointer", opacity: 0.7 }}>
                <div className="ab-node-icon ab-ic-dark"><Plus size={20} strokeWidth={2} /></div>
                <h4>Add Tool</h4>
                <span className="ab-node-role">(none)</span>
              </div>
            ) : (
              tools.map((name) => (
                <div key={name} className="ab-node">
                  <div className="ab-node-icon ab-ic-dark"><Search size={20} strokeWidth={2} /></div>
                  <h4>{toolLabel(name)}</h4>
                  <span className="ab-node-role">(Tool)</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bottom two-column area */}
      <div className="ab-bottom">
        {/* Node Configuration */}
        <div className="ab-config card">
          <h3 className="ab-panel-title">Node Configuration</h3>
          <div className="ab-cfg-tabs">
            {CFG_TABS.map((t) => (
              <button key={t} className={`ab-cfg-tab ${cfgTab === t ? "active" : ""}`} onClick={() => setCfgTab(t)}>
                {t}
              </button>
            ))}
          </div>

          <label className="ab-label">Node Name</label>
          <input className="ab-input" value={agent.name} readOnly />

          <label className="ab-label">Tools ({tools.length})</label>
          <div className="ca-chips" style={{ marginBottom: 10 }}>
            {tools.map((name) => (
              <span key={name} className="ca-chip">
                {toolLabel(name)}
                <span className="ca-chip-x" style={{ cursor: "pointer" }} onClick={() => toggleTool(name)}>×</span>
              </span>
            ))}
            <button className="ca-add-source" type="button" onClick={() => setToolPicker(true)}>
              <Plus size={16} strokeWidth={2.4} /> Add Tool
            </button>
          </div>

          <label className="ab-label">Sub-Agents ({subAgents.length})</label>
          <div className="ca-chips">
            {subAgents.map((id) => (
              <span key={id} className="ca-chip">
                {agentName(id)}
                <span className="ca-chip-x" style={{ cursor: "pointer" }} onClick={() => toggleSub(id)}>×</span>
              </span>
            ))}
            <button className="ca-add-source" type="button" onClick={() => setSubPicker(true)}>
              <Plus size={16} strokeWidth={2.4} /> Add Sub-Agent
            </button>
          </div>

          <label className="ab-label">System Prompt</label>
          <div className="ab-prompt-wrap">
            <textarea className="ab-textarea ab-prompt" rows={3} value={agent.system_prompt || ""} readOnly />
            <span className="ab-charcount">{(agent.system_prompt || "").length}/4000</span>
          </div>
        </div>

        {/* Test Agent + Recent Tests */}
        <div className="ab-right">
          <div className="ab-test card">
            <h3 className="ab-panel-title">Test Agent</h3>
            <div className="ab-test-input">
              <textarea
                placeholder="Send a test message..."
                rows={2}
                value={testMsg}
                onChange={(e) => setTestMsg(e.target.value)}
              />
              <button className="ab-send" aria-label="Send" onClick={runTest} disabled={testing || !testMsg.trim()}>
                {testing ? <Loader2 size={16} strokeWidth={2} className="animate-spin" /> : <Send size={16} strokeWidth={2} />}
              </button>
            </div>
          </div>

          <div className="ab-recent card">
            <h3 className="ab-panel-title">Recent Tests</h3>
            {recentTests.length === 0 ? (
              <p style={{ fontSize: 13, color: "#a1a9b5", padding: "6px 0" }}>No tests run yet.</p>
            ) : (
              <ul className="ab-recent-list">
                {recentTests.map((r, i) => (
                  <li key={i}>
                    <CheckCircle2 size={20} className="ab-check" strokeWidth={2} />
                    <div className="ab-recent-body">
                      <p className="ab-recent-title">{r.title}</p>
                      <div className="ab-recent-meta">
                        <span className="ab-success">{r.ok ? "Success" : "Failed"}</span>
                        <span className="ab-recent-time">{r.time}</span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="ab-footer">
        <div className="ab-footer-left">
          <button className="ab-btn-outline" type="button" onClick={() => { setTools(agent.tools || []); setSubAgents(agent.sub_agents || []); }}>
            <RefreshCw size={17} strokeWidth={2} /> Reset
          </button>
        </div>
        <button className="ab-btn-primary" type="button" onClick={save} disabled={saving || !dirty}>
          {saving ? <Loader2 size={17} strokeWidth={2} className="animate-spin" /> : <Save size={17} strokeWidth={2} />} Save Changes
          <ArrowRight size={17} strokeWidth={2.2} />
        </button>
      </div>

      {/* Tool picker */}
      <Modal open={toolPicker} onClose={() => setToolPicker(false)} title="Select Tools" icon={Search} size="md">
        <div className="neu-inset rounded-xl p-3 max-h-[50vh] overflow-y-auto flex flex-wrap gap-1.5">
          {allTools.map((t) => {
            const on = tools.includes(t.name);
            return (
              <button key={t.name} type="button" onClick={() => toggleTool(t.name)}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11.5px] font-medium ${on ? "neu-nav-active text-[#4f46e5]" : "neu-chip text-[#5b6678]"}`}>
                {on && <CheckCircle2 size={11} />} {t.display_name || t.name}
              </button>
            );
          })}
        </div>
      </Modal>

      {/* Sub-agent picker */}
      <Modal open={subPicker} onClose={() => setSubPicker(false)} title="Select Sub-Agents" icon={Bot} size="md">
        <div className="neu-inset rounded-xl p-3 max-h-[50vh] overflow-y-auto flex flex-wrap gap-1.5">
          {allAgents.filter((a) => a.id !== agent.id).map((a) => {
            const on = subAgents.includes(a.id);
            return (
              <button key={a.id} type="button" onClick={() => toggleSub(a.id)}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11.5px] font-medium ${on ? "neu-nav-active text-[#4f46e5]" : "neu-chip text-[#5b6678]"}`}>
                {on && <CheckCircle2 size={11} />} {a.name}
              </button>
            );
          })}
        </div>
      </Modal>
    </div>
  );
};

export default ViewAgentBuilder;
