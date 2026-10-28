// Knowledge · Knowledge Base (ViewKnowledgeBase.jsx)
// Mock layout (breadcrumb + icon header + tabs + toolbar + doc table + list/grid
// toggle + pagination), re-skinned neumorphic, wired to the real backend.
//   rows        = knowledgeApi.listDocuments().documents
//   delete      = knowledgeApi.deleteDocument
//   reindex     = knowledgeApi.reindexDocument (url docs only)
//   open        = knowledgeApi.getDocument(id) -> chunk inspector Modal
//   test search = knowledgeApi.search(q) -> Modal
//   onUpload    = navigate to Upload Sources
import { useEffect, useMemo, useState } from "react";
import {
  FileText, Folder, Globe, Plus, Search, ChevronDown, List, LayoutGrid,
  MoreHorizontal, ArrowRight, Loader2, Eye, RefreshCw, Trash2, Database, Boxes, Clock,
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";
import { knowledgeApi } from "../../knowledgeApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Modal } from "../ui/Modal.jsx";

const TABS = ["All Documents", "Categories", "Tags", "Access Control"];

const TYPE_ICON = { url: Globe, folder: Folder, pdf: FileText, docx: FileText, doc: FileText, csv: FileText, txt: FileText, md: FileText, xls: FileText };

const StatusBadge = ({ status }) => {
  const map = {
    active: "text-emerald-600",
    uploaded: "text-sky-600",
    error: "text-rose-500",
    processing: "text-amber-600",
    review: "text-amber-600",
  };
  const label = status === "uploaded" ? "Stored"
    : status === "active" ? "Indexed"
    : status ? status.charAt(0).toUpperCase() + status.slice(1) : "—";
  return (
    <span className={`neu-chip inline-flex items-center px-3 py-1 text-[12px] font-semibold ${map[(status || "").toLowerCase()] || "text-[#5b6678]"}`}>
      {label}
    </span>
  );
};

const Dropdown = ({ value, onChange, allLabel, options }) => (
  <div className="relative">
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="neu-btn-ghost appearance-none h-11 pl-4 pr-9 text-[14px] font-medium text-[#5b6678] cursor-pointer outline-none"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? (typeof o === "string" ? o.toUpperCase() : o)}</option>
      ))}
    </select>
    <ChevronDown size={16} className="text-[#9aa6b8] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
  </div>
);

const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" }) : "—");

