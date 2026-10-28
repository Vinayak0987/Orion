// Client-side export — turn a chat answer/plan into a downloadable HTML file
// or a PDF (via the browser's print dialog). The content is rendered from
// Markdown to properly structured HTML so the file looks like the chat page,
// NOT a raw text dump. Uses `marked` (sync, tiny). Zero network.

import { marked } from "marked";
import { missionApi } from "../missionApi";

marked.setOptions({ gfm: true, breaks: true });

// Fetch a chart image and return a self-contained base64 data URI so the
// exported HTML/PDF works offline (no dependency on the running backend).
async function toDataUri(url) {
  try {
    const full = /^https?:/i.test(url) ? url : `${missionApi.base}${url.startsWith("/") ? url : `/charts/${url.replace(/^charts\//, "")}`}`;
    const res = await fetch(full);
    if (!res.ok) return null;
    const blob = await res.blob();
    return await new Promise((resolve) => {
      const r = new FileReader();
      r.onloadend = () => resolve(r.result);
      r.onerror = () => resolve(null);
      r.readAsDataURL(blob);
    });
  } catch { return null; }
}

// Rewrite any /charts markdown image srcs in the body to data URIs we fetched.
function embedBodyImages(md = "", uriMap = {}) {
  return (md || "").replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, src) => {
    const key = src.replace(/^.*\/charts\//, "/charts/").replace(/^(?!\/charts\/)/, (s) => s);
    const uri = uriMap[src] || uriMap[key];
    return uri ? `![${alt}](${uri})` : "";  // drop broken refs if we couldn't embed
  });
}

function mdToHtml(md = "") {
  try {
    return marked.parse(md);
  } catch {
    // Fallback: escape and preserve line breaks.
    return `<p>${(md || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br/>")}</p>`;
  }
}

function escapeText(s = "") {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderDocument(title, bodyText, outputs = [], chartUris = []) {
  const intro = bodyText ? `<div class="section">${mdToHtml(bodyText)}</div>` : "";

  const chartsHtml = (chartUris || []).filter(Boolean).length
    ? `<section class="card"><h2 class="card-title">Charts</h2>${
        chartUris.filter(Boolean).map((u) => `<img class="chart" src="${u}" alt="chart" />`).join("")
      }</section>`
    : "";

  const sections = (outputs || [])
    .map((o) => {
      const body = o.result?.data || o.result?.summary || o.result?.error || "";
      if (!body) return "";
      return `
      <section class="card">
        <h2 class="card-title">${escapeText(o.task || "Result")}</h2>
        <div class="card-body">${mdToHtml(body)}</div>
      </section>`;
    })
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeText(title)}</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
           color: #334155; max-width: 760px; margin: 48px auto; padding: 0 28px; line-height: 1.65; }
    h1.doc-title { font-size: 28px; font-weight: 800; color: #0b1220; letter-spacing: -0.5px; margin: 0 0 4px; }
    .meta { color: #94a3b8; font-size: 13px; margin-bottom: 30px; }

    /* Rendered markdown styling — mirrors the chat page */
    .section, .card-body { font-size: 15px; }
    h1 { font-size: 22px; font-weight: 800; color: #1e293b; margin: 24px 0 10px; }
    h2 { font-size: 19px; font-weight: 700; color: #1e293b; margin: 22px 0 10px; }
    h3 { font-size: 16px; font-weight: 700; color: #334155; margin: 18px 0 8px; }
    h4 { font-size: 14.5px; font-weight: 700; color: #334155; margin: 16px 0 6px; }
    p { margin: 10px 0; }
    strong { font-weight: 700; color: #1e293b; }
    em { font-style: italic; }
    ul, ol { margin: 10px 0; padding-left: 24px; }
    li { margin: 5px 0; }
    a { color: #4f46e5; text-decoration: underline; }
    blockquote { border-left: 3px solid #c7cede; padding-left: 14px; margin: 14px 0; color: #64748b; font-style: italic; }
    hr { border: 0; border-top: 1px solid #e2e6ee; margin: 22px 0; }
    code { background: #eef1f6; color: #be185d; padding: 2px 6px; border-radius: 5px; font-size: 13px;
           font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    pre { background: #1e293b; color: #e2e8f0; padding: 14px 16px; border-radius: 10px; overflow-x: auto; margin: 14px 0; }
    pre code { background: transparent; color: inherit; padding: 0; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
    th, td { border: 1px solid #e2e6ee; padding: 9px 12px; text-align: left; vertical-align: top; }
    th { background: #eef1f6; font-weight: 700; color: #334155; }

    /* Per-task result cards */
    .card { border: 1px solid #e6ebf2; border-radius: 14px; padding: 18px 22px; margin: 18px 0;
            background: #fbfcfe; box-shadow: 0 2px 10px rgba(15,23,42,0.04); }
    .card-title { font-size: 15px; font-weight: 700; color: #4338ca; margin: 0 0 10px; letter-spacing: 0.2px; }
    .chart { max-width: 100%; border-radius: 10px; border: 1px solid #e6ebf2; background: #fff; margin: 8px 0; display: block; }
    footer { margin-top: 36px; padding-top: 16px; border-top: 1px solid #eef1f6; color: #cbd5e1; font-size: 12px; }
    @media print { body { margin: 0; max-width: none; } .card { break-inside: avoid; } .chart { break-inside: avoid; } h1,h2,h3 { break-after: avoid; } }
  </style>
</head>
<body>
  <h1 class="doc-title">${escapeText(title)}</h1>
  <div class="meta">Generated by Orion · ${new Date().toLocaleString()}</div>
  ${intro}
  ${chartsHtml}
  ${sections}
  <footer>Orion AI — Command Center export</footer>
</body>
</html>`;
}

// Collect every chart URL referenced by the payload (explicit charts[] +
// any /charts markdown images in body/outputs) and fetch them as data URIs.
async function gatherCharts({ body = "", outputs = [], charts = [] }) {
  const urls = new Set();
  (charts || []).forEach((c) => urls.add(c.url || c));
  const scan = (s) => (String(s || "").match(/\/charts\/[\w.-]+\.(?:png|jpe?g|svg)/gi) || []).forEach((u) => urls.add(u));
  scan(body);
  (outputs || []).forEach((o) => { scan(o.result?.data); scan(o.result?.summary); });
  const uriMap = {};
  const list = [];
  for (const u of urls) {
    const uri = await toDataUri(u);
    if (uri) { uriMap[u] = uri; list.push(uri); }
  }
  return { uriMap, list };
}

export async function exportHtml({ title = "Orion Plan", body = "", outputs = [], charts = [] }) {
  const { uriMap, list } = await gatherCharts({ body, outputs, charts });
  const html = renderDocument(title, embedBodyImages(body, uriMap), outputs, list);
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.replace(/[^\w- ]+/g, "").trim() || "orion-plan"}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function exportPdf({ title = "Orion Plan", body = "", outputs = [], charts = [] }) {
  const { uriMap, list } = await gatherCharts({ body, outputs, charts });
  const html = renderDocument(title, embedBodyImages(body, uriMap), outputs, list);
  const win = window.open("", "_blank", "width=820,height=900");
  if (!win) return false; // popup blocked
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.onload = () => { win.focus(); win.print(); };
  setTimeout(() => { try { win.focus(); win.print(); } catch { /* ignore */ } }, 600);
  return true;
}
