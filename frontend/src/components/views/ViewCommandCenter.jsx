import {
  Plus,
  ChevronDown,
  Check,
  Square,
  Paperclip,
  ArrowUp,
  Maximize2,
  UsersRound,
  Boxes,
  ClipboardCheck,
  FileText,
  Link2,
  User,
  Timer,
  Search,
  MapPin,
  BarChart3,
  FileStack,
  Coins,
} from "lucide-react";

const PLAN_ITEMS = [
  "Research prime locations in Thane",
  "Analyze competitors and market trends",
  "Study rental costs and property options",
  "Create pricing strategy and financial model",
  "Develop complete execution plan",
  "Identify required licenses and permits",
];

const AGENT_TASKS = [
  { agent: "Research Agent", task: "Finding location data...", LucideIcon: FileText, tint: "bg-emerald-50 text-emerald-600", status: "loading", wide: true },
  { agent: "Analysis Agent", task: "Analyzing competitors...", LucideIcon: Link2, tint: "bg-emerald-50 text-emerald-600", status: "loading", wide: false },
  { agent: "Finance Agent", task: "Building financial model...", LucideIcon: User, tint: "bg-[#eef2ff] text-[#4f46e5]", status: "queued" },
  { agent: "Strategy Agent", task: "Planning execution roadmap...", LucideIcon: Timer, tint: "bg-orange-50 text-orange-500", status: "queued" },
];

const TOOLS = [
  { name: "Web Search", LucideIcon: Search, color: "text-emerald-600 bg-emerald-50" },
  { name: "Maps API", LucideIcon: MapPin, color: "text-blue-600 bg-blue-50" },
  { name: "Data Analysis", LucideIcon: BarChart3, color: "text-[#4f46e5] bg-[#eef2ff]" },
  { name: "Document RAG", LucideIcon: FileStack, color: "text-orange-500 bg-orange-50" },
  { name: "Financial Modeling", LucideIcon: Coins, color: "text-violet-600 bg-violet-50" },
];

const QUICK_TAGS = ["Deep Research", "Create Plan", "Analyze Data", "Generate Strategy"];

// Live Agent Tree leaf tasks
const RESEARCH_LEAVES = ["Location Research", "Competitor Research", "Market Analysis"];
const ANALYSIS_LEAVES = ["Financial Model", "Pricing Strategy", "Demand Analysis"];
const EXECUTION_LEAVES = ["Operations Plan", "Legal & Compliance", "Launch Strategy"];

// ---- Coordinate-based Live Agent Tree with curved SVG connectors ----
const TREE = {
  W: 360,
  H: 640,
  green: "#22c55e",
  violet: "#8b5cf6",
  blue: "#4f46e5",
  // Orion Planner node (centered top)
  planner: { x: 90, top: 8, w: 200, h: 56 },
  // Research (left) + Analysis (right) nodes
  research: { x: 14, y: 132, w: 120, h: 46 },
  analysis: { x: 196, y: 132, w: 120, h: 46 },
  // Execution node (centered lower)
  execution: { x: 105, y: 430, w: 150, h: 46 },
  // leaf rows (dot x = start of leaf)
  researchLeafX: 54,
  researchLeafY: [206, 246, 286],
  analysisLeafX: 236,
  analysisLeafY: [206, 246, 286],
  execLeafX: 145,
  execLeafY: [498, 540, 582],
};

// Elbow with rounded corner: vertical from (x1,y1) down, then horizontal to (x2,y2).
// r = corner radius. Assumes y2 > y1.
const elbow = (x1, y1, x2, y2, r = 10) => {
  const dir = x2 > x1 ? 1 : -1;
  const cy = y2 - r;
  return `M ${x1} ${y1} L ${x1} ${cy} Q ${x1} ${y2} ${x1 + dir * r} ${y2} L ${x2} ${y2}`;
};

// Smooth vertical S-curve (for planner->branch and branch->execution converge).
const sCurve = (x1, y1, x2, y2) => {
  const my = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
};

const TreeLeaf = ({ label, color, x, y, w }) => (
  <div className="absolute flex items-center gap-2" style={{ left: x, top: y - 8, width: w }}>
    <span className="w-4 h-4 rounded-full border-2 grid place-items-center bg-white shrink-0" style={{ borderColor: color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }}></span>
    </span>
    <span className="text-[12px] font-medium text-slate-600 whitespace-nowrap">{label}</span>
  </div>
);

