// Knowledge · Upload / Connect Sources (ViewUploadSources.jsx)
// Mock layout (breadcrumb + icon header + tabs + two-column body: dropzone +
// recent uploads on the left, external sources on the right), re-skinned
// neumorphic, wired to the real backend.
//   file drop/browse -> knowledgeApi.uploadDocument(file)
//   URL ingest       -> knowledgeApi.ingestUrl(url)
//   per-item status  -> processing / active (+chunks) / error
import { useEffect, useRef, useState } from "react";
import { UploadCloud, ArrowRight, Link2, Loader2, CheckCircle2, XCircle, FileText } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";
import { knowledgeApi } from "../../knowledgeApi.js";
import { toolApi } from "../../toolApi.js";
import { Modal } from "../ui/Modal.jsx";
import { useToast } from "../ui/Toast.jsx";

const TABS = ["Upload Files", "Connect Sources", "Data Sync", "Source Management"];

/* --- Brand icons (inline SVG for crisp rendering) --- */
const GoogleDriveIcon = () => (
  <svg viewBox="0 0 87.3 78" className="w-7 h-7">
    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da" />
    <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47" />
    <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335" />
    <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d" />
    <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc" />
    <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00" />
  </svg>
);
const SharePointIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5">
    <circle cx="9" cy="7" r="5.2" fill="#036c70" />
    <circle cx="15.5" cy="11.5" r="4.6" fill="#1a9ba1" />
    <circle cx="12" cy="17.5" r="3.8" fill="#37c6d0" />
    <path d="M11 6.5H4.6A1.1 1.1 0 0 0 3.5 7.6v6.8A1.1 1.1 0 0 0 4.6 15.5H11a1.1 1.1 0 0 0 1.1-1.1V7.6A1.1 1.1 0 0 0 11 6.5z" fill="#03787c" />
    <text x="7.7" y="12.6" fontSize="6" fontWeight="700" fill="#fff" textAnchor="middle" fontFamily="Arial">S</text>
  </svg>
);
const SlackIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5">
    <path d="M5.04 15.16a2.4 2.4 0 1 1-2.4-2.4h2.4z" fill="#e01e5a" />
    <path d="M6.25 15.16a2.4 2.4 0 0 1 4.8 0v6.02a2.4 2.4 0 1 1-4.8 0z" fill="#e01e5a" />
    <path d="M8.65 5.04a2.4 2.4 0 1 1 2.4-2.4v2.4z" fill="#36c5f0" />
    <path d="M8.65 6.25a2.4 2.4 0 0 1 0 4.8H2.63a2.4 2.4 0 1 1 0-4.8z" fill="#36c5f0" />
    <path d="M18.77 8.65a2.4 2.4 0 1 1 2.4 2.4h-2.4z" fill="#2eb67d" />
    <path d="M17.56 8.65a2.4 2.4 0 0 1-4.8 0V2.63a2.4 2.4 0 1 1 4.8 0z" fill="#2eb67d" />
    <path d="M15.16 18.77a2.4 2.4 0 1 1-2.4 2.4v-2.4z" fill="#ecb22e" />
    <path d="M15.16 17.56a2.4 2.4 0 0 1 0-4.8h6.02a2.4 2.4 0 1 1 0 4.8z" fill="#ecb22e" />
  </svg>
);
const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5">
    <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.31-.54-1.53.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.65.25 2.87.12 3.18.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58C20.56 22.3 24 17.8 24 12.5 24 5.87 18.63.5 12 .5z" fill="#181717" />
  </svg>
);

const SOURCES = [
  { name: "Google Drive", sub: "Import files from Google", Icon: GoogleDriveIcon, provider: "google" },
  { name: "SharePoint", sub: "OneDrive & SharePoint files", Icon: SharePointIcon, provider: "microsoft" },
  { name: "GitHub", sub: "Import repository files", Icon: GitHubIcon, provider: "github" },
  { name: "Slack", sub: "Import shared files", Icon: SlackIcon, provider: "slack" },
];

