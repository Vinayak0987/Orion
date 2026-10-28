// Agent Templates — mock layout (agent-templates) wired to the real backend.
// Grid of templates from agentApi.templates(); "Use Template" calls
// agentApi.fromTemplate(id) to instantiate a real agent.
import { useEffect, useMemo, useState } from "react";
import {
  Search,
  ChevronDown,
  Headphones,
  Megaphone,
  ChartColumnIncreasing,
  Settings,
  IdCard,
  MessagesSquare,
  ShoppingBag,
  Bot,
  Loader2,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";

// Map a template (by id or category) to a mock icon + tint.
const ICON_BY_ID = {
  "tpl-marketing": { icon: <Megaphone size={24} strokeWidth={2} />, cls: "tpl-ic-red" },
  "tpl-finance": { icon: <ChartColumnIncreasing size={24} strokeWidth={2} />, cls: "tpl-ic-green" },
  "tpl-operations": { icon: <Settings size={24} strokeWidth={2} />, cls: "tpl-ic-purple" },
  "tpl-hr": { icon: <IdCard size={24} strokeWidth={2} />, cls: "tpl-ic-orange" },
  "tpl-support": { icon: <MessagesSquare size={24} strokeWidth={2} />, cls: "tpl-ic-indigo" },
  "tpl-sales": { icon: <ShoppingBag size={24} strokeWidth={2} />, cls: "tpl-ic-blue" },
  "tpl-research": { icon: <Headphones size={24} strokeWidth={2} />, cls: "tpl-ic-indigo" },
};
const iconFor = (t) => ICON_BY_ID[t.id] || { icon: <Bot size={24} strokeWidth={2} />, cls: "tpl-ic-indigo" };

export const ViewAgentTemplates = ({ onCreated }) => {
  const toast = useToast();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [activeCat, setActiveCat] = useState("All");
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    agentApi
      .templates()
      .then((d) => setTemplates(d.templates || []))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const categories = useMemo(() => {
    const set = new Set(["All"]);
    templates.forEach((t) => t.category && set.add(t.category));
    return [...set];
  }, [templates]);

  const featured = useMemo(() => templates.find((t) => t.is_featured) || templates[0], [templates]);

  const grid = useMemo(
    () =>
      templates.filter((t) => {
        if (activeCat !== "All" && t.category !== activeCat) return false;
        if (q && !(`${t.name} ${t.description}`.toLowerCase().includes(q.toLowerCase()))) return false;
        return true;
      }),
    [templates, activeCat, q]
  );

  const useTemplate = async (t) => {
    setBusyId(t.id);
    try {
      const r = await agentApi.fromTemplate(t.id);
      toast.success(`Created '${r.agent?.name || t.name}' from template`);
      onCreated?.(r.agent_id);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="agent-templates">
      {/* Header */}
      <div className="tpl-head">
        <h1>Agent Templates</h1>
        <p>Start with a pre-built agent and customize it.</p>
      </div>

      {/* Search + category dropdown */}
      <div className="tpl-searchrow">
        <div className="tpl-search">
          <Search size={19} strokeWidth={2} className="tpl-search-icon" />
          <input placeholder="Search templates..." value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <button className="tpl-catselect" onClick={() => setActiveCat("All")}>
          All Categories <ChevronDown size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Category chips */}
      <div className="tpl-chips">
        {categories.map((c) => (
          <button key={c} className={`tpl-chip ${activeCat === c ? "active" : ""}`} onClick={() => setActiveCat(c)}>
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: "grid", placeItems: "center", padding: "80px 0", color: "#a1a9b5" }}>
          <Loader2 className="animate-spin" />
        </div>
      ) : (
        <>
          {/* Featured Template */}
          {featured && (
            <div className="tpl-featured-wrap">
              <h2 className="tpl-featured-title">Featured Template</h2>
              <div className="tpl-featured card">
                <div className="tpl-featured-left">
                  <div className="tpl-featured-head">
                    <div className="tpl-featured-icon">
                      <Headphones size={30} strokeWidth={2} />
                    </div>
                    <h3>{featured.name}</h3>
                  </div>
                  <p className="tpl-featured-desc">{featured.description}</p>
                  <div className="tpl-tags">
                    {(featured.tags || []).map((t) => (
                      <span key={t} className="tpl-tag">{t}</span>
                    ))}
                  </div>
                  <div className="tpl-featured-actions">
                    <button className="tpl-btn-primary" onClick={() => useTemplate(featured)} disabled={busyId === featured.id}>
                      {busyId === featured.id ? "Creating…" : "Use Template"}
                    </button>
                  </div>
                </div>
                <div className="tpl-featured-art" aria-hidden="true">
                  <span className="tpl-blob tpl-blob-1" />
                  <span className="tpl-blob tpl-blob-2" />
                  <span className="tpl-blob tpl-blob-3" />
                  <span className="tpl-blob tpl-blob-4" />
                  <span className="tpl-art-ic tpl-art-chip"><Bot size={20} strokeWidth={2} /></span>
                </div>
              </div>
            </div>
          )}

          {/* Template grid */}
          <div className="tpl-grid">
            {grid.map((t) => {
              const { icon, cls } = iconFor(t);
              return (
                <div key={t.id} className="tpl-card card">
                  <div className={`tpl-card-icon ${cls}`}>{icon}</div>
                  <h3 className="tpl-card-name">{t.name}</h3>
                  <p className="tpl-card-desc">{t.description}</p>
                  <div className="tpl-tags">
                    {(t.tags || []).map((tag) => (
                      <span key={tag} className="tpl-tag">{tag}</span>
                    ))}
                  </div>
                  <button className="tpl-btn-primary tpl-card-btn" onClick={() => useTemplate(t)} disabled={busyId === t.id}>
                    {busyId === t.id ? "Creating…" : "Use Template"}
                  </button>
                </div>
              );
            })}
            {grid.length === 0 && (
              <div style={{ gridColumn: "1 / -1", textAlign: "center", padding: 40, color: "#a1a9b5" }}>
                No templates match your filters.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ViewAgentTemplates;
