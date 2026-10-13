import {
  ChevronRight, ArrowLeft, Download, MoreHorizontal, RotateCcw, RotateCw,
  Minus, Plus, ChevronDown, Maximize2, Users, FileText,
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = ["Details", "Comments", "Related"];

/* Small PDF badge icon */
const PdfBadge = () => (
  <svg viewBox="0 0 24 24" className="w-8 h-8">
    <path d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="#fee2e2" stroke="#ef4444" strokeWidth="1.3" />
    <path d="M14 2v4h4" fill="none" stroke="#ef4444" strokeWidth="1.3" />
    <text x="12" y="17" fontSize="5.5" fontWeight="700" fill="#ef4444" textAnchor="middle" fontFamily="Arial">PDF</text>
  </svg>
);

const OrionMark = () => (
  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#60a5fa] via-[#4f46e5] to-[#8b5cf6] grid place-items-center shadow-sm">
    <svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="currentColor"><path d="M12 2 15 9l7 3-7 3-3 7-3-7-7-3 7-3z" /></svg>
  </div>
);

/* Thumbnail mini page */
const Thumb = ({ n, active }) => (
  <div className="flex flex-col items-center gap-1.5">
    <div className={`w-[92px] h-[118px] rounded-lg bg-white overflow-hidden ${active ? "ring-2 ring-[#4f46e5] border border-[#4f46e5]" : "border border-[#e6ebf2]"}`}>
      <div className="p-2">
        <div className="flex items-center gap-1 mb-1.5">
          <div className="w-2 h-2 rounded-full bg-[#818cf8]" />
          <div className="h-1 w-6 bg-slate-300 rounded" />
        </div>
        <div className="space-y-[3px]">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-[3px] bg-slate-200 rounded" style={{ width: `${70 + ((i * 13) % 28)}%` }} />
          ))}
        </div>
      </div>
    </div>
    <span className="text-[12px] text-slate-500">{n}</span>
  </div>
);

const MetaRow = ({ label, children }) => (
  <div>
    <p className="text-[14px] font-bold text-[#0b1220]">{label}</p>
    <div className="text-[14px] text-slate-500 mt-1">{children}</div>
  </div>
);

