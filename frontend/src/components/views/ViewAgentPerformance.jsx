// Agent Performance — mock layout (agent-performance) wired to the real backend.
// KPI cards, SVG charts, Tool Usage, and Recent Runs all come from
// agentApi.performance(id). Charts are hand-built SVG (no charting library).
import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  CalendarDays,
  Timer,
  LayoutGrid,
  Clock,
  Image as ImageIcon,
  DollarSign,
  Droplet,
  Wrench,
  CircleDot,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";

const TABS = ["Overview", "Runs", "Tool Usage", "Cost Analysis"];

const pct = (v) => (v != null ? `${Math.round(v * 100)}%` : "—");
const relTime = (iso) => {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

/* ---- Bar chart (Tool usage distribution → run volume stand-in) ---- */
const BarChart = ({ values }) => {
  const W = 480, H = 250, padL = 40, padR = 12, padT = 20, padB = 34;
  const iw = W - padL - padR, ih = H - padT - padB;
  const bars = values.length ? values : [0];
  const max = Math.max(...bars, 1);
  const bw = (iw / bars.length) * 0.6;
  const gap = (iw / bars.length) * 0.4;
  const step = max / 4;
  const yTicks = [0, 1, 2, 3, 4].map((i) => Math.round(step * i));

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
    </svg>
  );
};

