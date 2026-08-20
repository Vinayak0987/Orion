// AnchorTrend - inline SVG line chart showing anchor vs proxy over time.
// Includes a <title> and a <table> fallback for screen readers.

import { useMemo } from "react";

const W = 600, H = 200, PAD = 40;

function buildPath(points, xScale, yMin, yMax) {
  if (!points.length) return "";
  const yRange = yMax - yMin || 1;
  return points.map((p, i) => {
    const x = PAD + (i / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
    const y = H - PAD - ((p.value - yMin) / yRange) * (H - 2 * PAD);
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

export default function AnchorTrend({ series, anchorName, proxyName }) {
  const anchorPoints = series?.[anchorName] ?? [];
  const proxyPoints = series?.[proxyName] ?? [];

  const chart = useMemo(() => {
    if (!anchorPoints.length) return null;
    const allValues = [
      ...anchorPoints.map((p) => p.value),
      ...proxyPoints.map((p) => p.value),
    ];
    const yMin = Math.min(...allValues);
    const yMax = Math.max(...allValues);
    const anchorPath = buildPath(anchorPoints, null, yMin, yMax);
    const proxyPath = proxyPoints.length ? buildPath(proxyPoints, null, yMin, yMax) : "";
    return { anchorPath, proxyPath, yMin, yMax };
  }, [anchorPoints, proxyPoints]);

  if (!chart) {
    return <div className="panel empty">No trend data available.</div>;
  }

  return (
    <div className="anchor-trend">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-labelledby="trend-title"
        className="trend-svg"
      >
        <title id="trend-title">
          Trend of {anchorName}{proxyName ? ` vs ${proxyName}` : ""}
        </title>
        {/* Y axis labels */}
        <text x={PAD - 4} y={PAD} textAnchor="end" className="trend-label">
          {chart.yMax.toFixed(1)}
        </text>
        <text x={PAD - 4} y={H - PAD} textAnchor="end" className="trend-label">
          {chart.yMin.toFixed(1)}
        </text>
        {/* Anchor line */}
        <path d={chart.anchorPath} fill="none" stroke="var(--primary)" strokeWidth="2" />
        {/* Proxy line (lighter) */}
        {chart.proxyPath && (
          <path d={chart.proxyPath} fill="none" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="4 3" />
        )}
      </svg>
      {/* Legend */}
      <div className="trend-legend">
        <span className="trend-legend-item">
          <span style={{ display: "inline-block", width: 16, height: 3, background: "var(--primary)", marginRight: 4 }} />
          {anchorName.replace(/_/g, " ")} (anchor 🔒)
        </span>
        {proxyName && (
          <span className="trend-legend-item">
            <span style={{ display: "inline-block", width: 16, height: 3, background: "var(--muted)", marginRight: 4, borderTop: "1px dashed var(--muted)" }} />
            {proxyName.replace(/_/g, " ")} (proxy)
          </span>
        )}
      </div>
      {/* Accessible table fallback */}
      <details className="trend-table-details">
        <summary>Data table</summary>
        <table className="trend-table" aria-label={`${anchorName} trend data`}>
          <thead>
            <tr>
              <th>Point</th>
              <th>{anchorName}</th>
              {proxyName && <th>{proxyName}</th>}
            </tr>
          </thead>
          <tbody>
            {anchorPoints.map((p, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{p.value.toFixed(2)}</td>
                {proxyName && <td>{proxyPoints[i]?.value?.toFixed(2) ?? "—"}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
