// 5.6 Agent Performance — built to match the reference design.
// Renders in the Agents section "Performance" sub-tab. Indigo accents.
// Charts are hand-built SVG (no charting library in this project).
import { useState } from "react";
import {
  ChevronDown,
  CalendarDays,
  Timer,
  LayoutGrid,
  Clock,
  Image as ImageIcon,
  DollarSign,
  Droplet,
  Globe,
  FileText,
  BarChart3,
  MessagesSquare,
  Settings,
  CircleDot,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";

const KPIS = [
  { label: "Success Rate", value: "96%", trend: "+2%", up: true, icon: <Timer size={22} strokeWidth={2} />, tint: "kpi-green" },
  { label: "Total Runs", value: "1,248", trend: "+12%", up: true, icon: <LayoutGrid size={22} strokeWidth={2} />, tint: "kpi-slate" },
  { label: "Avg. Latency", value: "2.4s", trend: "-18%", up: true, icon: <Clock size={22} strokeWidth={2} />, tint: "kpi-amber" },
  { label: "Token Usage", value: "482K", trend: "+9%", up: false, icon: <ImageIcon size={22} strokeWidth={2} />, tint: "kpi-indigo" },
  { label: "Estimated Cost", value: "$12.40", trend: "+5%", up: false, icon: <DollarSign size={22} strokeWidth={2} />, tint: "kpi-orange" },
  { label: "Error Rate", value: "4%", trend: "-2%", up: true, icon: <Droplet size={22} strokeWidth={2} />, tint: "kpi-red" },
];

const TABS = ["Overview", "Runs", "Tool Usage", "Sub-Agents", "Cost Analysis"];

const TOOL_USAGE = [
  { name: "Web Search", pct: 32, icon: <Globe size={18} strokeWidth={2} /> },
  { name: "Notion", pct: 24, icon: <FileText size={18} strokeWidth={2} /> },
  { name: "Analytics", pct: 18, icon: <BarChart3 size={18} strokeWidth={2} /> },
  { name: "Slack", pct: 14, icon: <MessagesSquare size={18} strokeWidth={2} /> },
  { name: "Custom API", pct: 12, icon: <Settings size={18} strokeWidth={2} /> },
];

const SUBAGENTS = [
  { name: "Content Creator", pct: 96 },
  { name: "SEO Analyst", pct: 84 },
  { name: "Campaign Manager", pct: 91 },
  { name: "Trend Researcher", pct: 88 },
];

const RECENT_RUNS = [
  { time: "2 min ago", input: "Social media post", status: "Success", latency: "2.1s", tokens: "1.2K", cost: "$0.03" },
  { time: "8 min ago", input: "Campaign analysis", status: "Success", latency: "2.4s", tokens: "2.8K", cost: "$0.07" },
  { time: "15 min ago", input: "Blog outline", status: "Failed", latency: "1.8s", tokens: "0.5K", cost: "$0.02" },
  { time: "32 min ago", input: "Competitor research", status: "Success", latency: "4.7s", tokens: "3.1K", cost: "$0.06" },
];

const X_LABELS = ["Sep 1", "Sep 8", "Sep 15", "Sep 22", "Sep 30"];

/* ---- Line chart (Success Rate % + Avg Latency) ---- */
const LineChart = () => {
  const W = 480, H = 250, padL = 44, padR = 40, padT = 20, padB = 34;
  const iw = W - padL - padR, ih = H - padT - padB;
  const success = [52, 54, 54, 55, 74, 72, 76, 75, 75];
  const latency = [34, 36, 33, 34, 52, 50, 55, 56, 52]; // as % of axis height
  const n = success.length;
  const xAt = (i) => padL + (iw * i) / (n - 1);
  const yAt = (v) => padT + ih - (ih * v) / 100;
  const path = (arr) => arr.map((v, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(v)}`).join(" ");
  const yTicks = [0, 25, 50, 75, 100];

  return (
    <svg className="perf-linechart" viewBox={`0 0 ${W} ${H}`}>
      {yTicks.map((t) => (
        <g key={t}>
          <line x1={padL} y1={yAt(t)} x2={W - padR} y2={yAt(t)} className="perf-grid" />
          <text x={padL - 8} y={yAt(t) + 4} className="perf-axis" textAnchor="end">{t}%</text>
          <text x={W - padR + 8} y={yAt(t) + 4} className="perf-axis" textAnchor="start">{(8 * t) / 100}s</text>
        </g>
      ))}
      {X_LABELS.map((lb, i) => (
        <text key={lb} x={padL + (iw * i) / (X_LABELS.length - 1)} y={H - 10} className="perf-axis" textAnchor="middle">{lb}</text>
      ))}
      <path d={path(latency)} className="perf-line perf-line-latency" />
      <path d={path(success)} className="perf-line perf-line-success" />
      {success.map((v, i) => <circle key={`s${i}`} cx={xAt(i)} cy={yAt(v)} r="3.5" className="perf-dot-success" />)}
      {latency.map((v, i) => <circle key={`l${i}`} cx={xAt(i)} cy={yAt(v)} r="3.5" className="perf-dot-latency" />)}
    </svg>
  );
};

/* ---- Bar chart (Run Volume) ---- */
const BarChart = () => {
  const W = 480, H = 250, padL = 40, padR = 12, padT = 20, padB = 34;
  const iw = W - padL - padR, ih = H - padT - padB;
  const bars = [88, 60, 92, 118, 95, 118, 162, 130, 120, 130, 88, 86, 122, 148, 168, 140];
  const max = 200;
  const bw = (iw / bars.length) * 0.6;
  const gap = (iw / bars.length) * 0.4;
  const yTicks = [0, 50, 100, 150, 200];

  return (
    <svg className="perf-barchart" viewBox={`0 0 ${W} ${H}`}>
      {yTicks.map((t) => (
        <g key={t}>
          <line x1={padL} y1={padT + ih - (ih * t) / max} x2={W - padR} y2={padT + ih - (ih * t) / max} className="perf-grid" />
          <text x={padL - 8} y={padT + ih - (ih * t) / max + 4} className="perf-axis" textAnchor="end">{t}</text>
        </g>
      ))}
      {bars.map((v, i) => {
        const x = padL + i * (bw + gap) + gap / 2;
        const h = (ih * v) / max;
        return <rect key={i} x={x} y={padT + ih - h} width={bw} height={h} rx="3" className="perf-bar" />;
      })}
      {X_LABELS.map((lb, i) => (
        <text key={lb} x={padL + (iw * i) / (X_LABELS.length - 1)} y={H - 10} className="perf-axis" textAnchor="middle">{lb}</text>
      ))}
    </svg>
  );
};

export const ViewAgentPerformance = () => {
  const [tab, setTab] = useState("Overview");

  return (
    <div className="agent-performance">
      {/* Header */}
      <div className="perf-head">
        <button className="perf-agent">
          Marketing Agent <ChevronDown size={20} strokeWidth={2} />
        </button>
        <button className="perf-range">
          <CalendarDays size={17} strokeWidth={2} /> Last 30 days
          <ChevronDown size={17} strokeWidth={2} className="perf-range-caret" />
        </button>
      </div>

      {/* KPI cards */}
      <div className="perf-kpis">
        {KPIS.map((k) => (
          <div key={k.label} className="perf-kpi card">
            <div className={`perf-kpi-icon ${k.tint}`}>{k.icon}</div>
            <div className="perf-kpi-body">
              <span className="perf-kpi-label">{k.label}</span>
              <div className="perf-kpi-valrow">
                <span className="perf-kpi-value">{k.value}</span>
                <span className={`perf-kpi-trend ${k.up ? "up" : "down"}`}>{k.trend}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="perf-tabs">
        {TABS.map((t) => (
          <button key={t} className={`perf-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Charts */}
      <div className="perf-charts">
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Success Rate &amp; Latency</h3>
          <div className="perf-legend">
            <span><i className="perf-leg-dot perf-leg-success" /> Success Rate (%)</span>
            <span><i className="perf-leg-dot perf-leg-latency" /> Avg. Latency (s)</span>
          </div>
          <LineChart />
        </div>
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Run Volume</h3>
          <BarChart />
        </div>
      </div>

      {/* Tool Usage + Sub-Agent Performance */}
      <div className="perf-mid">
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Tool Usage</h3>
          <ul className="perf-bars">
            {TOOL_USAGE.map((t) => (
              <li key={t.name}>
                <span className="perf-bar-icon">{t.icon}</span>
                <span className="perf-bar-name">{t.name}</span>
                <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: `${t.pct * 2.6}%` }} /></span>
                <span className="perf-bar-pct">{t.pct}%</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Sub-Agent Performance</h3>
          <ul className="perf-bars">
            {SUBAGENTS.map((s) => (
              <li key={s.name}>
                <span className="perf-bar-icon perf-bar-icon-dark"><CircleDot size={16} strokeWidth={2} /></span>
                <span className="perf-bar-name">{s.name}</span>
                <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: `${s.pct}%` }} /></span>
                <span className="perf-bar-pct">{s.pct}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="perf-panel card perf-recent">
        <h3 className="perf-panel-title">Recent Runs</h3>
        <table className="perf-table">
          <thead>
            <tr>
              <th>Time</th><th>Input</th><th>Status</th><th>Latency</th><th>Tokens</th><th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {RECENT_RUNS.map((r, i) => (
              <tr key={i}>
                <td className="perf-td-time">{r.time}</td>
                <td className="perf-td-input">{r.input}</td>
                <td>
                  <span className={`perf-status ${r.status === "Success" ? "ok" : "fail"}`}>
                    {r.status === "Success" ? <CheckCircle2 size={15} strokeWidth={2.2} /> : <AlertCircle size={15} strokeWidth={2.2} />}
                    {r.status}
                  </span>
                </td>
                <td>{r.latency}</td>
                <td>{r.tokens}</td>
                <td>{r.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="perf-viewall">
          View all runs <ArrowRight size={16} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
};
