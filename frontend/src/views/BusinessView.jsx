// BusinessView - Layer 1: is the company healthy?

import { useCallback, useState } from "react";
import { api } from "../api";
import usePolling from "../hooks/usePolling";
import AnchorBoard from "../operating/AnchorBoard";
import AnchorTrend from "../operating/AnchorTrend";
import CompanySelector, { DEFAULT_COMPANY } from "../operating/CompanySelector";
import DepartmentStrip from "../operating/DepartmentStrip";
import FindingsList from "../operating/FindingsList";

export default function BusinessView() {
  const [companyId, setCompanyId] = useState(DEFAULT_COMPANY);

  const { data: anchorData, error: anchorErr } = usePolling(
    useCallback(() => api.operating.anchors(companyId), [companyId]), 5000);
  const { data: historyData } = usePolling(
    useCallback(() => api.operating.anchorHistory(companyId, 20), [companyId]), 10000);
  const { data: findings } = usePolling(
    useCallback(() => api.operating.findings(companyId), [companyId]), 5000);
  const { data: departments } = usePolling(
    useCallback(() => api.operating.departments(), []), 30000);
  const { data: schedule } = usePolling(
    useCallback(() => api.operating.schedule(companyId), [companyId]), 10000);

  const noData = anchorData && anchorData.entry_count === 0;

  return (
    <div className="view business-view">
      <h2>Business View</h2>
      <p className="view-subtitle">
        How is the company doing? Every number below is computed from the ledger — no agent can write one.
      </p>

      <CompanySelector companyId={companyId} onChange={setCompanyId} />

      {anchorErr && <div className="error-msg">Cannot reach the backend: {anchorErr}</div>}

      {noData && (
        <div className="callout callout-info">
          <strong>No data yet for "{companyId}".</strong>
          <p>Run the autonomy demo to seed this company:</p>
          <pre style={{ fontSize: 12, margin: "6px 0 0" }}>
            python -m scripts.autonomy_demo --days 90
          </pre>
          <p className="hint">
            Or use the <strong>Manual Tick</strong> button above to advance one step at a time.
          </p>
        </div>
      )}

      {!noData && (
        <>
          <AnchorBoard anchors={anchorData?.anchors} />

          <AnchorTrend
            series={historyData?.series}
            anchorName="net_margin_pct"
            proxyName="customers_acquired"
          />

          <FindingsList findings={findings} />

          <DepartmentStrip departments={departments} schedule={schedule} />
        </>
      )}
    </div>
  );
}