export function ViewUploadSources({ onDone }) {
  const toast = useToast();
  const fileRef = useRef(null);
  const [items, setItems] = useState([]);   // {id, name, status, chunks?, error?}
  const [url, setUrl] = useState("");
  const [activeTab, setActiveTab] = useState(0);  // 0 Upload / 1 Connect / 2 Data Sync / 3 Management
  const [dragging, setDragging] = useState(false);
  const [urlBusy, setUrlBusy] = useState(false);
  const [importing, setImporting] = useState("");
  // Generic connector modal state (handles microsoft / github / slack list+import).
  const [conn, setConn] = useState(null);   // { provider, name } | null
  const [connFiles, setConnFiles] = useState([]);
  const [connLoading, setConnLoading] = useState(false);
  const [connErr, setConnErr] = useState("");
  const [connSearch, setConnSearch] = useState("");
  const [ghRepo, setGhRepo] = useState("");   // selected GitHub repo
  const [ghRepos, setGhRepos] = useState([]);
  const [statuses, setStatuses] = useState({}); // provider -> connected bool

  // Load connected status for every provider-backed source once.
  useEffect(() => {
    (async () => {
      const map = {};
      for (const s of SOURCES.filter((x) => x.provider)) {
        try {
          const st = s.provider === "google" ? await knowledgeApi.driveStatus()
            : s.provider === "microsoft" ? await knowledgeApi.msStatus()
            : s.provider === "github" ? await knowledgeApi.githubStatus()
            : await knowledgeApi.slackStatus();
          map[s.provider] = !!st.connected;
        } catch { map[s.provider] = false; }
      }
      setStatuses(map);
    })();
    // eslint-disable-next-line
  }, []);

  const startOAuth = async (provider) => {
    try {
      const res = await toolApi.oauthAuthorize(provider);
      if (res?.authorize_url) {
        window.open(res.authorize_url, "_blank", "width=560,height=680");
        toast.info("Authorize access, then click the connector again.");
      } else toast.error("Could not start sign-in.");
    } catch (e) { toast.error(e.message); }
  };

  const connectSource = async (src) => {
    const { name, provider } = src;
    if (!provider) { toast.info(`${name} connector is coming soon.`); return; }

    // Google Drive keeps its native-picker / modal path.
    if (provider === "google") {
      try {
        const cfg = await knowledgeApi.drivePickerConfig();
        if (!cfg.connected) return startOAuth("google");
        if (cfg.has_picker_key) {
          const { openGoogleDrivePicker } = await import("../../googlePicker.js");
          await openGoogleDrivePicker({
            accessToken: cfg.access_token, apiKey: cfg.api_key, appId: cfg.app_id,
            onPicked: async (docs) => { for (const f of docs) await importFile("google", f); },
          });
          return;
        }
        openConnector(src);
      } catch (e) { toast.error(e.message); }
      return;
    }

    // Microsoft / GitHub / Slack → open the generic list+import modal.
    if (!statuses[provider]) return startOAuth(provider);
    openConnector(src);
  };

  const openConnector = (src) => {
    setConn(src); setConnFiles([]); setConnErr(""); setConnSearch(""); setGhRepo(""); setGhRepos([]);
    loadConnFiles(src.provider, "");
  };

  const loadConnFiles = async (provider, q, repo) => {
    setConnLoading(true); setConnErr("");
    try {
      if (provider === "google") setConnFiles((await knowledgeApi.driveFiles(q)).files || []);
      else if (provider === "microsoft") setConnFiles((await knowledgeApi.msFiles(q)).files || []);
      else if (provider === "slack") setConnFiles((await knowledgeApi.slackFiles()).files || []);
      else if (provider === "github") {
        if (!repo) {
          const r = await knowledgeApi.githubRepos();
          setGhRepos(r.repos || []); setConnFiles([]);
        } else {
          setConnFiles((await knowledgeApi.githubFiles(repo, q)).files || []);
        }
      }
    } catch (e) { setConnErr(e.message); }
    finally { setConnLoading(false); }
  };

  const importFile = async (provider, f) => {
    const key = f.id || f.path || f.url;
    setImporting(key);
    try {
      let r;
      if (provider === "google") r = await knowledgeApi.driveImport(f.id, f.name, f.mimeType);
      else if (provider === "microsoft") r = await knowledgeApi.msImport(f.id, f.name);
      else if (provider === "github") r = await knowledgeApi.githubImport(ghRepo, f.path);
      else if (provider === "slack") r = await knowledgeApi.slackImport(f.url, f.name);
      toast.success(`Imported "${f.name}"`);
      setItems((it) => [{ id: r.document_id, name: f.name, status: "stored" }, ...it]);
      onDone?.();
    } catch (e) { toast.error(e.message); }
    finally { setImporting(""); }
  };

  const upload = async (files) => {
    for (const file of files) {
      const id = `${file.name}-${Date.now()}`;
      setItems((it) => [{ id, name: file.name, status: "processing" }, ...it]);
      try {
        await knowledgeApi.uploadDocument(file);
        setItems((it) => it.map((x) => (x.id === id ? { ...x, status: "stored" } : x)));
        toast.success(`Stored ${file.name}`);
      } catch (e) {
        setItems((it) => it.map((x) => (x.id === id ? { ...x, status: "error", error: e.message } : x)));
        toast.error(e.message);
      }
    }
    onDone?.();
  };

  const ingestUrl = async () => {
    if (!url.trim()) return;
    const id = `url-${Date.now()}`;
    setItems((it) => [{ id, name: url.trim(), status: "processing" }, ...it]);
    setUrlBusy(true);
    try {
      const r = await knowledgeApi.ingestUrl(url.trim());
      setItems((it) => it.map((x) => (x.id === id ? { ...x, name: r.name || x.name, status: "stored" } : x)));
      toast.success("URL stored");
      setUrl("");
    } catch (e) {
      setItems((it) => it.map((x) => (x.id === id ? { ...x, status: "error", error: e.message } : x)));
      toast.error(e.message);
    } finally { setUrlBusy(false); onDone?.(); }
  };

  const StatusChip = ({ it }) => {
    if (it.status === "processing") return <span className="neu-chip inline-flex items-center gap-1 px-3 py-1 text-[12px] font-semibold text-amber-600"><Loader2 size={11} className="animate-spin" /> Uploading</span>;
    if (it.status === "stored" || it.status === "active") return <span className="neu-chip inline-flex items-center gap-1 px-3 py-1 text-[12px] font-semibold text-emerald-600"><CheckCircle2 size={11} /> Stored</span>;
    return <span className="neu-chip inline-flex items-center gap-1 px-3 py-1 text-[12px] font-semibold text-rose-500" title={it.error}><XCircle size={11} /> Error</span>;
  };

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-6 sm:px-7 sm:py-7">
      <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Upload / Connect Sources" }]} />

      {/* Header */}
      <div className="flex items-start gap-4 mb-5">
        <span className="neu-circle w-11 h-11 rounded-xl text-[#4f46e5] grid place-items-center shrink-0">
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6M9 15l3-3 3 3"/></svg>
        </span>
        <div className="flex-1 pt-0.5">
          <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">Upload / Connect Sources</h1>
          <p className="text-[13px] text-[#8792a6] mt-1">Upload files or connect external data sources</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-8 border-b border-[#e2e6ee] mb-7">
        {TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setActiveTab(i)}
            className={`pb-3.5 text-[15px] font-semibold border-b-2 -mb-px transition-colors ${
              i === activeTab ? "text-[#4f46e5] border-[#4f46e5]" : "text-[#8792a6] border-transparent hover:text-[#5b6678]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Two-column body */}
      {activeTab === 0 && (
      <div className="grid grid-cols-[1.15fr_1fr] gap-6 items-start">
        {/* Left column */}
        <div className="space-y-6">
          {/* Dropzone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); upload([...e.dataTransfer.files]); }}
            onClick={() => fileRef.current?.click()}
            className={`neu-inset rounded-2xl px-6 py-12 flex flex-col items-center text-center cursor-pointer transition-all ${dragging ? "ring-2 ring-[#a5b4fc]" : ""}`}
          >
            <input ref={fileRef} type="file" multiple hidden onChange={(e) => upload([...e.target.files])} accept=".pdf,.doc,.docx,.txt,.md,.xls,.csv" />
            <UploadCloud size={52} className="text-[#4f46e5]" strokeWidth={1.6} />
            <p className="text-[17px] font-semibold text-[#334155] mt-4">Drag and drop files here</p>
            <p className="text-[15px] text-[#8792a6] mt-1.5">or click to browse</p>
            <p className="text-[13px] text-[#9aa6b8] mt-3">Supports PDF, DOC, DOCX, TXT, MD, XLS, CSV (Max 50MB)</p>
            <button type="button" onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }} className="neu-btn-primary mt-6 h-12 px-8 text-[15px] font-semibold">
              Browse Files
            </button>
          </div>

          {/* URL ingest */}
          <div className="neu-card rounded-2xl p-5">
            <h2 className="text-[15px] font-semibold text-[#334155] mb-3">Ingest from URL</h2>
            <div className="flex items-center gap-2">
              <div className="neu-inset flex items-center gap-2 px-3 h-11 rounded-xl flex-1">
                <Link2 size={16} className="text-[#9aa6b8]" />
                <input value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ingestUrl()}
                  placeholder="https://example.com/article" className="bg-transparent outline-none text-[14px] text-[#334155] w-full placeholder:text-[#9aa6b8]" />
              </div>
              <button onClick={ingestUrl} disabled={urlBusy || !url.trim()} className="neu-btn-primary inline-flex items-center gap-2 h-11 px-5 text-[14px] font-semibold disabled:opacity-55">
                {urlBusy ? <Loader2 size={15} className="animate-spin" /> : <Link2 size={15} />} Ingest
              </button>
            </div>
          </div>

          {/* Recent Uploads (live processing list) */}
          <div className="neu-card rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[15px] font-semibold text-[#334155]">Recent Uploads</h2>
            </div>
            {items.length === 0 ? (
              <p className="text-[14px] text-[#9aa6b8] py-6 text-center">No uploads yet. Drop a file or ingest a URL to begin.</p>
            ) : (
              <div className="space-y-1">
                {items.map((it, i) => (
                  <div key={it.id} className={`flex items-center gap-3.5 py-3 ${i !== items.length - 1 ? "border-b border-[#e2e6ee]" : ""}`}>
                    <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center text-[#4f46e5] shrink-0"><FileText size={20} /></span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[15px] font-semibold text-[#334155] truncate">{it.name}</p>
                      <p className="text-[13px] text-[#9aa6b8]">{(it.status === "stored" || it.status === "active") ? "Stored — chunked automatically when an agent needs it" : it.status === "error" ? (it.error || "Failed") : "Uploading…"}</p>
                    </div>
                    <StatusChip it={it} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column: External Sources */}
        <div className="neu-card rounded-2xl p-6">
          <h2 className="text-[15px] font-semibold text-[#334155] mb-5">Connect External Sources</h2>
          <div className="space-y-1">
            {SOURCES.map((s, i) => (
              <div key={s.name} className={`flex items-center gap-3.5 py-3.5 ${i !== SOURCES.length - 1 ? "border-b border-[#e2e6ee]" : ""}`}>
                <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0"><s.Icon /></span>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] font-semibold text-[#334155]">{s.name}</p>
                  <p className="text-[13px] text-[#9aa6b8]">{s.sub}</p>
                </div>
                <button
                  onClick={() => connectSource(s)}
                  disabled={!s.provider}
                  className="neu-btn-ghost h-10 px-6 text-[14px] font-semibold text-[#5b6678] disabled:opacity-50"
                >
                  {!s.provider ? "Soon" : statuses[s.provider] ? "Browse" : "Connect"}
                </button>
              </div>
            ))}
          </div>
          <button className="mt-5 text-[15px] font-semibold text-[#4f46e5] flex items-center gap-1.5">
            View more integrations <ArrowRight size={16} />
          </button>
        </div>
      </div>
      )}

      {/* Connect Sources tab — external connectors full-width */}
      {activeTab === 1 && (
        <div className="neu-card rounded-2xl p-6 max-w-[720px]">
          <h2 className="text-[15px] font-semibold text-[#334155] mb-1">Connect External Sources</h2>
          <p className="text-[13px] text-[#8792a6] mb-5">Import documents from your connected apps. Click Browse to pick files; Connect to authorize.</p>
          <div className="space-y-1">
            {SOURCES.map((s, i) => (
              <div key={s.name} className={`flex items-center gap-3.5 py-3.5 ${i !== SOURCES.length - 1 ? "border-b border-[#e2e6ee]" : ""}`}>
                <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0"><s.Icon /></span>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] font-semibold text-[#334155]">{s.name}</p>
                  <p className="text-[13px] text-[#9aa6b8]">{s.sub}</p>
                </div>
                {s.provider && statuses[s.provider] && (
                  <span className="neu-chip px-2.5 py-1 text-[11.5px] font-semibold text-emerald-600">Connected</span>
                )}
                <button onClick={() => connectSource(s)} disabled={!s.provider}
                  className="neu-btn-ghost h-10 px-6 text-[14px] font-semibold text-[#5b6678] disabled:opacity-50">
                  {!s.provider ? "Soon" : statuses[s.provider] ? "Browse" : "Connect"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Sync tab */}
      {activeTab === 2 && (
        <div className="neu-card rounded-2xl p-6 max-w-[720px]">
          <h2 className="text-[15px] font-semibold text-[#334155] mb-1">Data Sync</h2>
          <p className="text-[13px] text-[#8792a6] mb-5">Keep imported documents up to date with their source.</p>
          <div className="space-y-2">
            {SOURCES.filter((s) => s.provider).map((s) => (
              <div key={s.name} className="neu-inset rounded-xl px-4 py-3.5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="neu-circle w-9 h-9 rounded-lg grid place-items-center shrink-0"><s.Icon /></span>
                  <div>
                    <p className="text-[14px] font-semibold text-[#334155]">{s.name}</p>
                    <p className="text-[12.5px] text-[#9aa6b8] mt-0.5">{statuses[s.provider] ? "Connected — re-import to refresh a file." : "Not connected."}</p>
                  </div>
                </div>
                <button onClick={() => connectSource(s)} className="neu-btn-ghost h-9 px-4 text-[13px] font-semibold text-[#4f46e5]">
                  {statuses[s.provider] ? "Browse" : "Connect"}
                </button>
              </div>
            ))}
          </div>
          <p className="text-[12.5px] text-[#9aa6b8] mt-4">Scheduled automatic sync is on the roadmap — for now, re-import to pull the latest version of a document.</p>
        </div>
      )}

      {/* Source Management tab */}
      {activeTab === 3 && (
        <div className="neu-card rounded-2xl p-6 max-w-[720px]">
          <h2 className="text-[15px] font-semibold text-[#334155] mb-1">Source Management</h2>
          <p className="text-[13px] text-[#8792a6] mb-5">Documents you've imported this session.</p>
          {items.length === 0 ? (
            <p className="text-[14px] text-[#9aa6b8] py-8 text-center">No sources imported yet. Use Upload Files or Connect Sources.</p>
          ) : (
            <div className="space-y-1">
              {items.map((it, i) => (
                <div key={it.id} className={`flex items-center gap-3.5 py-3 ${i !== items.length - 1 ? "border-b border-[#e2e6ee]" : ""}`}>
                  <span className="neu-circle w-10 h-10 rounded-lg grid place-items-center text-[#4f46e5] shrink-0"><FileText size={18} /></span>
                  <span className="flex-1 min-w-0 text-[14px] font-semibold text-[#334155] truncate">{it.name}</span>
                  <StatusChip it={it} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Generic connector file picker (Drive / OneDrive / GitHub / Slack) */}
      <Modal open={!!conn} onClose={() => setConn(null)} title={conn ? `Import from ${conn.name}` : ""}
        subtitle="Pick files to store in your knowledge base (chunked lazily when an agent needs them)"
        icon={conn?.Icon || FileText} size="lg">
        {conn && (
          <div className="space-y-3">
            {/* GitHub: repo selector */}
            {conn.provider === "github" && !ghRepo && (
              <>
                <p className="text-[12.5px] text-[#8792a6]">Choose a repository:</p>
                {connLoading ? (
                  <div className="grid place-items-center py-10 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
                ) : (
                  <div className="space-y-1.5 max-h-[340px] overflow-y-auto">
                    {ghRepos.map((r) => (
                      <button key={r.full_name} onClick={() => { setGhRepo(r.full_name); loadConnFiles("github", "", r.full_name); }}
                        className="w-full flex items-center gap-3 neu-inset rounded-xl px-3 py-2.5 text-left hover:bg-[#e7eaf1]/40">
                        <conn.Icon />
                        <span className="flex-1 min-w-0 text-[13.5px] text-[#334155] truncate">{r.full_name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Search bar (Drive / OneDrive / GitHub-within-repo) */}
            {(conn.provider !== "github" || ghRepo) && conn.provider !== "slack" && (
              <div className="flex items-center gap-2">
                {conn.provider === "github" && (
                  <button onClick={() => { setGhRepo(""); loadConnFiles("github", ""); }}
                    className="neu-btn-ghost h-10 px-3 text-[12px] font-semibold text-[#5b6678]">← Repos</button>
                )}
                <input value={connSearch} onChange={(e) => setConnSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadConnFiles(conn.provider, connSearch, ghRepo)}
                  placeholder={conn.provider === "github" ? "Path (e.g. src)…" : "Search files…"}
                  className="neu-inset flex-1 h-10 px-3 rounded-xl text-[13.5px] outline-none" />
                <button onClick={() => loadConnFiles(conn.provider, connSearch, ghRepo)}
                  className="neu-btn-primary h-10 px-4 text-[13px] font-semibold">Search</button>
              </div>
            )}

            {/* File list */}
            {connErr ? (
              <p className="text-[13px] text-rose-500 py-6 text-center">{connErr}</p>
            ) : connLoading && (conn.provider !== "github" || ghRepo) ? (
              <div className="grid place-items-center py-10 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
            ) : (conn.provider !== "github" || ghRepo) ? (
              connFiles.length === 0 ? (
                <p className="text-[13px] text-[#9aa6b8] py-8 text-center">No files found.</p>
              ) : (
                <div className="space-y-1.5 max-h-[340px] overflow-y-auto">
                  {connFiles.map((f) => {
                    const key = f.id || f.path || f.url;
                    const isDir = f.type === "dir";
                    return (
                      <div key={key} className="flex items-center gap-3 neu-inset rounded-xl px-3 py-2.5">
                        <FileText size={16} className="text-[#4f46e5] shrink-0" />
                        <span className="flex-1 min-w-0 text-[13.5px] text-[#334155] truncate">{f.name}</span>
                        {isDir ? (
                          <button onClick={() => loadConnFiles("github", f.path, ghRepo)}
                            className="neu-btn-ghost h-8 px-3 text-[12px] font-semibold text-[#5b6678]">Open</button>
                        ) : (
                          <button onClick={() => importFile(conn.provider, f)} disabled={importing === key}
                            className="neu-btn-ghost h-8 px-3 text-[12px] font-semibold text-[#4f46e5] disabled:opacity-50">
                            {importing === key ? <Loader2 size={13} className="animate-spin" /> : "Import"}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )
            ) : null}
          </div>
        )}
      </Modal>
    </div>
  );
}





