// ReviewQueue - pending decisions, approve/reject/return with named human.
// Makes clear that approval does NOT unlock a hard constraint.

import { useCallback, useState } from "react";

export default function ReviewQueue({ decisions, onAction }) {
  if (!decisions || decisions.length === 0) {
    return <div className="panel empty">No decisions awaiting review.</div>;
  }

  return (
    <div className="review-queue">
      <h3>Review Queue</h3>
      <p className="review-note">
        ⚠️ Approving a decision does <strong>not</strong> unlock a hard constraint.
        If the action violates the Constitution it will still be blocked at execution.
      </p>
      <div className="review-list">
        {decisions.map((d) => (
          <ReviewCard key={d.id} decision={d} onAction={onAction} />
        ))}
      </div>
    </div>
  );
}

function ReviewCard({ decision, onAction }) {
  const [name, setName] = useState("");
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);

  const isIrreversible = decision.risk === "irreversible";
  const amount = decision.amount_minor ? `₹${(decision.amount_minor / 100).toLocaleString("en-IN")}` : "";

  const handleAction = useCallback(async (action) => {
    if (isIrreversible && action === "approve" && confirming !== "approve") {
      setConfirming("approve");
      return;
    }
    if (!name.trim()) return;
    setBusy(true);
    try {
      await onAction(decision.id, action, name.trim(), reason.trim());
    } finally {
      setBusy(false);
      setConfirming(null);
    }
  }, [decision.id, name, reason, onAction, isIrreversible, confirming]);

  return (
    <div className={`review-card review-risk-${decision.risk}`}>
      <div className="review-header">
        <span className="review-dept">{decision.department}</span>
        <span className={`review-risk risk-${decision.risk}`}>{decision.risk}</span>
        {amount && <span className="review-amount">{amount}</span>}
      </div>
      <p className="review-description">{decision.description || decision.action_kind}</p>
      <p className="review-reason">{decision.reason}</p>

      <div className="review-controls">
        <input
          type="text"
          placeholder="Your name (required)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="review-name-input"
          aria-label="Reviewer name"
          required
        />
        <input
          type="text"
          placeholder="Reason (for reject/return)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="review-reason-input"
          aria-label="Review reason"
        />
        <div className="review-actions">
          {confirming === "approve" && (
            <span className="review-confirm-warn">This is irreversible. Click again to confirm.</span>
          )}
          <button
            onClick={() => handleAction("approve")}
            disabled={busy || !name.trim()}
            className="btn btn-ok"
          >
            {confirming === "approve" ? "Confirm Approve" : "Approve"}
          </button>
          <button
            onClick={() => handleAction("reject")}
            disabled={busy || !name.trim()}
            className="btn btn-bad"
          >
            Reject
          </button>
          <button
            onClick={() => handleAction("return")}
            disabled={busy || !name.trim() || !reason.trim()}
            className="btn btn-muted"
          >
            Return
          </button>
        </div>
      </div>
    </div>
  );
}
