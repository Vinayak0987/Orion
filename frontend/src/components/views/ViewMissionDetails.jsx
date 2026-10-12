import {
  Rocket,
  ChevronDown,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Crosshair,
  Settings,
  FileText,
  Boxes,
  ClipboardList,
  CircleCheck,
  CircleDot,
  Clock,
  CircleX,
  Globe,
  UsersRound,
  Bug,
  ArrowRight,
} from "lucide-react";

const TABS = ["Overview", "Tasks", "Agents", "Tools", "Evidence", "Results", "Trace"];

// Leaf status styles
const STATUS = {
  Completed: { pill: "text-emerald-600 bg-emerald-50", Icon: CircleCheck, color: "text-emerald-500" },
  "In Progress": { pill: "text-blue-600 bg-blue-50", Icon: CircleDot, color: "text-blue-500" },
  Pending: { pill: "text-amber-600 bg-amber-50", Icon: Clock, color: "text-amber-500" },
};

// Three branches: agent node + its leaf tasks + the branch (edge) color.
const BRANCHES = [
  {
    name: "Market Research",
    tasks: "3 tasks",
    LucideIcon: FileText,
    tint: "text-emerald-600 bg-emerald-50",
    edge: "#22c55e",
    leaves: [
      { name: "Location Analysis", status: "Completed" },
      { name: "Competitor Study", status: "In Progress", active: true },
      { name: "Customer Insights", status: "Pending" },
    ],
  },
  {
    name: "Financial Analysis",
    tasks: "3 tasks",
    LucideIcon: Boxes,
    tint: "text-blue-600 bg-blue-50",
    edge: "#4f46e5",
    leaves: [
      { name: "Rental Cost Analysis", status: "Completed" },
      { name: "Pricing Strategy", status: "In Progress" },
      { name: "Revenue Modeling", status: "Pending" },
    ],
  },
  {
    name: "Execution Planning",
    tasks: "4 tasks",
    LucideIcon: ClipboardList,
    tint: "text-violet-600 bg-violet-50",
    edge: "#a78bfa",
    leaves: [
      { name: "Legal Requirements", status: "Pending" },
      { name: "Operations Setup", status: "Pending" },
      { name: "Launch Timeline", status: "Pending" },
    ],
  },
];

const TIMELINE_LEGEND = [
  { label: "Completed", Icon: CircleCheck, color: "text-emerald-500" },
  { label: "In Progress", Icon: CircleDot, color: "text-blue-500" },
  { label: "Waiting", Icon: Clock, color: "text-amber-500" },
  { label: "Failed", Icon: CircleX, color: "text-rose-500" },
];

const TOOLS_USED = [
  { name: "Web Search", LucideIcon: Globe, color: "text-emerald-600 bg-emerald-50" },
  { name: "Most API", LucideIcon: UsersRound, color: "text-violet-600 bg-violet-50" },
  { name: "Review Scraper", LucideIcon: Bug, color: "text-orange-500 bg-orange-50" },
];

const OUTPUT = [
  "Found 10 major competitors",
  "Average price range: ₹120 – ₹250",
  "Top 3 locations identified",
];

