// AnchorBoard - the 19 anchors grouped by category.
// Each shows value, unit, entry count, and thin-evidence marking.
// A null value means "not computable", never zero.

import { useMemo } from "react";

const GROUPS = {
  money: ["revenue", "cogs", "opex", "marketing_spend", "capex",
          "cash_balance", "gross_profit", "net_profit"],
  margins: ["gross_margin_pct", "net_margin_pct"],
  customers: ["customers_acquired", "customers_churned", "customers_active",
              "churn_pct", "retention_pct"],
  unit_economics: ["cac", "arpc"],
  delivery: ["sla_breaches", "tasks_completed"],
};

function formatValue(value, unit) {
  if (value === null || value === undefined) return null;
  if (unit === "INR") return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  if (unit === "%") return `${value.toFixed(2)}%`;
  return value.toLocaleString();
}

function AnchorCard({ anchor }) {
  const display = formatValue(anchor.value, anchor.unit);
  const isThin = anchor.thin;
  const isNull = anchor.value === null || anchor.value === undefined;

  return (
    <div className={`anchor-card${isThin ? " anchor-thin" : ""}${isNull ? " anchor-null" : ""}`}>
      <div className="anchor-header">
        <span className="anchor-lock" aria-label="computed anchor" title="Computed from the ledger — no agent can write this">🔒</span>
        <span className="anchor-name">{anchor.name.replace(/_/g, " ")}</span>
      </div>
      {isNull ? (
        <div className="anchor-value anchor-not-measurable">not yet measurable</div>
      ) : (
        <div className="anchor-value">{display}</div>
      )}
      <div className="anchor-meta">
        <span className="anchor-entries">from {anchor.entries} {anchor.entries === 1 ? "entry" : "entries"}</span>
        {isThin && <span className="anchor-thin-badge" title="Fewer than 5 contributing entries">thin evidence</span>}
      </div>
      {anchor.note && <div className="anchor-note">{anchor.note}</div>}
    </div>
  );
}

export default function AnchorBoard({ anchors }) {
  const grouped = useMemo(() => {
    if (!anchors) return {};
    const out = {};
    for (const [group, names] of Object.entries(GROUPS)) {
      out[group] = names
        .map((name) => anchors[name])
        .filter(Boolean);
    }
    return out;
  }, [anchors]);

  if (!anchors || Object.keys(anchors).length === 0) {
    return <div className="panel empty">No anchor data. The company has no ledger entries yet.</div>;
  }

  return (
    <div className="anchor-board">
      {Object.entries(grouped).map(([group, items]) => (
        <div key={group} className="anchor-group">
          <h3 className="anchor-group-title">{group.replace(/_/g, " ")}</h3>
          <div className="anchor-grid">
            {items.map((a) => <AnchorCard key={a.name} anchor={a} />)}
          </div>
        </div>
      ))}
    </div>
  );
}
