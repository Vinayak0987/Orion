// Renders arbitrary section payloads without a per-field component.
//
// The backend's section registry (F45) already decides which fields belong where,
// so the frontend only needs to know how to display a value by shape. That keeps
// adding a field to a department model from requiring a frontend change too.

const INR_FIELD = /_inr$|_inr_/;
const PCT_FIELD = /_pct$/;

export function humanize(key) {
  return key
    .replace(/_inr$/, " (₹)")
    .replace(/_pct$/, " (%)")
    .replace(/_/g, " ")
    .replace(/\b(y1|y2|y3)\b/g, (match) => `year ${match[1]}`)
    .replace(/^./, (char) => char.toUpperCase());
}

export function formatInr(value) {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  // Indian digit grouping: 15,00,000 rather than 1,500,000.
  return amount.toLocaleString("en-IN");
}

function Scalar({ field, value }) {
  if (value === null || value === undefined || value === "") return <span className="muted">—</span>;
  if (typeof value === "boolean") return <span>{value ? "yes" : "no"}</span>;
  if (typeof value === "number") {
    if (INR_FIELD.test(field)) return <span>₹{formatInr(value)}</span>;
    if (PCT_FIELD.test(field)) return <span>{value}%</span>;
    return <span>{formatInr(value)}</span>;
  }
  return <span>{String(value)}</span>;
}

function ObjectTable({ value }) {
  const entries = Object.entries(value).filter(
    ([, v]) => v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0)
  );
  if (entries.length === 0) return null;

  return (
    <table className="kv">
      <tbody>
        {entries.map(([key, nested]) => (
          <tr key={key}>
            <th>{humanize(key)}</th>
            <td>
              <Value field={key} value={nested} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ObjectList({ field, value }) {
  // Build a stable column set from the union of keys that carry content.
  const columns = [];
  for (const row of value) {
    for (const [key, nested] of Object.entries(row ?? {})) {
      const empty =
        nested === null || nested === undefined || nested === "" ||
        (Array.isArray(nested) && nested.length === 0);
      if (!empty && !columns.includes(key)) columns.push(key);
    }
  }
  if (columns.length === 0) return null;

  return (
    <div className="table-scroll">
      <table className="rows">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{humanize(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {value.map((row, index) => (
            <tr key={`${field}-${index}`}>
              {columns.map((column) => (
                <td key={column}>
                  <Value field={column} value={row?.[column]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Value({ field, value }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="muted">—</span>;
    if (typeof value[0] === "object" && value[0] !== null) {
      return <ObjectList field={field} value={value} />;
    }
    return (
      <ul className="bullets">
        {value.map((item, index) => (
          <li key={`${field}-${index}`}>{String(item)}</li>
        ))}
      </ul>
    );
  }

  if (value !== null && typeof value === "object") {
    if (field === "color_palette") return <Palette palette={value} />;
    return <ObjectTable value={value} />;
  }

  return <Scalar field={field} value={value} />;
}

function Palette({ palette }) {
  const swatches = [
    ["Primary", palette.primary_hex],
    ["Secondary", palette.secondary_hex],
    ["Accent", palette.accent_hex],
  ].filter(([, hex]) => hex);

  return (
    <div>
      <div className="palette">
        {swatches.map(([label, hex]) => (
          <div key={label} className="palette-item">
            <div className="swatch" style={{ backgroundColor: hex }} />
            <div className="meta">
              {label}
              <br />
              {hex}
            </div>
          </div>
        ))}
      </div>
      {palette.rationale && <p className="meta">{palette.rationale}</p>}
    </div>
  );
}
