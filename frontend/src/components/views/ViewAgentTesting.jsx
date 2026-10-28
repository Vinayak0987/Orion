// Agent Testing — mock layout (agent-testing) wired to the real backend.
// Three columns: Test Cases (local history), Execution Trace (real steps from
// agentApi.test), and Test Results (real output rendered as Markdown).
import { useEffect, useState } from "react";
import {
  Copy,
  Save,
  ChevronDown,
  Plus,
  FileText,
  Send,
  Bot,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Markdown } from "../ui/Markdown.jsx";

const stepTitle = (s) => {
  if (s.type === "tool") return `Tool Call (${s.tool_name || "tool"})`;
  if (s.type === "llm") return `LLM (${s.provider || ""} ${s.model || ""})`.trim();
  return s.type ? s.type[0].toUpperCase() + s.type.slice(1) : "Step";
};

export const ViewAgentTesting = ({ presetAgentId }) => {
  const toast = useToast();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);

  const [msg, setMsg] = useState("");
  const [testing, setTesting] = useState(false);
  const [cases, setCases] = useState([]); // local test history
  const [activeIdx, setActiveIdx] = useState(0);
  const [resultTab, setResultTab] = useState("Output");

  useEffect(() => {
    if (!presetAgentId) {
      setLoading(false);
      return;
    }
    agentApi
      .get(presetAgentId)
      .then(setAgent)
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetAgentId]);

  const active = cases[activeIdx] || null;

  const runTest = async () => {
    if (!agent) {
      toast.error("No agent selected — open one from the Overview.");
      return;
    }
    if (!msg.trim()) return;
    setTesting(true);
    const text = msg;
    try {
      const r = await agentApi.test(agent.id, text);
      const entry = {
        label: text,
        ok: r.ok,
        output: r.output,
        trace: r.trace || [],
        events: r.events || [],
      };
      setCases((prev) => [entry, ...prev]);
      setActiveIdx(0);
      setMsg("");
      setResultTab("Output");
      toast[r.ok ? "success" : "error"](r.ok ? "Test completed" : "Test failed");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTesting(false);
    }
  };

  const copyOutput = () => {
    if (active?.output) {
      navigator.clipboard?.writeText(typeof active.output === "string" ? active.output : JSON.stringify(active.output, null, 2));
      toast.info("Copied output");
    }
  };

  if (loading) {
    return (
      <div className="agent-testing">
        <div style={{ display: "grid", placeItems: "center", padding: "80px 0", color: "#a1a9b5" }}>
          <Loader2 className="animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="agent-testing">
      {/* Header */}
      <div className="at-head">
        <div>
          <h1>Agent Testing</h1>
          <p>Test your agent on sample inputs and validate its behavior.</p>
        </div>
        <div className="at-head-actions">
          <button className="at-btn-outline" onClick={copyOutput}>
            <Copy size={17} strokeWidth={2} /> Copy Output
          </button>
          <button className="at-btn-outline" disabled>
            <Save size={17} strokeWidth={2} /> Save Test Case
          </button>
        </div>
      </div>

      {/* Agent selector */}
      <div className="at-selects">
        <button className="at-select at-select-agent">
          <span className="at-agent-icon"><Bot size={17} strokeWidth={2} /></span>
          <span className="at-agent-label">
            {agent ? agent.name : "No agent selected"}{" "}
            {agent && <span className="at-agent-ver">({agent.version || "v1.0.0"})</span>}
          </span>
          <ChevronDown size={18} strokeWidth={2} className="at-select-caret" />
        </button>
        <button className="at-select at-select-env">
          Isolated run
          <ChevronDown size={18} strokeWidth={2} className="at-select-caret" />
        </button>
      </div>

      {/* Three columns */}
      <div className="at-columns">
        {/* Test Cases (history) */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Test Cases</h2>
            <button className="at-newtest" onClick={() => { setMsg(""); }}>
              <Plus size={17} strokeWidth={2.4} /> New Test
            </button>
          </div>
          <ul className="at-cases">
            {cases.length === 0 && (
              <li style={{ fontSize: 13, color: "#a1a9b5", padding: "8px 4px" }}>No tests yet. Run one below.</li>
            )}
            {cases.map((c, i) => (
              <li key={i}>
                <button className={`at-case ${activeIdx === i ? "active" : ""}`} onClick={() => setActiveIdx(i)}>
                  <span className="at-case-icon"><FileText size={16} strokeWidth={2} /></span>
                  <span className="at-case-label">{c.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Execution Trace */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Execution Trace</h2>
          </div>
          {testing ? (
            <div style={{ display: "grid", placeItems: "center", padding: 24, color: "#a1a9b5" }}>
              <Loader2 className="animate-spin" />
            </div>
          ) : !active ? (
            <p style={{ fontSize: 13, color: "#a1a9b5", padding: "8px 4px" }}>Run a test to see the trace.</p>
          ) : (
            <ul className="at-trace">
              {active.trace.map((step, i) => (
                <li
                  key={i}
                  className={`at-step ${step.success ? "done" : ""} ${i === active.trace.length - 1 ? "last" : ""}`}
                >
                  <span className="at-step-dot" />
                  <div className="at-step-body">
                    <div className="at-step-titlerow">
                      <span className="at-step-title">{stepTitle(step)}</span>
                      <span className="at-step-time">{step.latency_ms != null ? `${step.latency_ms}ms` : ""}</span>
                    </div>
                    <p className="at-step-desc">
                      {step.success ? "Completed" : (step.error || "Failed")}
                    </p>
                  </div>
                </li>
              ))}
              {active.trace.length === 0 && (
                <li style={{ fontSize: 13, color: "#a1a9b5" }}>No trace steps recorded.</li>
              )}
            </ul>
          )}
        </div>

        {/* Test Results */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Test Results</h2>
          </div>
          <div className="at-result-tabs">
            {["Output", "Logs"].map((t) => (
              <button key={t} className={`at-result-tab ${resultTab === t ? "active" : ""}`} onClick={() => setResultTab(t)}>
                {t}
              </button>
            ))}
          </div>
          {!active ? (
            <p className="at-result-intro">Results will appear here after a test run.</p>
          ) : resultTab === "Output" ? (
            <div className="at-result-card">
              <button className="at-result-copy" aria-label="Copy" onClick={copyOutput}><Copy size={16} strokeWidth={2} /></button>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 600, color: active.ok ? "#16a34a" : "#dc2626", marginBottom: 8 }}>
                {active.ok ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
                {active.ok ? "Success" : "Failed"}
              </span>
              <Markdown compact>
                {typeof active.output === "string"
                  ? active.output
                  : active.output != null
                  ? "```json\n" + JSON.stringify(active.output, null, 2) + "\n```"
                  : "_No output returned._"}
              </Markdown>
            </div>
          ) : (
            <div className="at-result-card">
              <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: 0 }}>
                {JSON.stringify(active.events, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="at-composer">
        <input
          placeholder="Type a test message..."
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runTest(); } }}
        />
        <button className="at-send" aria-label="Send" onClick={runTest} disabled={testing || !msg.trim()}>
          {testing ? <Loader2 size={20} strokeWidth={2} className="animate-spin" /> : <Send size={20} strokeWidth={2} />}
        </button>
      </div>
    </div>
  );
};

export default ViewAgentTesting;
