import { ChevronRight, UploadCloud, ArrowRight, MoreHorizontal } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = ["Upload Files", "Connect Sources", "Data Sync", "Source Management"];

/* --- Brand icons (inline SVG for crisp, high-quality rendering) --- */
const GoogleDriveIcon = () => (
  <svg viewBox="0 0 87.3 78" className="w-7 h-7">
    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da" />
    <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47" />
    <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335" />
    <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d" />
    <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc" />
    <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00" />
  </svg>
);
const NotionIcon = () => (
  <svg viewBox="0 0 24 24" className="w-7 h-7">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.328s0 .84-1.168.84l-3.222.186c-.093-.187 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933z" fill="#000" />
  </svg>
);
const ConfluenceIcon = () => (
  <svg viewBox="0 0 24 24" className="w-7 h-7">
    <path d="M2.3 17.9c-.2.3-.4.7-.6 1-.2.4-.1.9.3 1.1l4 2.5c.4.2.9.1 1.2-.3.2-.3.4-.6.5-.9 1.3-2.1 2.6-1.9 4.9-.8l4 1.9c.4.2.9 0 1.1-.4l1.9-4.3c.2-.4 0-.9-.4-1.1-.8-.4-2.5-1.2-4-1.9-5.3-2.6-9.8-2.4-12.8 3.1z" fill="#2684ff" />
    <path d="M21.7 6.1c.2-.3.4-.7.6-1 .2-.4.1-.9-.3-1.1l-4-2.5c-.4-.3-.9-.1-1.2.3-.2.3-.4.6-.5.9-1.3 2.1-2.6 1.9-4.9.8l-4-1.9c-.4-.2-.9 0-1.1.4l-1.9 4.3c-.2.4 0 .9.4 1.1.8.4 2.5 1.2 4 1.9 5.3 2.6 9.8 2.3 12.8-3.2z" fill="#2684ff" />
  </svg>
);
const SharePointIcon = () => (
  <svg viewBox="0 0 24 24" className="w-7 h-7">
    <circle cx="9" cy="7" r="5.2" fill="#036c70" />
    <circle cx="15.5" cy="11.5" r="4.6" fill="#1a9ba1" />
    <circle cx="12" cy="17.5" r="3.8" fill="#37c6d0" />
    <path d="M11 6.5H4.6A1.1 1.1 0 0 0 3.5 7.6v6.8A1.1 1.1 0 0 0 4.6 15.5H11a1.1 1.1 0 0 0 1.1-1.1V7.6A1.1 1.1 0 0 0 11 6.5z" fill="#03787c" />
    <text x="7.7" y="12.6" fontSize="6" fontWeight="700" fill="#fff" textAnchor="middle" fontFamily="Arial">S</text>
  </svg>
);
const SlackIcon = () => (
  <svg viewBox="0 0 24 24" className="w-7 h-7">
    <path d="M5.04 15.16a2.4 2.4 0 1 1-2.4-2.4h2.4z" fill="#e01e5a" />
    <path d="M6.25 15.16a2.4 2.4 0 0 1 4.8 0v6.02a2.4 2.4 0 1 1-4.8 0z" fill="#e01e5a" />
    <path d="M8.65 5.04a2.4 2.4 0 1 1 2.4-2.4v2.4z" fill="#36c5f0" />
    <path d="M8.65 6.25a2.4 2.4 0 0 1 0 4.8H2.63a2.4 2.4 0 1 1 0-4.8z" fill="#36c5f0" />
    <path d="M18.77 8.65a2.4 2.4 0 1 1 2.4 2.4h-2.4z" fill="#2eb67d" />
    <path d="M17.56 8.65a2.4 2.4 0 0 1-4.8 0V2.63a2.4 2.4 0 1 1 4.8 0z" fill="#2eb67d" />
    <path d="M15.16 18.77a2.4 2.4 0 1 1-2.4 2.4v-2.4z" fill="#ecb22e" />
    <path d="M15.16 17.56a2.4 2.4 0 0 1 0-4.8h6.02a2.4 2.4 0 1 1 0 4.8z" fill="#ecb22e" />
  </svg>
);
const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" className="w-7 h-7">
    <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.31-.54-1.53.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.65.25 2.87.12 3.18.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58C20.56 22.3 24 17.8 24 12.5 24 5.87 18.63.5 12 .5z" fill="#181717" />
  </svg>
);

const SOURCES = [
  { name: "Google Drive", sub: "Import files from Google", Icon: GoogleDriveIcon },
  { name: "Notion", sub: "Sync Notion workspace", Icon: NotionIcon },
  { name: "Confluence", sub: "Connect Confluence", Icon: ConfluenceIcon },
  { name: "SharePoint", sub: "Connect SharePoint", Icon: SharePointIcon },
  { name: "Slack", sub: "Sync Slack channels", Icon: SlackIcon },
  { name: "GitHub", sub: "Connect repositories", Icon: GitHubIcon },
];

