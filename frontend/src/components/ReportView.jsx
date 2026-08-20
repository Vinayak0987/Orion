// F49 - report viewer: department tabs, collapsible sections, headline metrics.
// F50 - download bar: PDF, JSON, copy-to-clipboard.

import { useMemo, useState } from "react";

import { api } from "../api";
import { Value, formatInr, humanize } from "./Value";

const DEPARTMENTS = ["strategy", "finance", "branding", "marketing", "operations"];

function Kpis({ plan }) {
  const finance = plan.finance ?? {};
  const strategy = plan.strategy ?? {};

  const entries = [
    finance.total_setup_cost_inr != null && {
      label: "Setup cost",
      value: `₹${formatInr(finance.total_setup_cost_inr)}`,
    },
    finance.projected_revenue_y1_inr != null && {
      label: "Year-1 revenue",
      value: `₹${formatInr(finance.projected_revenue_y1_inr)}`,
    },
    finance.net_margin_pct != null && {
      label: "Net margin",
      value: `${finance.net_margin_pct}%`,
    },
    finance.break_even_month
      ? { label: "Break-even", value: `Month ${finance.break_even_month}` }
      : null,
    strategy.location_score != null && {
      label: "Location score",
      value: `${strategy.location_score}/10`,
    },
  ].filter(Boolean);

  if (entries.length === 0) return null;

  return (
    <div className="kpi-row">
      {entries.map((entry) => (
        <div key={entry.label} className="kpi">
          <div className="kpi-label">{entry.label}</div>
          <div className="kpi-value">{entry.value}</div>
        </div>
      ))}
    </div>
  );
}

function Section({ spec, data, openByDefault }) {
  const [open, setOpen] = useState(openByDefault);

  const fields = Object.entries(data).filter(
    ([, value]) =>
      value !== null && value !== undefined && value !== "" &&
      !(Array.isArray(value) && value.length === 0)
  );
  if (fields.length === 0) return null;

  return (
    <section className="report-section">
      <button
        type="button"
        className="section-toggle"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="chevron">{open ? "▾" : "▸"}</span>
        <span className="section-title">{spec.title}</span>
        <span className="meta">{spec.description}</span>
        <span className="badge">{spec.features.join(" ")}</span>
      </button>

      {open && (
        <div className="section-body">
          {fields.map(([field, value]) => (
            <div key={field} className="field">
              <div className="field-name">{humanize(field)}</div>
              <div className="field-value">
                <Value field={field} value={value} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function ReportView({ summary, catalogue }) {
  const plan = summary.plan ?? {};
  const skipped = summary.routing?.skipped_departments ?? [];
  const available = DEPARTMENTS.filter((department) => plan[department]);
  const [tab, setTab] = useState(available[0] ?? "strategy");
  const [copied, setCopied] = useState("");

  const specsByDepartment = useMemo(() => {
    const grouped = {};
    for (const spec of catalogue) {
      (grouped[spec.department] ??= []).push(spec);
    }
    return grouped;
  }, [catalogue]);

  const contradictions = (summary.validation_warnings ?? []).filter(
    (warning) => !warning.startsWith("missing:")
  );

  async function copySection(department) {
    try {
      await navigator.clipboard.writeText(JSON.stringify(plan[department], null, 2));
      setCopied(department);
      setTimeout(() => setCopied(""), 1800);
    } catch {
      setCopied("failed");
    }
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify(summary, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `mabgp-plan-${summary.session_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const sectionSpecs = specsByDepartment[tab] ?? [];

  return (
    <div className="panel">
      <div className="report-head">
        <div>
          <h2 className="report-title">
            {plan.branding?.recommended_name || summary.intent?.business_type_label || "Business plan"}
          </h2>
          <p className="meta">
            {summary.status} · {summary.completeness_score}% complete ·{" "}
            {((summary.total_duration_ms ?? 0) / 1000).toFixed(1)}s ·{" "}
            {formatInr(summary.total_tokens)} tokens
            {skipped.length > 0 && ` · skipped: ${skipped.join(", ")}`}
          </p>
        </div>

        {/* F50 - downloads */}
        <div className="actions">
          <a className="button" href={api.reportUrl(summary.session_id)} target="_blank" rel="noreferrer">
            Open HTML report
          </a>
          <a className="button primary" href={api.pdfUrl(summary.session_id)}>
            Download PDF
          </a>
          <button type="button" className="button" onClick={downloadJson}>
            Download JSON
          </button>
        </div>
      </div>

      <Kpis plan={plan} />

      {contradictions.length > 0 && (
        <div className="callout callout-warn">
          <strong>Consistency checks flagged {contradictions.length} item(s)</strong>
          <ul className="bullets">
            {contradictions.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* F49 - department tabs */}
      <div className="tabs" role="tablist">
        {available.map((department) => (
          <button
            key={department}
            role="tab"
            aria-selected={tab === department}
            className={tab === department ? "tab tab-active" : "tab"}
            onClick={() => setTab(department)}
          >
            {department}
          </button>
        ))}
        {skipped.map((department) => (
          <span key={department} className="tab tab-disabled" title="Skipped by dynamic routing">
            {department}
          </span>
        ))}
      </div>

      <div className="tab-actions">
        <button type="button" className="link" onClick={() => copySection(tab)}>
          {copied === tab ? "Copied" : copied === "failed" ? "Copy failed" : `Copy ${tab} as JSON`}
        </button>
      </div>

      {sectionSpecs.map((spec, index) => {
        const departmentData = plan[spec.department] ?? {};
        const data = Object.fromEntries(
          spec.fields
            .filter((field) => field in departmentData)
            .map((field) => [field, departmentData[field]])
        );
        return (
          <Section key={spec.key} spec={spec} data={data} openByDefault={index === 0} />
        );
      })}
    </div>
  );
}
