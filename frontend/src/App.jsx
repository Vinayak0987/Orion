// MABGP / Orion frontend (F47-F52 + three-layer operating interface).
//
// Hash-based routing: #/generate, #/business, #/work, #/activity, #/loops.
// No router package — hand-rolled from window.location.hash + useState.

import { useCallback, useEffect, useRef, useState } from "react";

import { api, streamGeneration } from "./api";
import HistoryList from "./components/HistoryList";
import ProgressPanel from "./components/ProgressPanel";
import PromptForm from "./components/PromptForm";
import ReportView from "./components/ReportView";
import { ErrorState, HealthBanner } from "./components/Status";
import ActivityView from "./views/ActivityView";
import BusinessView from "./views/BusinessView";
import LoopsView from "./views/LoopsView";
import PlanView, { takePlanningHandoff } from "./views/PlanView";
import WorkView from "./views/WorkView";

// ============================================================================
// Hash routing
// ============================================================================

const ROUTES = ["plan", "generate", "business", "work", "activity", "loops"];

function getRoute() {
  const hash = window.location.hash.replace("#/", "").split("?")[0];
  return ROUTES.includes(hash) ? hash : "generate";
}

function Nav({ route, onChange }) {
  return (
    <nav className="main-nav" aria-label="Main navigation">
      {ROUTES.map((r) => (
        <a
          key={r}
          href={`#/${r}`}
          className={`nav-link${route === r ? " nav-active" : ""}`}
          onClick={(e) => { e.preventDefault(); onChange(r); }}
          aria-current={route === r ? "page" : undefined}
        >
          {r.charAt(0).toUpperCase() + r.slice(1)}
        </a>
      ))}
    </nav>
  );
}

// ============================================================================
// Generation layer (existing F47-F52, unchanged logic)
// ============================================================================

function GenerateView() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const [catalogue, setCatalogue] = useState([]);

  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [summary, setSummary] = useState(null);
  const [failure, setFailure] = useState(null);
  const [forceAll, setForceAll] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  const cancelRef = useRef(null);
  const lastPromptRef = useRef("");
  const timerRef = useRef(null);

  useEffect(() => {
    api.health().then(setHealth).catch((error) => setHealthError(error.message));
    api.sectionCatalogue()
      .then((body) => setCatalogue(body.sections))
      .catch(() => setCatalogue([]));
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      setSessions(await api.sessions());
    } catch (error) {
      setHistoryError(error.message);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  // A confirmed planning report hands off here: PlanView stored the
  // confirmed report + prompt, and the run starts immediately carrying
  // planning_report_id (design.md §4 step 5).
  useEffect(() => {
    const handoff = takePlanningHandoff();
    if (handoff?.prompt) {
      // Pass forceAll explicitly: the generate closure still holds the
      // pre-handoff state at this point.
      setForceAll(Boolean(handoff.forceAll));
      generate(handoff.prompt, handoff.planningReportId ?? null, Boolean(handoff.forceAll));
    }
    // Runs once per mount, straight after a confirm hand-off.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!running) { clearInterval(timerRef.current); return undefined; }
    const startedAt = Date.now();
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 100);
    return () => clearInterval(timerRef.current);
  }, [running]);

  const generate = useCallback((prompt, planningReportId = null, forceAllOverride = null) => {
    const effectiveForceAll = forceAllOverride ?? forceAll;
    lastPromptRef.current = prompt;
    setRunning(true); setEvents([]); setSummary(null); setFailure(null);
    cancelRef.current = streamGeneration({
      prompt, forceAllDepartments: effectiveForceAll, planningReportId,
      onEvent: (event) => setEvents((c) => [...c, event]),
      onResult: (result) => { setSummary(result); setRunning(false); loadHistory(); },
      onError: (detail, kind) => { setFailure({ detail, kind }); setRunning(false); loadHistory(); },
    });
  }, [forceAll, loadHistory]);

  useEffect(() => () => cancelRef.current?.(), []);

  async function openSession(sessionId) {
    setFailure(null);
    try {
      const record = await api.session(sessionId);
      setSummary({
        session_id: record.id, status: record.status,
        completeness_score: record.completeness_score,
        total_duration_ms: record.total_duration_ms,
        total_tokens: record.total_tokens,
        intent: record.intent ?? {}, plan: record.plan ?? {},
        routing: { active_departments: record.active_departments ?? [], skipped_departments: record.skipped_departments ?? [] },
        validation_warnings: record.metadata?.validation_warnings ?? [], errors: [],
      });
      setEvents([]);
    } catch (error) { setFailure({ detail: error.message, kind: "generation" }); }
  }

  async function deleteSession(sessionId) {
    try {
      await api.deleteSession(sessionId);
      if (summary?.session_id === sessionId) setSummary(null);
      loadHistory();
    } catch (error) { setHistoryError(error.message); }
  }

  const hasPartialPlan = summary?.plan && Object.keys(summary.plan).length > 0;

  return (
    <>
      <HealthBanner health={health} error={healthError} />
      <div className="layout">
        <main className="main">
          <PromptForm onGenerate={generate} running={running} forceAll={forceAll} onForceAllChange={setForceAll} />
          {running && <ProgressPanel events={events} elapsedSeconds={elapsed} skipped={events.find((e) => e.event === "routing_resolved")?.detail?.includes("skipped") ? ["operations"] : []} />}
          {failure && <ErrorState message={failure.detail} kind={failure.kind} partial={hasPartialPlan} onRetry={() => generate(lastPromptRef.current)} />}
          {summary && catalogue.length > 0 && <ReportView summary={summary} catalogue={catalogue} />}
          {summary && !hasPartialPlan && (
            <div className="callout callout-warn"><strong>No department output was stored for this run.</strong><p className="hint">Status was "{summary.status}". Check the backend logs.</p></div>
          )}
          {!running && !summary && !failure && (
            <div className="panel empty"><p>Describe a business above and MABGP will produce a strategy, financial model, brand, marketing plan and operations playbook.</p><p className="hint">Physical businesses run all five departments. Digital ones skip Operations automatically.</p></div>
          )}
        </main>
        <HistoryList sessions={sessions} activeId={summary?.session_id} loading={historyLoading} error={historyError} onOpen={openSession} onDelete={deleteSession} onRefresh={loadHistory} />
      </div>
    </>
  );
}

// ============================================================================
// App shell
// ============================================================================

export default function App() {
  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    function onHashChange() { setRoute(getRoute()); }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = useCallback((r) => {
    window.location.hash = `#/${r}`;
    setRoute(r);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Orion</h1>
          <p className="subtitle">AI Business Operating System</p>
        </div>
        <Nav route={route} onChange={navigate} />
        <span className="meta">{api.base}</span>
      </header>

      {route === "plan" && <PlanView />}
      {route === "generate" && <GenerateView />}
      {route === "business" && <BusinessView />}
      {route === "work" && <WorkView />}
      {route === "activity" && <ActivityView />}
      {route === "loops" && <LoopsView />}

      <footer className="footer meta">
        Research prototype. Generated figures are model estimates, not financial advice.
      </footer>
    </div>
  );
}
