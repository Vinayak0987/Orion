// Knowledge · Memory Details (ViewMemoryDetails.jsx)
// Mock layout (breadcrumb + icon header + "Selected Memory" detail card),
// re-skinned neumorphic. Inspects a single memory entry passed via props from
// the Overview; deletes via knowledgeApi.deleteMemory.
//   props: entry, agentName, onBack, onDeleted
import { ArrowLeft, Trash2, FileText, Clock, Calendar, Brain } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";
import { knowledgeApi } from "../../knowledgeApi.js";
import { useToast } from "../ui/Toast.jsx";

const fmt = (iso, withTime = false) =>
  iso ? new Date(iso).toLocaleString(undefined, withTime
    ? { month: "short", day: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" }
    : { month: "short", day: "2-digit", year: "numeric" }) : "—";

export function ViewMemoryDetails({ entry, agentName, onBack, onDeleted }) {
  const toast = useToast();

  const del = async () => {
    try { await knowledgeApi.deleteMemory(entry.id); toast.success("Memory deleted"); onDeleted?.(); }
    catch (e) { toast.error(e.message); }
  };

  const tags = entry?.tags || entry?.metadata?.tags || [];

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-6 sm:px-7 sm:py-7">
      <DirectoryLocation items={[{ label: "Knowledge & Memory", onClick: onBack }, { label: "Memory Details" }]} />

      {/* Header */}
      <div className="flex items-start gap-4 mb-5">
        <span className="neu-circle w-11 h-11 rounded-xl text-[#4f46e5] grid place-items-center shrink-0">
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="3" width="16" height="18" rx="2.5"/><path d="M9 3v18" strokeLinecap="round"/><circle cx="14.5" cy="12" r="2.2"/></svg>
        </span>
        <div className="flex-1 pt-0.5">
          <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">Memory Details</h1>
          <p className="text-[13px] text-[#8792a6] mt-1">View and delete a specific memory</p>
        </div>
        <button onClick={onBack} className="neu-btn-ghost h-12 px-5 text-[15px] font-semibold text-[#5b6678] flex items-center gap-2">
          <ArrowLeft size={18} /> Back
        </button>
      </div>

      {/* Selected Memory */}
      <h2 className="text-[15px] font-semibold text-[#334155] mb-4">Selected Memory</h2>

      {!entry ? (
        <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">Open a memory entry from the Overview to inspect it.</div>
      ) : (
        <div className="neu-card rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <span className="neu-circle w-14 h-14 rounded-2xl text-violet-600 grid place-items-center shrink-0"><Brain size={24} /></span>
            <div className="flex-1 min-w-0">
              <h3 className="text-[15px] font-semibold text-[#334155]">{agentName || entry.agent_id}</h3>
              <p className="text-[14px] mt-1 flex items-center gap-2 flex-wrap">
                <span className="text-[#4f46e5] font-medium">episodic memory</span>
                <span className="text-[#c7d2fe]">•</span>
                <span className="text-[#8792a6]">{fmt(entry.created_at, true)}</span>
              </p>
            </div>
            <button onClick={del} className="neu-btn-danger inline-flex items-center gap-1.5 h-11 px-5 text-[14px] font-semibold text-rose-500">
              <Trash2 size={16} /> Delete
            </button>
          </div>

          <div className="neu-inset rounded-xl p-4 mt-5">
            <p className="text-[15px] text-[#334155] leading-relaxed whitespace-pre-wrap">{entry.content}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-5 text-[13px] text-[#8792a6]">
            <div className="flex items-center gap-2"><Clock size={15} /> Created {fmt(entry.created_at, true)}</div>
            <div className="flex items-center gap-2"><Calendar size={15} /> Expires {fmt(entry.expires_at)}</div>
          </div>

          {tags.length > 0 && (
            <div className="flex items-center gap-3 mt-5 pt-5 border-t border-[#e2e6ee] flex-wrap">
              <span className="text-[14px] font-semibold text-[#334155] flex items-center gap-1.5"><FileText size={15} /> Tags</span>
              {tags.map((t) => (
                <span key={t} className="neu-chip px-3.5 py-1.5 text-[13px] font-medium text-[#4f46e5]">{t}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}





