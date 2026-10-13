// 5.5 Agent Testing — built to match the reference design.
// Renders in the Agents section "Testing" sub-tab. Indigo accents.
import { useState } from "react";
import {
  Copy,
  Save,
  ChevronDown,
  Plus,
  FileText,
  Send,
  Bot,
} from "lucide-react";

const TEST_CASES = [
  "Social media post generation",
  "Campaign analysis",
  "Blog outline creation",
  "Competitor research",
  "Audience analysis",
  "A/B test suggestions",
];

const TRACE = [
  { title: "Input received", desc: "Processing your request...", time: "0.8s" },
  { title: "Planning", desc: "Analyzing requirements...", time: "2.1s" },
  { title: "Tool Call (Web Search)", desc: "Searching for latest trends...", time: "3.4s" },
  { title: "Tool Call (Notion)", desc: "Storing research data...", time: "1.2s" },
  { title: "Generating response", desc: "Creating content...", time: "4.6s" },
  { title: "Completed", desc: "Response generated successfully.", time: "0.3s", done: true },
];

export const ViewAgentTesting = () => {
  const [activeCase, setActiveCase] = useState("Social media post generation");
  const [resultTab, setResultTab] = useState("Output");

  return (
    <div className="agent-testing">
      {/* Header */}
      <div className="at-head">
        <div>
          <h1>Agent Testing</h1>
          <p>Test your domain sample inputs and validate its behavior.</p>
        </div>
        <div className="at-head-actions">
          <button className="at-btn-outline">
            <Copy size={17} strokeWidth={2} /> Compare Runs
          </button>
          <button className="at-btn-outline">
            <Save size={17} strokeWidth={2} /> Save Test Case
          </button>
        </div>
      </div>

      {/* Dropdowns */}
      <div className="at-selects">
        <button className="at-select at-select-agent">
          <span className="at-agent-icon"><Bot size={17} strokeWidth={2} /></span>
          <span className="at-agent-label">Marketing Agent <span className="at-agent-ver">(v1.2.0)</span></span>
          <ChevronDown size={18} strokeWidth={2} className="at-select-caret" />
        </button>
        <button className="at-select at-select-env">
          Development
          <ChevronDown size={18} strokeWidth={2} className="at-select-caret" />
        </button>
      </div>

      {/* Three columns */}
      <div className="at-columns">
        {/* Test Cases */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Test Cases</h2>
            <button className="at-newtest">
              <Plus size={17} strokeWidth={2.4} /> New Test
            </button>
          </div>
          <ul className="at-cases">
            {TEST_CASES.map((c) => {
              const active = activeCase === c;
              return (
                <li key={c}>
                  <button
                    className={`at-case ${active ? "active" : ""}`}
                    onClick={() => setActiveCase(c)}
                  >
                    <span className="at-case-icon"><FileText size={16} strokeWidth={2} /></span>
                    <span className="at-case-label">{c}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Execution Trace */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Execution Trace</h2>
          </div>
          <ul className="at-trace">
            {TRACE.map((step, i) => (
              <li key={step.title} className={`at-step ${step.done ? "done" : ""} ${i === TRACE.length - 1 ? "last" : ""}`}>
                <span className="at-step-dot" />
                <div className="at-step-body">
                  <div className="at-step-titlerow">
                    <span className="at-step-title">{step.title}</span>
                    <span className="at-step-time">{step.time}</span>
                  </div>
                  <p className="at-step-desc">{step.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Test Results */}
        <div className="at-col card">
          <div className="at-col-head">
            <h2>Test Results</h2>
          </div>
          <div className="at-result-tabs">
            {["Output", "Logs"].map((t) => (
              <button
                key={t}
                className={`at-result-tab ${resultTab === t ? "active" : ""}`}
                onClick={() => setResultTab(t)}
              >
                {t}
              </button>
            ))}
          </div>
          <p className="at-result-intro">
            Here's a social media post about our new AI product launch:
          </p>
          <div className="at-result-card">
            <button className="at-result-copy" aria-label="Copy"><Copy size={16} strokeWidth={2} /></button>
            <p className="at-result-lead">📢 Exciting news!<br />Our latest AI product is here!</p>
            <p>Transform your business with intelligent automation…</p>
            <p>#AI #Innovation #Tech</p>
            <p>What features would you like me to highlight?</p>
          </div>
        </div>
      </div>

      {/* Composer */}
      <div className="at-composer">
        <input placeholder="Type a test message..." />
        <button className="at-send" aria-label="Send">
          <Send size={20} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
};