const LeafCard = ({ leaf }) => {
  const s = STATUS[leaf.status];
  return (
    <div
      className={`flex items-center gap-2.5 bg-white rounded-xl px-3 py-2.5 border shadow-sm ${
        leaf.active ? "border-[#a5b4fc] ring-2 ring-[#eef2ff]" : "border-[#e6ebf2]"
      }`}
    >
      <s.Icon size={18} className={s.color} strokeWidth={2.2} />
      <div className="min-w-0">
        <p className="text-[13px] font-bold text-slate-800 leading-tight truncate">{leaf.name}</p>
        <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded ${s.pill}`}>{leaf.status}</span>
      </div>
    </div>
  );
};

// ---- Coordinate-based Execution Graph with curved SVG connectors ----
// Virtual canvas. Positions are top-left of each node box.
const GEO = {
  W: 700,
  H: 624,
  // orchestrator circle (moved a little left)
  orchCx: 58,
  orchCy: 268,
  orchR: 46,
  agentX: 190,
  agentW: 210,
  agentH: 62,
  agentY: [104, 268, 432], // top-y of each agent node → centers 135/299/463
  leafX: 476,
  leafW: 205,
  leafH: 56,
  // top-y of each leaf row (9 rows grouped 3/3/3); centers align around each agent center
  leafY: [46, 110, 174, 240, 304, 368, 434, 498, 562],
};

// Cubic bezier between two points with horizontal control handles.
const curve = (x1, y1, x2, y2) => {
  const dx = Math.max(45, (x2 - x1) * 0.55);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
};

const ExecutionGraph = () => {
  const G = GEO;

  let leafIndex = 0;

  return (
    <div className="w-full h-full overflow-auto p-4 bg-[radial-gradient(circle,#eaeef7_1px,transparent_1px)] [background-size:16px_16px]">
      <div className="relative mx-auto" style={{ width: G.W, height: G.H }}>
        {/* SVG connectors underlay */}
        <svg className="absolute inset-0 pointer-events-none" width={G.W} height={G.H} viewBox={`0 0 ${G.W} ${G.H}`}>
          <defs>
            {BRANCHES.map((b, bi) => (
              <marker key={bi} id={`arrow-${bi}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9" fill="none" stroke={b.edge} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </marker>
            ))}
          </defs>

          {/* dotted orbit ring around orchestrator */}
          <circle cx={G.orchCx} cy={G.orchCy} r={G.orchR + 12} fill="none" stroke="#c7d2fe" strokeWidth="1.5" strokeDasharray="2 6" strokeLinecap="round" />

          {BRANCHES.map((b, bi) => {
            const ay = G.agentY[bi];
            const agentLeftX = G.agentX;
            const agentRightX = G.agentX + G.agentW;
            const agentCy = ay + G.agentH / 2;
            const paths = [];
            // Orchestrator (right edge of circle) -> agent left-center, with arrowhead
            paths.push(
              <path key={`o-${bi}`} d={curve(G.orchCx + G.orchR + 12, G.orchCy, agentLeftX - 6, agentCy)} stroke={b.edge} strokeWidth="2.5" fill="none" markerEnd={`url(#arrow-${bi})`} />
            );
            // agent right-center -> each leaf left-center, with arrowhead
            b.leaves.forEach((_, li) => {
              const ly = G.leafY[leafIndex] + G.leafH / 2;
              paths.push(
                <path key={`l-${bi}-${li}`} d={curve(agentRightX, agentCy, G.leafX - 6, ly)} stroke={b.edge} strokeWidth="2.5" fill="none" opacity="0.9" markerEnd={`url(#arrow-${bi})`} />
              );
              leafIndex++;
            });
            return <g key={bi}>{paths}</g>;
          })}
        </svg>

        {/* Orchestrator */}
        <div className="absolute flex flex-col items-center" style={{ left: G.orchCx - 66, top: G.orchCy - G.orchR - 2, width: 132 }}>
          <div
            className="rounded-full bg-gradient-to-br from-[#6366f1] via-[#4f46e5] to-[#312e81] text-white flex flex-col items-center justify-center shadow-[0_4px_12px_rgba(79,70,229,0.28)] ring-4 ring-[#eef2ff]"
            style={{ width: G.orchR * 2, height: G.orchR * 2 }}
          >
            <Settings size={22} strokeWidth={2} />
            <span className="text-[11px] font-semibold mt-0.5">Orchestrator</span>
          </div>
          <div className="mt-2 bg-white/70 rounded-xl px-3 py-1.5 text-center">
            <p className="text-sm font-bold text-slate-800 leading-tight">Orion Planner</p>
            <p className="text-[11px] text-slate-400">Coordinator</p>
          </div>
        </div>

        {/* Agent nodes */}
        {BRANCHES.map((b, bi) => (
          <div
            key={bi}
            className="absolute flex items-center gap-2.5 bg-white rounded-2xl px-3.5 py-2.5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]"
            style={{ left: G.agentX, top: G.agentY[bi], width: G.agentW, height: G.agentH }}
          >
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${b.tint}`}>
              <b.LucideIcon size={18} strokeWidth={2} />
            </div>
            <div className="min-w-0">
              <h5 className="text-sm font-bold text-slate-800 leading-tight truncate">{b.name}</h5>
              <p className="text-xs text-slate-400">{b.tasks}</p>
            </div>
          </div>
        ))}

        {/* Leaf nodes */}
        {BRANCHES.flatMap((b) => b.leaves).map((leaf, i) => (
          <div key={i} className="absolute" style={{ left: GEO.leafX, top: GEO.leafY[i], width: GEO.leafW }}>
            <LeafCard leaf={leaf} />
          </div>
        ))}
      </div>
    </div>
  );
};

export const ViewMissionDetails = () => (
  <div className="h-full flex flex-col p-6 sm:p-7 max-w-[1400px] mx-auto min-h-0 bg-[#f8fafc]">
    {/* Header */}
    <div className="flex justify-between items-center mb-5 shrink-0">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-violet-100 flex items-center justify-center text-violet-600 shrink-0">
          <Rocket size={24} strokeWidth={2} />
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Expand to New City (Thane)</h1>
            <span className="px-3 py-1 rounded-full text-xs font-semibold text-blue-600 bg-blue-100">In Progress</span>
          </div>
          <p className="text-slate-500 mt-1">Research market and create go-to-market plan for Thane cafe.</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {/* Progress ring */}
        <div className="relative w-14 h-14 flex items-center justify-center">
          <svg className="w-full h-full -rotate-90">
            <circle cx="28" cy="28" r="24" stroke="#E2E8F0" strokeWidth="5" fill="none" />
            <circle cx="28" cy="28" r="24" stroke="#4F46E5" strokeWidth="5" fill="none" strokeDasharray={2 * Math.PI * 24} strokeDashoffset={2 * Math.PI * 24 * (1 - 0.7)} strokeLinecap="round" />
          </svg>
          <span className="absolute text-sm font-bold text-slate-800">70%</span>
        </div>
        <button className="bg-white border border-[#e6ebf2] text-slate-700 font-semibold py-2.5 px-4 rounded-xl text-sm shadow-sm flex items-center gap-2 hover:bg-slate-50">
          Actions <ChevronDown size={16} className="text-slate-400" />
        </button>
      </div>
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-2 mb-5 shrink-0 overflow-x-auto scrollbar-hide">
      {TABS.map((tab, i) => (
        <button key={i} className={`px-5 py-2.5 rounded-xl text-sm font-semibold whitespace-nowrap transition-colors ${i === 0 ? "bg-white border border-[#e6ebf2] text-slate-800 shadow-sm" : "text-slate-500 hover:bg-slate-100"}`}>
          {tab}
        </button>
      ))}
    </div>

    {/* Main Content */}
    <div className="flex-1 flex gap-6 min-h-0">
      {/* Execution Graph */}
      <div className="flex-[2] flex flex-col bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] overflow-hidden">
        <div className="p-4 flex justify-between items-center border-b border-slate-100">
          <div className="flex items-center gap-3">
            <h3 className="font-bold text-slate-800">Execution Graph (Live)</h3>
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animated-pulse"></span> Live
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button className="w-8 h-8 rounded-lg border border-[#e6ebf2] hover:bg-slate-50 flex items-center justify-center text-slate-500"><ZoomIn size={15} /></button>
            <button className="w-8 h-8 rounded-lg border border-[#e6ebf2] hover:bg-slate-50 flex items-center justify-center text-slate-500"><ZoomOut size={15} /></button>
            <button className="w-8 h-8 rounded-lg border border-[#e6ebf2] hover:bg-slate-50 flex items-center justify-center text-slate-500"><Maximize2 size={14} /></button>
            <button className="w-8 h-8 rounded-lg border border-[#e6ebf2] hover:bg-slate-50 flex items-center justify-center text-slate-500"><Crosshair size={15} /></button>
            <button className="w-8 h-8 rounded-lg border border-[#e6ebf2] hover:bg-slate-50 flex items-center justify-center text-slate-500"><ChevronDown size={15} /></button>
          </div>
        </div>

        {/* Graph body: Orchestrator -> Agents -> Leaves (curved connectors) */}
        <div className="flex-1 min-h-0">
          <ExecutionGraph />
        </div>

        {/* Timeline legend */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex justify-between items-center mb-3">
            <h4 className="text-sm font-bold text-slate-800">Execution Timeline</h4>
            <a href="#" className="text-xs font-semibold text-[#4f46e5] hover:text-[#4338ca] flex items-center gap-1">View all <ArrowRight size={12} /></a>
          </div>
          <div className="flex items-center gap-5 text-xs font-medium text-slate-600">
            {TIMELINE_LEGEND.map((t, i) => (
              <span key={i} className="flex items-center gap-1.5"><t.Icon size={15} className={t.color} strokeWidth={2.2} /> {t.label}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Task Details */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-6 overflow-y-auto w-[380px] shrink-0 scrollbar-hide">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-slate-900">Task Details</h2>
          <span className="px-3 py-1 rounded-full text-xs font-semibold text-blue-600 bg-blue-100">In Progress</span>
        </div>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-11 h-11 rounded-xl bg-violet-100 text-violet-600 flex items-center justify-center shrink-0">
            <UsersRound size={20} strokeWidth={2} />
          </div>
          <div>
            <h4 className="text-base font-bold text-slate-800">Competitor Study</h4>
            <p className="text-xs text-slate-500">Research (Agent)</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Started 10:24 AM · 68% complete</p>
          </div>
        </div>

        <section className="mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-1.5">Description</h4>
          <p className="text-sm text-slate-500 leading-relaxed">Analyze top cafes in Thane (pricing, menu, footfall, reviews).</p>
        </section>

        <section className="mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-2">Tools Used</h4>
          <div className="flex flex-wrap gap-2">
            {TOOLS_USED.map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-50 text-xs font-medium text-slate-600">
                <span className={`w-5 h-5 rounded-md grid place-items-center ${t.color}`}><t.LucideIcon size={12} strokeWidth={2} /></span>
                {t.name}
              </div>
            ))}
          </div>
        </section>

        <section className="mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-2">Evidence</h4>
          <p className="text-xs text-slate-400 mb-2">12 documents · 3 datasets</p>
          <div className="flex gap-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="w-full aspect-square rounded-lg bg-slate-100 border border-[#e6ebf2]"></div>
            ))}
          </div>
        </section>

        <section className="mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-2">Current Output</h4>
          <ul className="space-y-1.5">
            {OUTPUT.map((o, i) => (
              <li key={i} className="text-sm text-slate-500 flex items-start gap-2"><span className="text-slate-300 mt-0.5">•</span> {o}</li>
            ))}
          </ul>
        </section>

        <section className="mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-1.5">Next Action</h4>
          <p className="text-sm text-slate-500">Compile analysis and generate comparison report.</p>
        </section>

        <button className="mt-auto w-full py-3 bg-[#eef2ff] text-[#4f46e5] font-bold rounded-xl text-sm hover:bg-[#eef2ff] transition-colors flex items-center justify-center gap-2">
          View Full Details <ArrowRight size={16} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  </div>
);
