// PlanView - the pre-execution Planning Report flow (design.md §9).
//
// Operator flow (§4): submit a prompt -> a report is built and persisted
// (at most one LLM call) -> review intent, agents, estimates, blockers ->
// confirm (free) -> hand off to #/generate, which runs carrying
// planning_report_id.
//
// The pending hand-off travels via sessionStorage: PlanView confirms, stores
// {prompt, forceAll, planningReportId}, and navigates to #/generate, where
// GenerateView picks it up and starts streaming immediately.

import { useCallback, useState } from "react";

import { api } from "../api";
import AgentRoster from "./plan/AgentRoster";
import ConfirmBar from "./plan/ConfirmBar";
import EstimatesPanel from "./plan/EstimatesPanel";
import InferencesPanel from "./plan/InferencesPanel";
import PlanForm from "./plan/PlanForm";
import ReadinessBanner from "./plan/ReadinessBanner";

export const PLANNING_HANDOFF_KEY = "orion.planning.handoff";

export function takePlanningHandoff() {
  try {
    const raw = sessionStorage.getItem(PLANNING_HANDOFF_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(PLANNING_HANDOFF_KEY);
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default function PlanView() {
  const [building, setBuilding] = useState(false);
  const [buildError, setBuildError] = useState("");
  const [report, setReport] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState("");

  const build = useCallback(async (prompt, forceAll) => {
    setBuilding(true);
    setBuildError("");
    setReport(null);
    setConfirmError("");
    try {
      setReport(await api.planning.createReport(prompt, forceAll));
    } catch (error) {
      setBuildError(error.message);
    } finally {
      setBuilding(false);
    }
  }, []);

  const confirm = useCallback(async () => {
    if (!report) return;
    setConfirming(true);
    setConfirmError("");
    try {
      const confirmed = await api.planning.confirm(report.id);
      // dynamic_routing === false means the report planned every department
      // (force-all arm); the run must match the report it executes.
      const forceAll = confirmed.routing?.dynamic_routing === false;
      sessionStorage.setItem(
        PLANNING_HANDOFF_KEY,
        JSON.stringify({
          prompt: confirmed.prompt,
          forceAll,
          planningReportId: confirmed.id,
        }),
      );
      window.location.hash = "#/generate";
    } catch (error) {
      setConfirmError(error.message);
      // The report may have expired between build and confirm - refresh it.
      try {
        setReport(await api.planning.report(report.id));
      } catch {
        /* the build error surface already owns unreachable-backend states */
      }
      setConfirming(false);
    }
  }, [report]);

  return (
    <div className="view plan-view">
      <h2>Plan</h2>
      <p className="view-subtitle">
        See what will run, in what order, on which providers — before anything
        spends quota.
      </p>

      <PlanForm onSubmit={build} building={building} />
      {buildError && (
        <div className="callout callout-bad" role="alert">
          <strong>Could not build the report.</strong>
          <p>{buildError}</p>
        </div>
      )}

      {report && (
        <>
          <ReadinessBanner report={report} />
          {(report.warnings ?? []).length > 0 && (
            <div className="callout callout-warn">
              <strong>Warnings</strong>
              <ul className="bullets">
                {report.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          <InferencesPanel report={report} />
          <AgentRoster report={report} />
          <EstimatesPanel report={report} />
          <ConfirmBar
            report={report}
            confirming={confirming}
            onConfirm={confirm}
            error={confirmError}
          />
        </>
      )}

      {!building && !report && !buildError && (
        <div className="panel empty">
          <p>
            Build a planning report to inspect the intent, the exact agent
            roster, cost estimates and readiness before running the pipeline.
          </p>
          <p className="hint">
            Physical businesses run all 21 agents. Digital ones run 17 and skip
            Operations automatically.
          </p>
        </div>
      )}
    </div>
  );
}
