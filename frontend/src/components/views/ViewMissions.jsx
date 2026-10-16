import { useCallback, useEffect, useState } from "react";
import { Plus, Search, RefreshCw, ChevronRight } from "lucide-react";

import { missionApi } from "../../missionApi";

const STATUS_STYLES = {
  planning: "text-amber-600 bg-amber-50",
  running: "text-blue-600 bg-blue-50",
  completed: "text-emerald-600 bg-emerald-50",
  partial: "text-amber-600 bg-amber-50",
  failed: "text-rose-600 bg-rose-50",
};

function timeAgo(iso) {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export const ViewMissions = ({ onViewDetails }) => {
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    missionApi
      .missions(50)
      .then((d) => {
        setMissions(d.missions);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = missions.filter(
    (m) =>
      !query ||
      (m.title || m.prompt).toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="p-6 sm:p-7 max-w-[1400px] mx-auto h-full flex flex-col bg-[#f8fafc]">
      <div className="flex justify-between items-start mb-6 shrink-0">
        <div>
          <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220] mb-2">
            Missions
          </h1>
          <p className="text-[15px] text-[#64748b]">
            Every goal Orion has worked on. Click one to see the full run.
          </p>
        </div>
        <button
          onClick={load}
          className="bg-white border border-[#e6ebf2] text-slate-700 font-semibold h-11 px-4 rounded-xl text-sm flex items-center gap-2 hover:bg-slate-50"
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      <div className="flex items-center gap-3 mb-4 shrink-0">
        <div className="relative w-72">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search missions…"
            className="w-full bg-white border border-[#e6ebf2] rounded-lg py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:border-[#a5b4fc] shadow-sm"
          />
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 text-sm">
          {error}
          <span className="block text-rose-400 text-xs mt-1">
            Start the mission backend on port 8081.
          </span>
        </div>
      )}

      <div className="flex-1 overflow-auto bg-white rounded-2xl border border-[#e6ebf2] shadow-sm">
        {loading ? (
          <div className="p-10 text-center text-slate-400 text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-slate-400 text-sm">
            No missions yet. Go to Command Center to start your first mission.
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#e6ebf2]">
                <th className="py-3 px-4 text-sm font-semibold text-slate-500">Mission</th>
                <th className="py-3 px-4 text-sm font-semibold text-slate-500">Tasks</th>
                <th className="py-3 px-4 text-sm font-semibold text-slate-500">Agents</th>
                <th className="py-3 px-4 text-sm font-semibold text-slate-500">Status</th>
                <th className="py-3 px-4 text-sm font-semibold text-slate-500 text-right">
                  Created
                </th>
                <th className="py-3 px-4 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eef2f8]">
              {filtered.map((m) => (
                <tr
                  key={m.id}
                  onClick={() => onViewDetails?.(m.id)}
                  className="group cursor-pointer hover:bg-slate-50 transition-colors"
                >
                  <td className="py-4 px-4">
                    <h4 className="text-sm font-bold text-slate-800">
                      {m.title || m.prompt}
                    </h4>
                    <p className="text-xs mt-0.5 text-slate-400 truncate max-w-md">
                      {m.prompt}
                    </p>
                  </td>
                  <td className="py-4 px-4 text-sm text-slate-600">{m.task_count}</td>
                  <td className="py-4 px-4 text-sm text-slate-600">{m.agent_count}</td>
                  <td className="py-4 px-4">
                    <span
                      className={`inline-block px-3 py-1 rounded-lg text-xs font-semibold ${
                        STATUS_STYLES[m.status] || "text-slate-500 bg-slate-100"
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-right text-sm text-slate-400 whitespace-nowrap">
                    {timeAgo(m.created_at)}
                  </td>
                  <td className="py-4 px-4 text-slate-300 group-hover:text-slate-500">
                    <ChevronRight size={18} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