const LiveAgentTree = () => {
  const T = TREE;
  const plCx = T.planner.x + T.planner.w / 2;
  const plBottom = T.planner.top + T.planner.h;
  const rCx = T.research.x + T.research.w / 2;
  const rBottom = T.research.y + T.research.h;
  const aCx = T.analysis.x + T.analysis.w / 2;
  const aBottom = T.analysis.y + T.analysis.h;
  const eCx = T.execution.x + T.execution.w / 2;
  const eTop = T.execution.y;

  // spine x (vertical line) for each group — sits just left of the leaf dots
  const rSpineX = T.researchLeafX - 16;
  const aSpineX = T.analysisLeafX - 16;
  const eSpineX = T.execLeafX - 16;
  const dotR = 8; // half of leaf dot (16px)

  return (
    <div className="relative mx-auto" style={{ width: T.W, height: T.H }}>
      <svg className="absolute inset-0 pointer-events-none" width={T.W} height={T.H} viewBox={`0 0 ${T.W} ${T.H}`}>
        <defs>
          {[["g", T.green], ["v", T.violet], ["b", T.blue]].map(([id, col]) => (
            <marker key={id} id={`ah-${id}`} viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9" fill="none" stroke={col} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </marker>
          ))}
        </defs>

        {/* Planner -> Research (green) & Analysis (violet) — hook down then out, arrowhead into node top */}
        <path d={sCurve(plCx - 26, plBottom, rCx, T.research.y - 6)} stroke={T.green} strokeWidth="2.5" fill="none" markerEnd="url(#ah-g)" />
        <path d={sCurve(plCx + 26, plBottom, aCx, T.analysis.y - 6)} stroke={T.violet} strokeWidth="2.5" fill="none" markerEnd="url(#ah-v)" />

        {/* Research spine + elbows to leaves (green) */}
        {T.researchLeafY.map((ly, i) => (
          <path key={`r${i}`} d={elbow(rSpineX, rBottom, T.researchLeafX - dotR - 2, ly)} stroke={T.green} strokeWidth="2" fill="none" />
        ))}
        {/* Analysis spine + elbows to leaves (violet) */}
        {T.analysisLeafY.map((ly, i) => (
          <path key={`a${i}`} d={elbow(aSpineX, aBottom, T.analysisLeafX - dotR - 2, ly)} stroke={T.violet} strokeWidth="2" fill="none" />
        ))}

        {/* Research (green) & Analysis (violet) -> Execution top, arrowhead */}
        <path d={sCurve(rSpineX, T.researchLeafY[2] + 10, eCx - 18, eTop - 6)} stroke={T.green} strokeWidth="2.5" fill="none" markerEnd="url(#ah-b)" />
        <path d={sCurve(aSpineX, T.analysisLeafY[2] + 10, eCx + 18, eTop - 6)} stroke={T.violet} strokeWidth="2.5" fill="none" markerEnd="url(#ah-b)" />

        {/* Execution spine + elbows to leaves (violet) */}
        {T.execLeafY.map((ly, i) => (
          <path key={`e${i}`} d={elbow(eSpineX, T.execution.y + T.execution.h, T.execLeafX - dotR - 2, ly)} stroke={T.violet} strokeWidth="2" fill="none" />
        ))}
      </svg>

      {/* Orion Planner */}
      <div className="absolute flex items-center gap-3 bg-[#eef2ff]/70 border border-[#c7d2fe] rounded-2xl px-4 py-3" style={{ left: T.planner.x, top: T.planner.top, width: T.planner.w }}>
        <div className="w-10 h-10 rounded-full bg-[#4f46e5] text-white flex items-center justify-center shrink-0 ring-4 ring-[#eef2ff]">
          <Boxes size={18} strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <h4 className="text-sm font-bold text-slate-800 leading-tight">Orion Planner</h4>
          <p className="text-[11px] text-slate-400 truncate">Decomposing objective...</p>
        </div>
      </div>

      {/* Research node */}
      <div className="absolute flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2.5" style={{ left: T.research.x, top: T.research.y, width: T.research.w }}>
        <UsersRound size={17} className="text-emerald-600 shrink-0" strokeWidth={2} />
        <div>
          <h5 className="text-[13px] font-bold text-emerald-700 leading-none">Research</h5>
          <p className="text-[10px] text-emerald-500/70 mt-1">3 agents</p>
        </div>
      </div>

      {/* Analysis node (active — blue ring like the image) */}
      <div className="absolute flex items-center gap-2 bg-violet-50 border border-blue-300 ring-2 ring-blue-100 rounded-xl px-3 py-2.5" style={{ left: T.analysis.x, top: T.analysis.y, width: T.analysis.w }}>
        <Boxes size={17} className="text-violet-600 shrink-0" strokeWidth={2} />
        <div>
          <h5 className="text-[13px] font-bold text-violet-700 leading-none">Analysis</h5>
          <p className="text-[10px] text-violet-500/70 mt-1">2 agents</p>
        </div>
      </div>

      {/* Execution node */}
      <div className="absolute flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2.5" style={{ left: T.execution.x, top: T.execution.y, width: T.execution.w }}>
        <ClipboardCheck size={17} className="text-blue-600 shrink-0" strokeWidth={2} />
        <div>
          <h5 className="text-[13px] font-bold text-[#0b1220] leading-none">Execution</h5>
          <p className="text-[10px] text-slate-400 mt-1">2 agents</p>
        </div>
      </div>

      {/* Leaves */}
      {RESEARCH_LEAVES.map((l, i) => (
        <TreeLeaf key={`rl${i}`} label={l} color={T.green} x={T.researchLeafX} y={T.researchLeafY[i]} w={130} />
      ))}
      {ANALYSIS_LEAVES.map((l, i) => (
        <TreeLeaf key={`al${i}`} label={l} color={T.violet} x={T.analysisLeafX} y={T.analysisLeafY[i]} w={130} />
      ))}
      {EXECUTION_LEAVES.map((l, i) => (
        <TreeLeaf key={`el${i}`} label={l} color={T.violet} x={T.execLeafX} y={T.execLeafY[i]} w={130} />
      ))}
    </div>
  );
};