export const ViewDocumentViewer = ({ onBack }) => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation
      items={[
        { label: "Knowledge & Memory" },
        { label: "Knowledge Base", onClick: onBack },
        { label: "Document" },
      ]}
    />

    {/* Header */}
    <div className="flex items-start gap-4 mb-6">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <FileText size={26} />
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Document Viewer</h1>
        <p className="text-[15px] text-slate-500 mt-2">View and manage documents</p>
      </div>
    </div>

    {/* Viewer container */}
    <div className="rounded-2xl border border-[#e6ebf2] shadow-sm overflow-hidden">
      {/* Top toolbar */}
      <div className="flex items-center gap-4 px-5 py-4 border-b border-[#e6ebf2]">
        <button onClick={onBack} className="h-11 px-4 rounded-xl border border-[#e6ebf2] text-[14px] font-semibold text-slate-700 flex items-center gap-2 hover:bg-slate-50">
          <ArrowLeft size={17} /> Back
        </button>
        <div className="flex items-center gap-3">
          <PdfBadge />
          <div>
            <p className="text-[16px] font-bold text-slate-800 leading-tight">Product Strategy 2026.pdf</p>
            <p className="text-[13px] text-slate-400 mt-0.5">PDF • 2.4 MB • Updated Sep 15, 2026</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2.5">
          <button className="h-11 px-5 rounded-xl bg-[#4f46e5] text-white text-[14px] font-semibold flex items-center gap-2 hover:bg-[#4338ca]">
            <Download size={17} /> Download
          </button>
          <button className="w-11 h-11 rounded-xl border border-[#e6ebf2] grid place-items-center text-slate-500 hover:bg-slate-50">
            <MoreHorizontal size={18} />
          </button>
        </div>
      </div>

      {/* Body: thumbs | canvas | details */}
      <div className="grid grid-cols-[132px_1fr_320px]">
        {/* Thumbnail rail */}
        <div className="border-r border-[#e6ebf2] p-4 space-y-4 max-h-[640px] overflow-y-auto scrollbar-hide bg-slate-50/30">
          {[1, 2, 3, 4].map((n) => <Thumb key={n} n={n} active={n === 1} />)}
        </div>

        {/* Canvas */}
        <div className="border-r border-[#e6ebf2] flex flex-col">
          {/* PDF toolbar */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#e6ebf2]">
            <button className="w-9 h-9 rounded-lg grid place-items-center text-slate-500 hover:bg-slate-100"><RotateCcw size={17} /></button>
            <button className="w-9 h-9 rounded-lg grid place-items-center text-slate-500 hover:bg-slate-100"><RotateCw size={17} /></button>
            <span className="h-9 px-3 rounded-lg bg-slate-100 text-[13px] font-semibold text-slate-600 grid place-items-center">1 / 24</span>
            <div className="flex items-center rounded-lg border border-[#e6ebf2] ml-1">
              <button className="w-9 h-9 grid place-items-center text-slate-500 hover:bg-slate-50"><Minus size={16} /></button>
              <button className="w-9 h-9 grid place-items-center text-slate-500 hover:bg-slate-50 border-l border-[#e6ebf2]"><Plus size={16} /></button>
            </div>
            <button className="h-9 px-3 rounded-lg border border-[#e6ebf2] text-[13px] font-medium text-slate-600 flex items-center gap-2 hover:bg-slate-50">
              100% <ChevronDown size={14} className="text-slate-400" />
            </button>
            <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] grid place-items-center text-slate-500 hover:bg-slate-50 ml-auto"><Maximize2 size={16} /></button>
          </div>

          {/* Document page */}
          <div className="flex-1 grid place-items-center p-8 bg-slate-50/40">
            <div className="w-full max-w-[420px] aspect-[3/4] bg-white rounded-lg shadow-lg border border-[#e6ebf2] relative overflow-hidden">
              <div className="p-10">
                <div className="flex items-center gap-2.5 mb-16">
                  <OrionMark />
                  <span className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Orion</span>
                </div>
                <h2 className="text-[40px] leading-[1.05] font-extrabold text-[#0b1220]">Product<br />Strategy 2026</h2>
                <p className="text-[17px] text-slate-500 mt-6 leading-snug">From idea to execution.<br />All in one place.</p>
                <div className="w-10 h-1 bg-[#4f46e5] rounded mt-10 mb-4" />
                <p className="text-[15px] font-semibold text-slate-700">Confidential</p>
                <p className="text-[15px] text-slate-400">September 2026</p>
              </div>
              {/* decorative wave */}
              <svg viewBox="0 0 420 200" className="absolute bottom-0 left-0 w-full" preserveAspectRatio="none">
                <path d="M0 120 C100 80 180 160 260 120 C330 86 380 130 420 110 L420 200 L0 200 Z" fill="#c7d2fe" opacity="0.7" />
                <path d="M0 150 C110 110 190 180 280 150 C350 126 390 160 420 145 L420 200 L0 200 Z" fill="#a5b4fc" opacity="0.7" />
              </svg>
            </div>
          </div>
        </div>

        {/* Details panel */}
        <div className="flex flex-col max-h-[640px] overflow-y-auto scrollbar-hide">
          {/* Tabs */}
          <div className="flex items-center gap-6 px-5 border-b border-[#e6ebf2]">
            {TABS.map((t, i) => (
              <button key={t} className={`py-4 text-[15px] font-semibold border-b-2 -mb-px ${i === 0 ? "text-[#4f46e5] border-[#4f46e5]" : "text-slate-400 border-transparent hover:text-slate-600"}`}>{t}</button>
            ))}
          </div>
          <div className="p-5 space-y-5">
            <MetaRow label="File Name">Product Strategy 2026.pdf</MetaRow>
            <MetaRow label="Type">PDF Document</MetaRow>
            <MetaRow label="Size">2.4 MB</MetaRow>
            <MetaRow label="Uploaded">Sep 15, 2026, 10:30 AM</MetaRow>
            <MetaRow label="Department">Product</MetaRow>
            <div>
              <p className="text-[14px] font-bold text-[#0b1220] mb-2.5">Tags</p>
              <div className="flex flex-wrap gap-2">
                {["strategy", "product", "2026"].map((t) => (
                  <span key={t} className="px-3 py-1.5 rounded-lg bg-[#eef2ff] text-[#4f46e5] text-[13px] font-medium">{t}</span>
                ))}
                <button className="px-3 py-1.5 rounded-lg border border-[#e6ebf2] text-slate-500 text-[13px] font-medium flex items-center gap-1">
                  <Plus size={13} /> Add Tag
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <p className="text-[14px] font-bold text-[#0b1220]">Access</p>
              <span className="text-[14px] text-slate-600 font-medium flex items-center gap-1.5"><Users size={16} className="text-slate-500" /> All Members</span>
            </div>
            <button className="w-full h-11 rounded-xl border border-[#e6ebf2] text-[14px] font-semibold text-slate-700 hover:bg-slate-50">
              Edit Metadata
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
);
