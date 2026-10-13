import { ObsCard, StatusChip, ObsTabs, PanelTitle, pageShellCls } from "./ObsShared.jsx";
import { ArrowLeft, MoreHorizontal, CheckCircle2 } from "lucide-react";

const STEPS = [
  { n: 1, title: "Initialize", sub: "Agent initialized with config", time: "120ms", done: true },
  { n: 2, title: "Retrieve Context", sub: "Query vector database (Pinecone)", time: "532ms", done: true },
  { n: 3, title: "Plan", sub: "Generate execution plan", time: "1.2s", done: true },
  { n: 4, title: "Execute Tools", sub: "Use web search tool", time: "12.4s", done: true, active: true },
  { n: 5, title: "LLM Call", sub: "Generate response (gpt-4o)", time: "45.2s", done: true },
  { n: 6, title: "Post Process", sub: "Format and validate output", time: "1.1s", done: true },
];

const TABS = ["Trace Timeline", "Input / Output", "Logs", "Metadata", "Costs"];

export const ViewObsTrace = ({ onBack }) => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <button
        onClick={onBack}
        className="flex items-center gap-2 h-11 px-4 rounded-xl border border-[#e6ebf2] bg-white text-[14px] font-semibold text-[#334155] hover:bg-[#f5f8fc] mb-5"
      >
        <ArrowLeft size={16} /> Back to Runs
      </button>

      <div className="flex items-center gap-3 mb-2">
        <div className="w-12 h-12 rounded-xl bg-[#4f46e5] grid place-items-center text-[14px] font-bold text-white shrink-0 shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
          MA
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[28px] font-extrabold text-[#0b1220] tracking-[-0.4px]">
            run_7c9e1
          </span>
          <StatusChip label="● Success" tone="green" />
        </div>
        <div className="ml-auto flex items-center gap-2.5">
          <button className="h-11 px-5 rounded-xl bg-[#4f46e5] text-white text-[14px] font-bold hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
            Re-run
          </button>
          <button className="w-11 h-11 rounded-xl border border-[#e6ebf2] grid place-items-center text-[#64748b] hover:bg-[#f5f8fc]">
            <MoreHorizontal size={17} />
          </button>
        </div>
      </div>
      <p className="text-[14px] text-[#64748b] mb-6 ml-[60px]">
        Marketing Agent &nbsp;·&nbsp; Jan 12, 2026, 10:24 AM &nbsp;·&nbsp; 3m 12s &nbsp;·&nbsp; $0.034
      </p>

      <ObsTabs tabs={TABS} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-5">
        <div className="flex flex-col gap-3">
          {STEPS.map((s) => (
            <ObsCard
              key={s.n}
              className={`p-4 ${s.active ? "ring-2 ring-[#4f46e5]/25 border-[#c7d2fe]" : ""}`}
            >
              <div className="flex items-start gap-3">
                <span className="w-7 h-7 rounded-full bg-[#e7f8ef] text-[#16a34a] grid place-items-center shrink-0 mt-0.5">
                  <CheckCircle2 size={15} strokeWidth={2.4} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[15px] font-bold text-[#0b1220]">
                      {s.n}. {s.title}
                    </p>
                    <span className="text-[13px] font-semibold text-[#64748b]">{s.time}</span>
                  </div>
                  <p className="text-[13px] text-[#64748b] mt-0.5">{s.sub}</p>
                </div>
              </div>
            </ObsCard>
          ))}
        </div>

        <ObsCard className="p-5 h-fit">
          <PanelTitle className="mb-4">Step Details</PanelTitle>
          <dl className="text-[14px]">
            <div className="flex justify-between py-2 border-b border-[#eef2f8]">
              <dt className="text-[#64748b]">Step</dt>
              <dd className="font-semibold text-[#0b1220]">Execute Tools</dd>
            </div>
            <div className="flex justify-between py-2 border-b border-[#eef2f8]">
              <dt className="text-[#64748b]">Type</dt>
              <dd className="font-semibold text-[#0b1220]">Tool</dd>
            </div>
            <div className="flex justify-between py-2">
              <dt className="text-[#64748b]">Tool</dt>
              <dd className="font-semibold text-[#0b1220]">Search API</dd>
            </div>
          </dl>

          <div className="mt-4">
            <p className="text-[12px] font-bold text-[#64748b] mb-1.5 uppercase tracking-wide">
              Input
            </p>
            <pre className="rounded-xl bg-[#f8fafc] border border-[#e6ebf2] p-3 text-[12px] font-mono text-[#334155] whitespace-pre-wrap">{`{
  "query": "best marketing…"
}`}</pre>
          </div>
          <div className="mt-4">
            <p className="text-[12px] font-bold text-[#64748b] mb-1.5 uppercase tracking-wide">
              Output
            </p>
            <pre className="rounded-xl bg-[#f8fafc] border border-[#e6ebf2] p-3 text-[12px] font-mono text-[#334155] whitespace-pre-wrap">{`{
  "results": [...]
}`}</pre>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div>
              <p className="text-[12px] font-bold text-[#64748b] uppercase tracking-wide">
                Duration
              </p>
              <p className="text-[16px] font-bold text-[#0b1220]">12.4s</p>
            </div>
            <StatusChip label="● Success" tone="green" />
          </div>
        </ObsCard>
      </div>
    </div>
  </div>
);
