// WorkView - Layer 2: what needs a decision?

import { useCallback, useState } from "react";
import { api } from "../api";
import usePolling from "../hooks/usePolling";
import CadenceStatus from "../operating/CadenceStatus";
import CompanySelector, { DEFAULT_COMPANY } from "../operating/CompanySelector";
import ConstitutionPanel from "../operating/ConstitutionPanel";
import DecisionHistory from "../operating/DecisionHistory";
import ReviewQueue from "../operating/ReviewQueue";

export default function WorkView() {
  const [companyId, setCompanyId] = useState(DEFAULT_COMPANY);

  const { data: pending, refetch: refetchPending } = usePolling(
    useCallback(() => api.operating.decisions(companyId, "pending_review"), [companyId]), 5000);
  const { data: allDecisions, refetch: refetchAll } = usePolling(
    useCallback(() => api.operating.decisions(companyId), [companyId]), 10000);
  const { data: constitution } = usePolling(
    useCallback(() => api.operating.constitution(), []), 60000);
  const { data: schedule } = usePolling(
    useCallback(() => api.operating.schedule(companyId), [companyId]), 10000);

  const handleAction = useCallback(async (decisionId, action, by, reason) => {
    if (action === "approve") {
      await api.operating.approve(decisionId, by);
    } else if (action === "reject") {
      await api.operating.reject(decisionId, by, reason);
    } else if (action === "return") {
      await api.operating.returnDecision(decisionId, by, reason);
    }
    refetchPending();
    refetchAll();
  }, [refetchPending, refetchAll]);

  return (
    <div className="view work-view">
      <h2>Work View</h2>
      <p className="view-subtitle">What is happening and what needs a decision?</p>

      <CompanySelector companyId={companyId} onChange={setCompanyId} />

      <ReviewQueue decisions={pending} onAction={handleAction} />
      <DecisionHistory decisions={allDecisions} />
      <ConstitutionPanel rules={constitution} />
      <CadenceStatus schedule={schedule} />
    </div>
  );
}