export function ViewKnowledgeBase({ onUpload }) {
  const toast = useToast();
  const [docs, setDocs] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [grid, setGrid] = useState(false);
  const [activeTab, setActiveTab] = useState(0);         // 0 All / 1 Categories / 2 Tags / 3 Access
  const [typeFilter, setTypeFilter] = useState("");      // "" = all
  const [deptFilter, setDeptFilter] = useState("");
  const [sortBy, setSortBy] = useState("latest");        // latest | name | chunks

  const [viewer, setViewer] = useState(null);        // getDocument result
  const [searchModal, setSearchModal] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [searchRes, setSearchRes] = useState(null);
  const [searching, setSearching] = useState(false);

  const load = async () => {
    try {
      const d = await knowledgeApi.listDocuments({ search: q });
      setDocs(d.documents || []);
      setSummary(d.summary || {});
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { const t = setTimeout(load, q ? 250 : 0); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [q]);

  const open = async (doc) => {
    try { setViewer(await knowledgeApi.getDocument(doc.id)); }
    catch (e) { toast.error(e.message); }
  };
  const remove = async (id) => {
    try { await knowledgeApi.deleteDocument(id); setDocs((d) => d.filter((x) => x.id !== id)); toast.success("Document deleted"); }
    catch (e) { toast.error(e.message); }
  };
  const reindex = async (id) => {
    try { await knowledgeApi.reindexDocument(id); toast.success("Reindexed"); load(); }
    catch (e) { toast.error(e.message); }
  };
  const runSearch = async () => {
    if (!searchQ.trim()) return;
    setSearching(true);
    try { setSearchRes(await knowledgeApi.search(searchQ.trim(), 5)); }
    catch (e) { toast.error(e.message); }
    finally { setSearching(false); }
  };

  const count = docs.length;

  // Filter + sort the docs by the active dropdown selections.
  const typeOptions = useMemo(() => [...new Set(docs.map((d) => (d.type || "").toLowerCase()).filter(Boolean))], [docs]);
  const deptOptions = useMemo(() => [...new Set(docs.map((d) => d.department_id || d.department).filter(Boolean))], [docs]);
  const visible = useMemo(() => {
    let out = docs.filter((d) =>
      (!typeFilter || (d.type || "").toLowerCase() === typeFilter) &&
      (!deptFilter || (d.department_id || d.department) === deptFilter));
    if (sortBy === "name") out = [...out].sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    else if (sortBy === "chunks") out = [...out].sort((a, b) => (b.chunks_count || 0) - (a.chunks_count || 0));
    else out = [...out].sort((a, b) => new Date(b.uploaded_at || 0) - new Date(a.uploaded_at || 0));
    return out;
  }, [docs, typeFilter, deptFilter, sortBy]);

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-6 sm:px-7 sm:py-7">
      <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Knowledge Base" }]} />

      {/* Header */}
      <div className="flex items-start gap-4 mb-5">
        <span className="neu-circle w-11 h-11 rounded-xl text-[#4f46e5] grid place-items-center shrink-0">
          <FileText size={20} />
        </span>
        <div className="flex-1 pt-0.5">
          <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">Knowledge Base</h1>
          <p className="text-[13px] text-[#8792a6] mt-1">Company documents, files, and data sources</p>
        </div>
        <button onClick={onUpload} className="neu-btn-primary h-12 px-5 text-[15px] font-semibold flex items-center gap-2">
          <Plus size={18} strokeWidth={2.5} />
          Add Document
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        {[
          { Icon: Database, label: "Documents", value: summary.documents ?? count, tint: "text-[#4f46e5]" },
          { Icon: Boxes, label: "Chunks", value: summary.chunks ?? 0, tint: "text-sky-600" },
          { Icon: Clock, label: "Last Updated", value: summary.last_updated ? fmtDate(summary.last_updated) : "—", tint: "text-violet-600" },
        ].map((s) => (
          <div key={s.label} className="neu-raised rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-[12.5px] font-medium text-[#8792a6]">{s.label}</p>
              <p className="text-[20px] font-semibold text-[#334155] leading-none mt-1.5">{s.value}</p>
            </div>
            <span className={`neu-circle w-10 h-10 rounded-lg grid place-items-center ${s.tint}`}><s.Icon size={18} /></span>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-8 border-b border-[#e2e6ee] mb-6">
        {TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setActiveTab(i)}
            className={`pb-3.5 text-[15px] font-semibold border-b-2 -mb-px transition-colors ${
              i === activeTab ? "text-[#4f46e5] border-[#4f46e5]" : "text-[#8792a6] border-transparent hover:text-[#4f46e5]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-[340px]">
          <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9aa6b8] z-10" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search documents..."
            className="neu-input w-full h-11 pl-10 pr-3 text-[14px] text-[#334155] placeholder:text-[#9aa6b8]"
          />
        </div>
        <Dropdown value={typeFilter} onChange={setTypeFilter} allLabel="All Types" options={typeOptions} />
        <Dropdown value={deptFilter} onChange={setDeptFilter} allLabel="All Departments" options={deptOptions} />
        <div className="relative">
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
            className="neu-btn-ghost appearance-none h-11 pl-4 pr-9 text-[14px] font-medium text-[#5b6678] cursor-pointer outline-none">
            <option value="latest">Latest</option>
            <option value="name">Name A–Z</option>
            <option value="chunks">Most chunks</option>
          </select>
          <ChevronDown size={16} className="text-[#9aa6b8] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
        <div className="ml-auto neu-raised flex items-center rounded-xl overflow-hidden">
          <button onClick={() => setGrid(false)} className={`w-11 h-11 grid place-items-center ${!grid ? "text-[#4f46e5]" : "text-[#8792a6] hover:text-[#5b6678]"}`}>
            <List size={18} />
          </button>
          <button onClick={() => setGrid(true)} className={`w-11 h-11 grid place-items-center ${grid ? "text-[#4f46e5]" : "text-[#8792a6] hover:text-[#5b6678]"}`}>
            <LayoutGrid size={18} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
      ) : count === 0 ? (
        <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">No documents yet. Upload files or ingest a URL in Upload Sources.</div>
      ) : visible.length === 0 ? (
        <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">No documents match the current filters.</div>
      ) : activeTab !== 0 ? (
        /* Grouped views: Categories (by type) / Tags (by status) / Access Control (by department) */
        <div className="space-y-5">
          {Object.entries(
            visible.reduce((acc, d) => {
              const key = activeTab === 1 ? ((d.type || "other").toUpperCase())
                : activeTab === 2 ? (d.status === "active" ? "Indexed" : "Stored")
                : (d.department_id || d.department || "Organization-wide");
              (acc[key] = acc[key] || []).push(d);
              return acc;
            }, {})
          ).map(([group, list]) => (
            <div key={group} className="neu-card rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[14px] font-semibold text-[#334155]">{group}</h3>
                <span className="neu-chip px-3 py-1 text-[12px] font-semibold text-[#4f46e5]">{list.length}</span>
              </div>
              <div className="grid gap-2">
                {list.map((d) => {
                  const Icon = TYPE_ICON[(d.type || "").toLowerCase()] || FileText;
                  return (
                    <div key={d.id} onClick={() => open(d)}
                      className="flex items-center gap-3 neu-inset rounded-xl px-3 py-2.5 cursor-pointer hover:bg-[#e7eaf1]/40">
                      <span className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#4f46e5] shrink-0"><Icon size={16} /></span>
                      <span className="flex-1 min-w-0 text-[14px] font-semibold text-[#334155] truncate">{d.name}</span>
                      <StatusBadge status={d.status} />
                      <button onClick={(e) => { e.stopPropagation(); remove(d.id); }} className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-rose-500 shrink-0" title="Delete"><Trash2 size={14} /></button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ) : grid ? (
        /* Grid view */
        <div className="grid grid-cols-3 gap-4">
          {visible.map((d) => {
            const Icon = TYPE_ICON[(d.type || "").toLowerCase()] || FileText;
            return (
              <div key={d.id} onClick={() => open(d)} className="neu-card rounded-2xl p-5 cursor-pointer">
                <div className="flex items-center justify-between mb-3">
                  <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center text-[#4f46e5]"><Icon size={20} /></span>
                  <StatusBadge status={d.status} />
                </div>
                <h3 className="text-[15px] font-semibold text-[#334155] truncate">{d.name}</h3>
                <p className="text-[13px] text-[#8792a6] mt-1">{(d.type || "").toUpperCase()} · {d.chunks_count || 0} chunks</p>
                <p className="text-[12px] text-[#9aa6b8] mt-0.5">{fmtDate(d.uploaded_at)}</p>
                <div className="flex items-center gap-2 mt-4" onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => open(d)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#5b6678]" title="View"><Eye size={15} /></button>
                  {d.type === "url" && <button onClick={() => reindex(d.id)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#5b6678]" title="Reindex"><RefreshCw size={15} /></button>}
                  <button onClick={() => remove(d.id)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-rose-500" title="Delete"><Trash2 size={15} /></button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Table */
        <div className="neu-card rounded-2xl overflow-hidden">
          {/* Head */}
          <div className="grid grid-cols-[1fr_120px_150px_150px_130px_140px] items-center px-5 h-14 border-b border-[#e2e6ee] text-[14px] font-semibold text-[#5b6678]">
            <span>Name</span>
            <span>Type</span>
            <span>Chunks</span>
            <span>Updated</span>
            <span>Status</span>
            <span>Actions</span>
          </div>
          {/* Rows */}
          {visible.map((d, i) => {
            const Icon = TYPE_ICON[(d.type || "").toLowerCase()] || FileText;
            return (
              <div
                key={d.id}
                onClick={() => open(d)}
                className={`grid grid-cols-[1fr_120px_150px_150px_130px_140px] items-center px-5 h-[74px] cursor-pointer hover:bg-[#e7eaf1]/50 ${
                  i !== visible.length - 1 ? "border-b border-[#e2e6ee]" : ""
                }`}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <span className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#4f46e5] shrink-0"><Icon size={19} /></span>
                  <span className="text-[15px] font-semibold text-[#334155] truncate">{d.name}</span>
                </span>
                <span className="text-[14px] text-[#8792a6]">{(d.type || "").toUpperCase()}</span>
                <span className="text-[14px] text-[#8792a6]">{d.chunks_count || 0}</span>
                <span className="text-[14px] text-[#8792a6]">{fmtDate(d.uploaded_at)}</span>
                <span><StatusBadge status={d.status} /></span>
                <span className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => open(d)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#5b6678]" title="View"><Eye size={15} /></button>
                  {d.type === "url" && <button onClick={() => reindex(d.id)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#5b6678]" title="Reindex"><RefreshCw size={15} /></button>}
                  <button onClick={() => remove(d.id)} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-rose-500" title="Delete"><Trash2 size={15} /></button>
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer: count + Test Search (replaces mock's static pagination) */}
      {!loading && count > 0 && (
        <div className="flex items-center justify-between mt-6 mb-2">
          <p className="text-[14px] text-[#8792a6]">Showing {count} document{count === 1 ? "" : "s"}</p>
          <button
            onClick={() => { setSearchModal(true); setSearchRes(null); setSearchQ(""); }}
            className="neu-btn-ghost inline-flex items-center gap-1.5 h-10 px-4 text-[14px] font-semibold text-[#4f46e5]"
          >
            <Search size={15} /> Test Search <ArrowRight size={15} />
          </button>
        </div>
      )}

      {/* Document viewer — shows the RAW stored document (works even for
          store-only docs that haven't been chunked yet) */}
      <Modal open={!!viewer} onClose={() => setViewer(null)} title={viewer?.document?.name}
        subtitle={viewer ? `${(viewer.document.type || "").toUpperCase()} · ${viewer.document.status === "active" ? `${viewer.document.chunks_count} chunks` : "Stored (chunked on demand)"}` : ""} icon={FileText} size="xl">
        {viewer && (
          <div className="space-y-4">
            {/* Raw content */}
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-2">Document Content</div>
              {viewer.raw && viewer.raw.trim() ? (
                <div className="neu-inset rounded-xl p-4 max-h-[55vh] overflow-auto">
                  <pre className="text-[12.5px] text-[#334155] whitespace-pre-wrap font-mono leading-relaxed">{viewer.raw}</pre>
                  {viewer.raw_truncated && <p className="text-[11px] text-[#9aa6b8] mt-3">Showing the first 200,000 characters.</p>}
                </div>
              ) : (
                <p className="text-[13px] text-[#9aa6b8] neu-inset rounded-xl p-4">
                  No readable text was extracted from this file (it may be an image-only PDF or binary).
                </p>
              )}
            </div>

            {/* Chunk inspector — only when the doc has been indexed */}
            {(viewer.chunks || []).length > 0 && (
              <details>
                <summary className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-2 cursor-pointer select-none">
                  Chunk Inspector ({viewer.chunks.length})
                </summary>
                <div className="space-y-2 max-h-[40vh] overflow-y-auto mt-2">
                  {viewer.chunks.map((c, i) => (
                    <div key={i} className="neu-inset rounded-xl p-3">
                      <div className="text-[10.5px] text-[#b4bdcc] mb-1">chunk {c.chunk ?? i}</div>
                      <p className="text-[12.5px] text-[#334155] whitespace-pre-wrap line-clamp-6">{c.text}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </Modal>

      {/* Test search */}
      <Modal open={searchModal} onClose={() => setSearchModal(false)} title="Test Search" subtitle="See what document_rag would return" icon={Search} size="lg">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runSearch()}
              placeholder="e.g. what is our Q4 revenue target" className="neu-inset flex-1 h-10 px-3 rounded-xl text-[13.5px] outline-none" />
            <button onClick={runSearch} disabled={searching} className="neu-btn-primary inline-flex items-center gap-2 h-10 px-4 text-[13px] font-semibold">
              {searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Search
            </button>
          </div>
          {searchRes && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {(searchRes.passages || []).length === 0 ? <p className="text-[13px] text-[#9aa6b8]">No matching passages.</p> :
                searchRes.passages.map((p, i) => (
                  <div key={i} className="neu-inset rounded-xl p-3">
                    {p.source && <div className="text-[11px] text-[#4f46e5] font-semibold mb-1">{p.source}</div>}
                    <p className="text-[12.5px] text-[#334155] line-clamp-4">{p.text}</p>
                  </div>
                ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}









