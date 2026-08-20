// ActivityView - Layer 3: what did that loop do at 14:32?

import { useCallback, useState } from "react";
import { api } from "../api";
import usePolling from "../hooks/usePolling";
import CompanySelector, { DEFAULT_COMPANY } from "../operating/CompanySelector";
import LedgerTail from "../operating/LedgerTail";
import MemoryInspector from "../operating/MemoryInspector";
import RunLog from "../operating/RunLog";

export default function ActivityView() {
  const [companyId, setCompanyId] = useState(DEFAULT_COMPANY);

  const { data: runs } = usePolling(
    useCallback(() => api.operating.runs(companyId, null, 50), [companyId]), 3000);
  const { data: ledger } = usePolling(
    useCallback(() => api.operating.ledger(companyId, 50), [companyId]), 3000);

  return (
    <div className="view activity-view">
      <h2>Activity View</h2>
      <p className="view-subtitle">Debugging: what exactly happened?</p>

      <CompanySelector companyId={companyId} onChange={setCompanyId} />

      <RunLog runs={runs} />
      <LedgerTail entries={ledger} />
      <MemoryInspector companyId={companyId} />
    </div>
  );
}
