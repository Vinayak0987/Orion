import { useState } from "react";
import {
  Image as ImageIcon,
  Film,
  FileCode2,
  FileText,
  Download,
  Maximize2,
  Table as TableIcon,
  Braces,
  File as FileIcon,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

import { missionApi } from "../../missionApi";
import { Markdown } from "./Markdown.jsx";

// ---------------------------------------------------------------------------
// ArtifactCard — a reusable neumorphic renderer for a single typed artifact.
//
// An artifact is: { type, url?, content?, mime?, filename?, title? }
//   type: 'text' | 'image' | 'video' | 'html' | 'file' | 'data'
//
// Backend-served files come back as relative URLs ("/charts/..", "/artifacts/..").
// Those are resolved against missionApi.base so the browser can load them.
// Styled to match ChartCard / the app's neumorphic ink palette.
// ---------------------------------------------------------------------------

// Resolve a possibly-relative artifact URL to something the browser can load.
export function resolveArtifactUrl(url) {
  if (!url) return url;
  if (/^(https?:|data:|blob:)/i.test(url)) return url; // already absolute
  if (url.startsWith("/")) return `${missionApi.base}${url}`; // /charts/.., /artifacts/..
  // bare filename → assume served under /artifacts/
  return `${missionApi.base}/artifacts/${url.replace(/^\.?\/*/, "")}`;
}

// Human-readable byte size (accepts a number of bytes or an already-formatted string).
function fmtSize(size) {
  if (size == null) return "";
  if (typeof size === "string") return size;
  const n = Number(size);
  if (!Number.isFinite(n) || n <= 0) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// A soft header row (icon + label + optional action) shared by card types.
function CardHead({ Icon, label, children }) {
  return (
    <div className="flex items-center justify-between mb-2 px-1">
      <span className="flex items-center gap-1.5 text-[12px] font-semibold text-[#5b6678]">
        <Icon size={14} className="text-[#4f46e5]" /> {label}
      </span>
      {children}
    </div>
  );
}

// Trigger a browser download of a text blob (used for inline HTML content).
function downloadText(filename, text, mime = "text/html") {
  const blob = new Blob([text ?? ""], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---- image ----------------------------------------------------------------
function ImageArtifact({ artifact, onZoom }) {
  const src = resolveArtifactUrl(artifact.url);
  const [err, setErr] = useState(false);
  const open = () => (onZoom ? onZoom(src) : window.open(src, "_blank", "noreferrer"));
  return (
    <div className="neu-card rounded-2xl p-3 max-w-[560px]">
      <CardHead Icon={ImageIcon} label={artifact.title || "Image"}>
        <button onClick={open} title="Enlarge"
          className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#8792a6] hover:text-[#4f46e5]">
          <Maximize2 size={13} />
        </button>
      </CardHead>
      {err ? (
        <div className="neu-inset rounded-xl py-10 text-center text-[12.5px] text-[#9aa6b8]">Image unavailable.</div>
      ) : (
        <button onClick={open} className="block w-full neu-inset rounded-xl p-2">
          <img src={src} alt={artifact.title || "artifact"} onError={() => setErr(true)}
            className="w-full rounded-lg bg-white cursor-zoom-in" loading="lazy" />
        </button>
      )}
    </div>
  );
}

// ---- video ----------------------------------------------------------------
function VideoArtifact({ artifact }) {
  const src = resolveArtifactUrl(artifact.url);
  const poster = artifact.poster ? resolveArtifactUrl(artifact.poster) : undefined;
  return (
    <div className="neu-card rounded-2xl p-3 max-w-[560px]">
      <CardHead Icon={Film} label={artifact.title || "Video"} />
      <div className="neu-inset rounded-xl p-2">
        <video src={src} poster={poster} controls preload="metadata"
          className="w-full rounded-lg bg-black">
          Your browser does not support the video tag.
        </video>
      </div>
    </div>
  );
}

// ---- html ------------------------------------------------------------------
function HtmlArtifact({ artifact }) {
  const hasContent = typeof artifact.content === "string" && artifact.content.length > 0;
  const src = artifact.url ? resolveArtifactUrl(artifact.url) : null;
  const filename = artifact.filename || `${(artifact.title || "artifact").replace(/[^\w- ]+/g, "").trim() || "artifact"}.html`;
  const download = () => {
    if (hasContent) downloadText(filename, artifact.content, "text/html");
    else if (src) window.open(src, "_blank", "noreferrer");
  };
  return (
    <div className="neu-card rounded-2xl p-3 max-w-[720px]">
      <CardHead Icon={FileCode2} label={artifact.title || "HTML"}>
        <button onClick={download} title="Download .html"
          className="neu-btn-ghost flex items-center gap-1.5 px-2.5 py-1.5 text-[11.5px] font-medium">
          <Download size={13} /> {hasContent ? "Download .html" : "Open"}
        </button>
      </CardHead>
      <div className="neu-inset rounded-xl p-2 overflow-hidden">
        <iframe
          title={artifact.title || "html-artifact"}
          sandbox="allow-same-origin"
          {...(hasContent ? { srcDoc: artifact.content } : { src })}
          className="w-full rounded-lg bg-white"
          style={{ height: "420px", maxHeight: "60vh", border: "0" }}
        />
      </div>
    </div>
  );
}

// ---- file ------------------------------------------------------------------
function FileArtifact({ artifact }) {
  const href = resolveArtifactUrl(artifact.url);
  const name = artifact.filename || artifact.title || (artifact.url || "").split("/").pop() || "file";
  const size = fmtSize(artifact.size);
  return (
    <a href={href} target="_blank" rel="noreferrer"
      className="neu-card rounded-2xl flex items-center gap-3 px-3.5 py-3 max-w-sm hover:-translate-y-0.5 transition-transform">
      <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0 text-[#4f46e5]">
        <FileIcon size={20} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-semibold text-[#334155] truncate">{name}</p>
        <p className="text-[11px] text-[#9aa6b8]">
          {artifact.mime || "file"}{size ? ` · ${size}` : ""}
        </p>
      </div>
      <Download size={16} className="text-[#8792a6] shrink-0" />
    </a>
  );
}

// ---- data ------------------------------------------------------------------
function DataTable({ rows }) {
  // rows is a non-empty array of plain objects → compact table of the union of keys.
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r || {})))];
  const cell = (v) =>
    v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
  return (
    <div className="neu-inset rounded-xl overflow-auto om-scroll" style={{ maxHeight: "360px" }}>
      <table className="w-full text-[12.5px] border-collapse">
        <thead className="bg-[#eef1f6] sticky top-0">
          <tr>
            {cols.map((c) => (
              <th key={c} className="border border-[#e2e6ee] px-3 py-2 text-left font-semibold text-[#334155] whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className="border border-[#e2e6ee] px-3 py-1.5 text-[#4a5568] align-top">{cell(r?.[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DataArtifact({ artifact }) {
  // Data may arrive as `content` (object/array/string) or inline on the artifact.
  let data = artifact.content;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch { /* keep as raw string */ }
  }
  const isObjectArray =
    Array.isArray(data) && data.length > 0 && data.every((r) => r && typeof r === "object" && !Array.isArray(r));

  const json = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  const large = (json || "").length > 1200;
  const [open, setOpen] = useState(!large);

  return (
    <div className="neu-card rounded-2xl p-3 max-w-[720px]">
      <CardHead Icon={isObjectArray ? TableIcon : Braces} label={artifact.title || "Data"}>
        {!isObjectArray && large && (
          <button onClick={() => setOpen((o) => !o)}
            className="neu-btn-ghost flex items-center gap-1.5 px-2.5 py-1.5 text-[11.5px] font-medium">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} {open ? "Collapse" : "Expand"}
          </button>
        )}
      </CardHead>
      {isObjectArray ? (
        <DataTable rows={data} />
      ) : open ? (
        <pre className="neu-inset rounded-xl p-3 text-[11.5px] text-[#5b6678] font-mono whitespace-pre-wrap overflow-auto om-scroll" style={{ maxHeight: "360px" }}>
          {json}
        </pre>
      ) : (
        <button onClick={() => setOpen(true)}
          className="neu-inset rounded-xl py-6 w-full text-center text-[12px] text-[#9aa6b8] hover:text-[#4f46e5]">
          Large data block · click to expand
        </button>
      )}
    </div>
  );
}

// ---- text ------------------------------------------------------------------
function TextArtifact({ artifact }) {
  return (
    <div className="neu-card rounded-2xl p-3.5 max-w-[720px]">
      {artifact.title && <CardHead Icon={FileText} label={artifact.title} />}
      <Markdown compact>{artifact.content || ""}</Markdown>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public component. Dispatches by `artifact.type`. `onZoom(src)` is optional —
// when provided (e.g. the Command Center chart zoom overlay), image clicks call
// it; otherwise images open in a new tab.
// ---------------------------------------------------------------------------
export function ArtifactCard({ artifact, onZoom }) {
  if (!artifact || typeof artifact !== "object") return null;
  switch (artifact.type) {
    case "image":
      return <ImageArtifact artifact={artifact} onZoom={onZoom} />;
    case "video":
      return <VideoArtifact artifact={artifact} />;
    case "html":
      return <HtmlArtifact artifact={artifact} />;
    case "file":
      return <FileArtifact artifact={artifact} />;
    case "data":
      return <DataArtifact artifact={artifact} />;
    case "text":
      return <TextArtifact artifact={artifact} />;
    default:
      // Unknown type: degrade gracefully to a JSON data view.
      return <DataArtifact artifact={{ ...artifact, type: "data", content: artifact.content ?? artifact }} />;
  }
}

export default ArtifactCard;