export const ViewAgentPerformance = ({ presetAgentId }) => {
  const toast = useToast();
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("Overview");

  useEffect(() => {
    if (!presetAgentId) {
      setLoading(false);
      return;
    }
    agentApi
      .performance(presetAgentId)
      .then(setPerf)
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetAgentId]);

  const kpis = useMemo(() => {
    if (!perf) return [];
    return [
      { label: "Success Rate", value: pct(perf.success_rate), icon: <Timer size={22} strokeWidth={2} />, tint: "kpi-green" },
      { label: "Total Runs", value: (perf.runs || 0).toLocaleString(), icon: <LayoutGrid size={22} strokeWidth={2} />, tint: "kpi-slate" },
      { label: "Avg. Latency", value: perf.avg_latency_ms != null ? `${(perf.avg_latency_ms / 1000).toFixed(2)}s` : "—", icon: <Clock size={22} strokeWidth={2} />, tint: "kpi-amber" },
      { label: "Token Usage", value: (perf.total_tokens || 0).toLocaleString(), icon: <ImageIcon size={22} strokeWidth={2} />, tint: "kpi-indigo" },
      { label: "Estimated Cost", value: `$${(perf.estimated_cost_usd || 0).toFixed(2)}`, icon: <DollarSign size={22} strokeWidth={2} />, tint: "kpi-orange" },
      { label: "Error Rate", value: pct(perf.error_rate), icon: <Droplet size={22} strokeWidth={2} />, tint: "kpi-red" },
    ];
  }, [perf]);

  const toolUsage = perf?.tool_usage || [];
  const maxTool = Math.max(...toolUsage.map((t) => t.count), 1);
  const recentRuns = perf?.recent_runs || [];

  if (loading) {
    return (
      <div className="agent-performance">
        <div style={{ display: "grid", placeItems: "center", padding: "80px 0", color: "#a1a9b5" }}>
          <Loader2 className="animate-spin" />
        </div>
      </div>
    );
  }

  if (!perf) {
    return (
      <div className="agent-performance">
        <div className="perf-panel card" style={{ textAlign: "center", padding: 40, color: "#a1a9b5" }}>
          No agent selected. Open an agent from the Overview to see its performance.
        </div>
      </div>
    );
  }

  return (
    <div className="agent-performance">
      {/* Header */}
      <div className="perf-head">
        <button className="perf-agent">
          {perf.agent?.name || "Agent"} <ChevronDown size={20} strokeWidth={2} />
        </button>
        <button className="perf-range">
          <CalendarDays size={17} strokeWidth={2} /> All time
          <ChevronDown size={17} strokeWidth={2} className="perf-range-caret" />
        </button>
      </div>

      {/* KPI cards */}
      <div className="perf-kpis">
        {kpis.map((k) => (
          <div key={k.label} className="perf-kpi card">
            <div className={`perf-kpi-icon ${k.tint}`}>{k.icon}</div>
            <div className="perf-kpi-body">
              <span className="perf-kpi-label">{k.label}</span>
              <div className="perf-kpi-valrow">
                <span className="perf-kpi-value">{k.value}</span>
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
          <h3 className="perf-panel-title">Tool Call Volume</h3>
          <div className="perf-legend">
            <span><i className="perf-leg-dot perf-leg-success" /> Calls per tool</span>
          </div>
          <BarChart values={toolUsage.map((t) => t.count)} />
        </div>
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Run Outcomes</h3>
          <div className="perf-legend">
            <span><i className="perf-leg-dot perf-leg-success" /> Success rate {pct(perf.success_rate)}</span>
            <span><i className="perf-leg-dot perf-leg-latency" /> Error rate {pct(perf.error_rate)}</span>
          </div>
          <BarChart values={[perf.trace_count - (perf.error_count || 0), perf.error_count || 0]} />
        </div>
      </div>

      {/* Tool Usage + Sub-Agent/Trace breakdown */}
      <div className="perf-mid">
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Tool Usage</h3>
          {toolUsage.length === 0 ? (
            <p style={{ fontSize: 13, color: "#a1a9b5", padding: "6px 0" }}>No tool calls recorded.</p>
          ) : (
            <ul className="perf-bars">
              {toolUsage.map((t) => (
                <li key={t.tool}>
                  <span className="perf-bar-icon"><Wrench size={18} strokeWidth={2} /></span>
                  <span className="perf-bar-name">{t.tool}</span>
                  <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: `${(t.count / maxTool) * 100}%` }} /></span>
                  <span className="perf-bar-pct">{t.count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="perf-panel card">
          <h3 className="perf-panel-title">Execution Summary</h3>
          <ul className="perf-bars">
            <li>
              <span className="perf-bar-icon perf-bar-icon-dark"><CircleDot size={16} strokeWidth={2} /></span>
              <span className="perf-bar-name">Total trace steps</span>
              <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: "100%" }} /></span>
              <span className="perf-bar-pct">{perf.trace_count || 0}</span>
            </li>
            <li>
              <span className="perf-bar-icon perf-bar-icon-dark"><CircleDot size={16} strokeWidth={2} /></span>
              <span className="perf-bar-name">Successful steps</span>
              <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: `${perf.trace_count ? ((perf.trace_count - (perf.error_count || 0)) / perf.trace_count) * 100 : 0}%` }} /></span>
              <span className="perf-bar-pct">{(perf.trace_count || 0) - (perf.error_count || 0)}</span>
            </li>
            <li>
              <span className="perf-bar-icon perf-bar-icon-dark"><CircleDot size={16} strokeWidth={2} /></span>
              <span className="perf-bar-name">Errors</span>
              <span className="perf-bar-track"><span className="perf-bar-fill" style={{ width: `${perf.trace_count ? ((perf.error_count || 0) / perf.trace_count) * 100 : 0}%` }} /></span>
              <span className="perf-bar-pct">{perf.error_count || 0}</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="perf-panel card perf-recent">
        <h3 className="perf-panel-title">Recent Runs</h3>
        <table className="perf-table">
          <thead>
            <tr>
              <th>Time</th><th>Type</th><th>Status</th><th>Latency</th><th>Tool</th><th>Model</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "#a1a9b5" }}>No runs recorded yet.</td></tr>
            ) : (
              recentRuns.map((r, i) => (
                <tr key={i}>
                  <td className="perf-td-time">{relTime(r.created_at)}</td>
                  <td className="perf-td-input">{r.trace_type}</td>
                  <td>
                    <span className={`perf-status ${r.success ? "ok" : "fail"}`}>
                      {r.success ? <CheckCircle2 size={15} strokeWidth={2.2} /> : <AlertCircle size={15} strokeWidth={2.2} />}
                      {r.success ? "Success" : "Failed"}
                    </span>
                  </td>
                  <td>{r.latency_ms != null ? `${r.latency_ms}ms` : "—"}</td>
                  <td>{r.tool_name || "—"}</td>
                  <td>{r.model || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <button className="perf-viewall">
          View all runs <ArrowRight size={16} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
};

export default ViewAgentPerformance;
