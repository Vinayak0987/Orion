import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleDot,
  Clock,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

import { missionApi } from "../../missionApi";

const TABS = ["Overview", "Tasks", "Results"];

const STATUS = {
  pending: { Icon: Clock, cls: "text-slate-400 bg-slate-50" },
  running: { Icon: CircleDot, cls: "text-blue-500 bg-blue-50" },
  completed: { Icon: CheckCircle2, cls: "text-emerald-500 bg-emerald-50" },
  failed: { Icon: AlertCircle, cls: "text-rose-500 bg-rose-50" },
};

export const ViewMissionDetails = ({ missionId, onBack }) => {
  const [mission, setMission] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("Overview");

  const load = useCallback(() => {
    if (!missionId) return;
    missionApi
      .mission(missionId)
      .then(setMission)
      .catch((e) => setError(e.message));
  }, [missionId]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while running.
  useEffect(() => {
    if (!mission || ["completed", "failed", "partial"].includes(mission.status)) return;
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [mission, load]);

  if (error) {
    return (
      <div className="p-7 max-w-[1400px] mx-auto">
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-slate-600 mb-4">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="rounded-xl bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!mission) {
    return <div className="p-10 text-center text-slate-400 text-sm">Loading…</div>;
  }

  const tasks = mission.tasks || [];

  return (
    <div className="h-full flex flex-col p-6 sm:p-7 max-w-[1400px] mx-auto bg-[#f8fafc]">
      <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-900 mb-4">
        <ArrowLeft size={16} /> Back to Missions
      </button>

      <div className="flex justify-between items-start mb-5 shrink-0">
        <div>
          <h1 className="text-[28px] leading-tight font-extrabold tracking-[-0.4px] text-[#0b1220]">
            {mission.title || mission.prompt}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">{mission.prompt}</p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1.5 rounded-full text-xs font-semibold ${
              STATUS[mission.status]?.cls || "text-slate-500 bg-slate-100"
            }`}
          >
            {mission.status}
          </span>
          <button onClick={load} className="w-10 h-10 rounded-xl border border-[#e6ebf2] grid place-items-center text-slate-500 hover:bg-slate-50">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-5 shrink-0">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 rounded-xl text-sm font-semibold ${
              tab === t
                ? "bg-white border border-[#e6ebf2] text-slate-800 shadow-sm"
                : "text-slate-500 hover:bg-slate-100"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {(tab === "Overview" || tab === "Tasks") && (
          <div className="space-y-3">
            {tasks.map((t) => {
              const s = STATUS[t.status] || STATUS.pending;
              return (
                <div
                  key={t.id}
                  className="bg-white rounded-2xl border border-[#e6ebf2] shadow-sm p-4"
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-9 h-9 rounded-xl grid place-items-center ${s.cls}`}>
                      <s.Icon size={18} strokeWidth={2.2} />
                    </span>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-slate-800">{t.title}</h4>
                      <p className="text-xs text-slate-400">
                        {t.agent_type}
                        {t.depends_on?.length ? ` · depends on: ${t.depends_on.join(", ")}` : ""}
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">{t.status}</span>
                  </div>
                  {t.result?.summary && (
                    <p className="mt-3 text-sm text-slate-600 pl-12">{t.result.summary}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "Results" && (
          <div className="space-y-4">
            {tasks
              .filter((t) => t.result?.data)
              .map((t) => (
                <div
                  key={t.id}
                  className="bg-white rounded-2xl border border-[#e6ebf2] shadow-sm p-5"
                >
                  <h4 className="text-sm font-bold text-slate-800 mb-2">{t.title}</h4>
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">
                    {t.result.data}
                  </p>
                </div>
              ))}
            {tasks.every((t) => !t.result?.data) && (
              <div className="p-10 text-center text-slate-400 text-sm">
                No results yet.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