export const ViewCommandCenter = () => (
  <div className="p-6 sm:p-7 h-full flex flex-col max-w-[1400px] mx-auto bg-[#f8fafc]">
    {/* Header */}
    <div className="flex justify-between items-start mb-6 shrink-0">
      <div>
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220] mb-2">Orion Command Center</h1>
        <p className="text-[15px] text-[#64748b]">Turn your ideas into real outcomes with AI agents.</p>
      </div>
      <div className="flex items-center gap-3">
        <button className="bg-white border border-[#e6ebf2] text-slate-700 text-sm rounded-xl px-4 py-2.5 shadow-sm font-semibold flex items-center gap-2">
          GPT-4o <ChevronDown size={16} className="text-slate-400" />
        </button>
        <button className="bg-[#4f46e5] hover:bg-[#4338ca] text-white font-bold h-12 px-5 rounded-xl text-[15px] transition-colors shadow-md whitespace-nowrap flex items-center gap-2">
          <Plus size={18} strokeWidth={2.5} /> New Chat
        </button>
      </div>
    </div>

    <div className="flex-1 flex gap-6 min-h-0">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 scrollbar-hide">
          {/* User Message */}
          <div className="flex items-start gap-2.5 justify-start">
            <div className="w-8 h-8 shrink-0 rounded-full bg-blue-500 text-white grid place-items-center">
              <User size={16} strokeWidth={2.2} />
            </div>
            <div>
              <div className="bg-[#eef0fb] rounded-2xl px-4 py-3 text-sm leading-snug text-slate-700 max-w-md">
                I want to open a cafe in Thane. Research locations, competitors, rent, pricing and create an execution plan.
              </div>
              <div className="text-[11px] text-slate-400 mt-1 text-right">10:24 AM</div>
            </div>
          </div>

          {/* AI Message */}
          <div className="flex gap-2.5 items-start">
            <div className="w-8 h-8 shrink-0 rounded-full bg-[#eef2ff] grid place-items-center">
              <Boxes size={16} className="text-[#4f46e5]" strokeWidth={2} />
            </div>
            <div className="flex-1 space-y-4">
              <div className="bg-white border border-[#e6ebf2] rounded-2xl p-4 shadow-sm">
                <p className="text-sm leading-snug text-slate-700 mb-3">I'll help you with this! I'll create a comprehensive plan to open a cafe in Thane. Here's what I'll do:</p>
                <ul className="flex flex-col gap-2.5">
                  {PLAN_ITEMS.map((item, i) => (
                    <li key={i} className="flex items-center gap-2.5 text-sm text-slate-700">
                      <span className="w-5 h-5 shrink-0 rounded-full bg-[#4f46e5] grid place-items-center">
                        <Check size={11} className="text-white" strokeWidth={3} />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Progress card */}
              <div className="bg-white border border-[#e6ebf2] rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 shrink-0 rounded-full border-4 border-[#c7d2fe] border-t-indigo-500 animate-spin"></div>
                  <div className="flex-1">
                    <div className="text-sm font-bold text-slate-800">Creating dynamic plan...</div>
                    <div className="text-xs text-slate-400 leading-tight mt-0.5">Deploying specialized agents and gathering real-time...</div>
                  </div>
                  <button className="flex items-center gap-1.5 bg-slate-100 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors">
                    <Square size={11} className="fill-slate-600 text-slate-600" /> Stop
                  </button>
                </div>

                <div className="mt-3 flex flex-col gap-2">
                  {AGENT_TASKS.map((t, i) => (
                    <div key={i} className="flex items-center gap-3 py-1.5">
                      <span className={`w-7 h-7 shrink-0 rounded-lg grid place-items-center ${t.tint}`}>
                        <t.LucideIcon size={15} strokeWidth={2} />
                      </span>
                      <span className="text-sm font-semibold text-slate-700 w-28 shrink-0">{t.agent}</span>
                      <span className="text-xs text-slate-400 flex-1 min-w-0 truncate">{t.task}</span>
                      {t.status === "loading" ? (
                        <div className="w-16 h-2 rounded-full bg-slate-100 overflow-hidden shrink-0">
                          <div className={`h-2 rounded-full bg-[#4f46e5] ${t.wide ? "w-full" : "w-2/3"}`}></div>
                        </div>
                      ) : (
                        <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 rounded-md px-2.5 py-1 shrink-0">Queued</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Composer */}
        <div className="pt-4 shrink-0">
          <div className="flex items-center gap-2 bg-white border border-[#e6ebf2] rounded-2xl pl-4 pr-2.5 py-2 shadow-sm">
            <input type="text" placeholder="Type your message or objective..." className="flex-1 min-w-0 bg-transparent border-0 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none py-1.5" />
            <button className="p-1.5 text-slate-400 hover:text-slate-600" aria-label="Attach file">
              <Paperclip size={18} />
            </button>
            <button className="w-9 h-9 shrink-0 rounded-full bg-[#4f46e5] hover:bg-[#4f46e5] grid place-items-center text-white transition-colors" aria-label="Send">
              <ArrowUp size={18} strokeWidth={2.5} />
            </button>
          </div>
          <div className="flex gap-2 mt-3 flex-wrap">
            {QUICK_TAGS.map((tag, i) => (
              <button key={i} className="whitespace-nowrap px-3 py-2 rounded-xl border border-[#e6ebf2] bg-white text-xs font-medium text-slate-500 hover:bg-[#eef2ff] hover:border-[#c7d2fe] transition-colors">
                {tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-[420px] flex flex-col gap-5 shrink-0 overflow-y-auto scrollbar-hide">
        {/* Live Agent Tree */}
        <div className="bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-5">
          <div className="flex justify-between items-center mb-5">
            <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
              Live Agent Tree <span className="text-xs text-slate-400 font-medium">(Generating...)</span>
            </h3>
            <button className="text-slate-400 hover:text-slate-600"><Maximize2 size={16} /></button>
          </div>

          {/* Live tree with curved connectors */}
          <LiveAgentTree />
        </div>

        {/* Tools Being Used */}
        <div className="bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-5">
          <h3 className="font-bold text-slate-800 text-base mb-4">Tools Being Used</h3>
          <div className="grid grid-cols-2 gap-2.5">
            {TOOLS.map((tool, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-slate-50 text-sm font-medium text-slate-600">
                <span className={`w-6 h-6 rounded-md grid place-items-center ${tool.color}`}>
                  <tool.LucideIcon size={14} strokeWidth={2} />
                </span>
                {tool.name}
              </div>
            ))}
            <div className="flex items-center justify-center px-3 py-2.5 rounded-xl bg-slate-50 text-sm font-medium text-slate-400 hover:bg-slate-100 cursor-pointer">
              More …
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);