/* File type mini icons for recent uploads */
const PdfFile = () => (
  <span className="w-11 h-11 rounded-xl bg-rose-50 grid place-items-center">
    <svg viewBox="0 0 24 24" className="w-6 h-6"><path d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="#fee2e2" stroke="#ef4444" strokeWidth="1.3"/><path d="M14 2v4h4" fill="none" stroke="#ef4444" strokeWidth="1.3"/><text x="12" y="17" fontSize="5.5" fontWeight="700" fill="#ef4444" textAnchor="middle" fontFamily="Arial">PDF</text></svg>
  </span>
);
const DocFile = () => (
  <span className="w-11 h-11 rounded-xl bg-blue-50 grid place-items-center">
    <svg viewBox="0 0 24 24" className="w-6 h-6"><path d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="#dbeafe" stroke="#4f46e5" strokeWidth="1.3"/><path d="M14 2v4h4" fill="none" stroke="#4f46e5" strokeWidth="1.3"/><path d="M8 12h8M8 15h8M8 18h5" stroke="#4f46e5" strokeWidth="1.2" strokeLinecap="round"/></svg>
  </span>
);
const XlsFile = () => (
  <span className="w-11 h-11 rounded-xl bg-emerald-50 grid place-items-center">
    <svg viewBox="0 0 24 24" className="w-6 h-6"><path d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="#d1fae5" stroke="#10b981" strokeWidth="1.3"/><path d="M14 2v4h4" fill="none" stroke="#10b981" strokeWidth="1.3"/><text x="12" y="17" fontSize="5.5" fontWeight="700" fill="#10b981" textAnchor="middle" fontFamily="Arial">XLS</text></svg>
  </span>
);

const UPLOADS = [
  { name: "Q3_Strategy.pdf", meta: "2.4 MB · Sep 15, 2026", status: "Completed", File: PdfFile },
  { name: "Product_Manual.docx", meta: "1.8 MB · Sep 14, 2026", status: "Completed", File: DocFile },
  { name: "Market_Data.xlsx", meta: "3.1 MB · Sep 13, 2026", status: "Processing", File: XlsFile },
];

export const ViewUploadSources = () => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Upload / Connect Sources" }]} />

    {/* Header */}
    <div className="flex items-start gap-4 mb-7">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6M9 15l3-3 3 3"/></svg>
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Upload / Connect Sources</h1>
        <p className="text-[15px] text-slate-500 mt-2">Upload files or connect external data sources</p>
      </div>
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-8 border-b border-[#e6ebf2] mb-7">
      {TABS.map((t, i) => (
        <button
          key={t}
          className={`pb-3.5 text-[15px] font-semibold border-b-2 -mb-px transition-colors ${
            i === 0 ? "text-[#4f46e5] border-[#4f46e5]" : "text-slate-500 border-transparent hover:text-slate-700"
          }`}
        >
          {t}
        </button>
      ))}
    </div>

    {/* Two-column body */}
    <div className="grid grid-cols-[1.15fr_1fr] gap-6 items-start">
      {/* Left column */}
      <div className="space-y-6">
        {/* Dropzone */}
        <div className="rounded-2xl border-2 border-dashed border-[#e6ebf2] bg-slate-50/40 px-6 py-12 flex flex-col items-center text-center">
          <UploadCloud size={52} className="text-[#4f46e5]" strokeWidth={1.6} />
          <p className="text-[22px] font-bold text-[#0b1220] mt-5">Drag and drop files here</p>
          <p className="text-[15px] text-slate-500 mt-1.5">or click to browse</p>
          <p className="text-[13px] text-slate-400 mt-3">Supports PDF, DOC, DOCX, TXT, MD, XLS, CSV (Max 50MB)</p>
          <button className="mt-6 h-12 px-8 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            Browse Files
          </button>
        </div>

        {/* Recent Uploads */}
        <div className="rounded-2xl border border-[#e6ebf2] shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[17px] font-bold text-[#0b1220]">Recent Uploads</h2>
            <button className="text-[14px] font-semibold text-[#4f46e5] flex items-center gap-1">
              View all <ArrowRight size={15} />
            </button>
          </div>
          <div className="space-y-1">
            {UPLOADS.map((u, i) => (
              <div key={u.name} className={`flex items-center gap-3.5 py-3 ${i !== UPLOADS.length - 1 ? "border-b border-slate-100" : ""}`}>
                <u.File />
                <div className="flex-1 min-w-0">
                  <p className="text-[15px] font-semibold text-slate-800 truncate">{u.name}</p>
                  <p className="text-[13px] text-slate-400">{u.meta}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-[12px] font-semibold ${
                  u.status === "Completed" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-600"
                }`}>{u.status}</span>
                <button className="w-8 h-8 grid place-items-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                  <MoreHorizontal size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right column: External Sources */}
      <div className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <h2 className="text-[18px] font-bold text-[#0b1220] mb-5">Connect External Sources</h2>
        <div className="space-y-1">
          {SOURCES.map((s, i) => (
            <div key={s.name} className={`flex items-center gap-3.5 py-3.5 ${i !== SOURCES.length - 1 ? "border-b border-slate-100" : ""}`}>
              <span className="w-11 h-11 grid place-items-center shrink-0"><s.Icon /></span>
              <div className="flex-1 min-w-0">
                <p className="text-[15px] font-bold text-slate-800">{s.name}</p>
                <p className="text-[13px] text-slate-400">{s.sub}</p>
              </div>
              <button className="h-10 px-6 rounded-xl bg-[#1e2438] text-white text-[14px] font-semibold hover:bg-[#2b3350]">
                Connect
              </button>
            </div>
          ))}
        </div>
        <button className="mt-5 text-[15px] font-semibold text-[#4f46e5] flex items-center gap-1.5">
          View more integrations <ArrowRight size={16} />
        </button>
      </div>
    </div>
  </div>
);
