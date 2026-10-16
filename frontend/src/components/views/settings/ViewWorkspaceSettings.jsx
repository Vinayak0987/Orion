import { useEffect, useRef, useState } from "react";
import { Sparkles, ImageUp, Trash2, UserPlus, Users, CheckCircle2 } from "lucide-react";

import { authApi } from "../../../auth/authApi.js";
import { TIMEZONE_OPTIONS, LANGUAGE_OPTIONS } from "../../../settingsLocal.js";
import { useToast } from "../../ui/Toast.jsx";
import { Modal } from "../../ui/Modal.jsx";
import {
  SettingsHeader,
  Chip,
  Tabs,
  NeuField,
  neuInput,
  neuSelect,
  NeuPrimaryButton,
  NeuGhostButton,
  NeuChip,
  NeuSectionTitle,
} from "./SettingsShared.jsx";

const ROLE_TONE = { Owner: "indigo", Admin: "amber", Member: "green", Viewer: "neutral" };

function initials(s) {
  return (s || "?").trim().slice(0, 2).toUpperCase();
}

/* ---------------- Overview ---------------- */
function Overview() {
  const toast = useToast();
  const [ws, setWs] = useState(null);
  const [uploading, setUploading] = useState(false);
  const logoRef = useRef(null);
  const set = (k, v) => setWs((w) => ({ ...w, [k]: v }));

  useEffect(() => { authApi.getWorkspace().then(setWs).catch((e) => toast.error(e.message)); /* eslint-disable-next-line */ }, []);

  async function save() {
    try {
      const u = await authApi.updateWorkspace({ name: ws.name, description: ws.description, timezone: ws.timezone, language: ws.language, logo_url: ws.logo_url });
      setWs(u);
      toast.success("Workspace saved.");
    } catch (e) { toast.error(e.message); }
  }

  async function onLogo(e) {
    const file = e.target.files?.[0]; e.target.value = ""; if (!file) return;
    setUploading(true);
    try {
      const res = await authApi.uploadFile(file);
      const u = await authApi.updateWorkspace({ logo_url: res.url });
      setWs(u);
      toast.success("Logo updated.");
    } catch (e) { toast.error(e.message); } finally { setUploading(false); }
  }

  if (!ws) return <div className="text-[13px] text-[#94a3b8] py-6">Loading…</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-7">
      {/* Form — neumorphic */}
      <div className="neu-card p-7">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-[15px] font-semibold text-[#334155]">Workspace Details</h2>
            <p className="text-[13px] text-[#8792a6] mt-0.5">Configure your workspace.</p>
          </div>
          <NeuPrimaryButton onClick={save}>
            <CheckCircle2 size={15} /> Save
          </NeuPrimaryButton>
        </div>

        <div className="flex flex-col gap-5">
          <NeuField label="Workspace Name">
            <input className={neuInput} value={ws.name || ""} onChange={(e) => set("name", e.target.value)} />
          </NeuField>
          <NeuField label="Description">
            <input className={neuInput} value={ws.description || ""} onChange={(e) => set("description", e.target.value)} placeholder="What this workspace is for" />
          </NeuField>
          <NeuField label="Logo">
            <button
              onClick={() => logoRef.current?.click()}
              disabled={uploading}
              className="neu-inset w-full h-[96px] flex flex-col items-center justify-center gap-1 hover:brightness-[0.99] transition overflow-hidden"
            >
              {ws.logo_url ? (
                <img src={ws.logo_url} alt="logo" className="h-full object-contain py-2" />
              ) : (
                <>
                  <ImageUp size={20} className="text-[#4f46e5]" />
                  <span className="text-[13px] font-semibold text-[#5b6678]">{uploading ? "Uploading…" : "Click to upload"}</span>
                  <span className="text-[11.5px] text-[#9aa6b8]">PNG or JPG · up to 10 MB</span>
                </>
              )}
            </button>
            <input ref={logoRef} type="file" accept="image/*" className="hidden" onChange={onLogo} />
          </NeuField>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <NeuField label="Default Timezone">
              <select value={ws.timezone || ""} onChange={(e) => set("timezone", e.target.value)} className={`${neuInput} appearance-none cursor-pointer`}>
                {TIMEZONE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </NeuField>
            <NeuField label="Default Language">
              <select value={ws.language || ""} onChange={(e) => set("language", e.target.value)} className={`${neuInput} appearance-none cursor-pointer`}>
                {LANGUAGE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </NeuField>
          </div>
        </div>
      </div>

      {/* Preview — neumorphic */}
      <div className="neu-card p-7 h-fit">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[15px] font-semibold text-[#334155]">Preview</h2>
          <span className="neu-raised text-[11px] font-semibold text-[#8792a6] rounded-full px-3 py-1">Live</span>
        </div>

        <div className="flex flex-col items-center text-center">
          <div className="neu-avatar-well p-2 rounded-2xl">
            <span className="grid place-items-center w-[72px] h-[72px] rounded-xl bg-gradient-to-br from-[#6366f1] to-[#4338ca] text-white overflow-hidden">
              {ws.logo_url ? <img src={ws.logo_url} alt="" className="w-full h-full object-cover" /> : <Sparkles size={26} fill="currentColor" />}
            </span>
          </div>
          <p className="text-[17px] font-semibold text-[#334155] mt-5 truncate max-w-full">{ws.name || "My Workspace"}</p>
          <p className="text-[13px] text-[#8792a6] mt-1 line-clamp-2">{ws.description || "Personal workspace"}</p>
        </div>

        <div className="neu-inset mt-6 p-4 space-y-3 text-[13px]">
          <div className="flex items-center justify-between">
            <span className="text-[#8792a6]">Plan</span>
            <Chip tone="green">Free</Chip>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[#8792a6] shrink-0">Timezone</span>
            <span className="font-medium text-[#5b6678] truncate text-right">{ws.timezone}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#8792a6]">Language</span>
            <span className="font-medium text-[#5b6678]">{ws.language}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Members ---------------- */
function InviteModal({ open, onClose, onAdded }) {
  const toast = useToast();
  const [draft, setDraft] = useState({ name: "", email: "", role: "Member" });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setDraft((d) => ({ ...d, [k]: v }));

  async function submit() {
    if (!draft.name.trim() || !draft.email.trim()) return;
    setBusy(true);
    try {
      await authApi.addMember(draft);
      toast.success(`Invited ${draft.name}.`);
      setDraft({ name: "", email: "", role: "Member" });
      onAdded();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Invite a member"
      subtitle="They'll be added to your workspace."
      icon={UserPlus}
      footer={
        <>
          <NeuGhostButton onClick={onClose}>Cancel</NeuGhostButton>
          <NeuPrimaryButton className="h-9 px-4" onClick={submit} disabled={busy}>{busy ? "Inviting…" : "Send Invite"}</NeuPrimaryButton>
        </>
      }
    >
      <div className="flex flex-col gap-3.5">
        <NeuField label="Full Name"><input className={neuInput} value={draft.name} onChange={(e) => set("name", e.target.value)} autoFocus /></NeuField>
        <NeuField label="Email"><input className={neuInput} value={draft.email} onChange={(e) => set("email", e.target.value)} placeholder="name@example.com" /></NeuField>
        <NeuField label="Role">
          <select value={draft.role} onChange={(e) => set("role", e.target.value)} className={`${neuInput} neu-select`}>
            {["Admin", "Member", "Viewer"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </NeuField>
      </div>
    </Modal>
  );
}

function Members() {
  const toast = useToast();
  const [members, setMembers] = useState([]);
  const [invite, setInvite] = useState(false);

  const load = () => authApi.getMembers().then((d) => setMembers(d.members)).catch((e) => toast.error(e.message));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  async function remove(id) {
    try { await authApi.removeMember(id); toast.success("Member removed."); load(); }
    catch (e) { toast.error(e.message); }
  }

  return (
    <>
      <div className="neu-card p-7">
        <div className="flex items-center justify-between mb-4">
          <div>
            <NeuSectionTitle>Team Members</NeuSectionTitle>
            <p className="text-[13px] text-[#8792a6] mt-0.5">{members.length} {members.length === 1 ? "member" : "members"} in this workspace</p>
          </div>
          <NeuPrimaryButton className="h-9 px-4" onClick={() => setInvite(true)}><UserPlus size={15} /> Invite</NeuPrimaryButton>
        </div>
        <div>
          {members.map((m, i) => (
            <div key={m.id} className={`flex items-center gap-3.5 py-3.5 ${i < members.length - 1 ? "border-b border-[#e2e6ee]" : ""}`}>
              <span className="w-9 h-9 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-[12px] font-semibold text-white shrink-0">
                {initials(m.name || m.email)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13.5px] font-semibold text-[#334155] truncate">{m.name}</p>
                <p className="text-[12.5px] text-[#8792a6] truncate">{m.email}</p>
              </div>
              <NeuChip>{m.role}</NeuChip>
              <span className="text-[12px] text-[#9aa6b8] capitalize w-16 text-right">{m.status}</span>
              {m.role !== "Owner" ? (
                <button onClick={() => remove(m.id)} className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#e11d48]" title="Remove">
                  <Trash2 size={15} />
                </button>
              ) : (
                <span className="w-8" />
              )}
            </div>
          ))}
        </div>
      </div>

      <InviteModal open={invite} onClose={() => setInvite(false)} onAdded={load} />
    </>
  );
}

export const ViewWorkspaceSettings = () => {
  const [tab, setTab] = useState(0);
  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-9 sm:py-8">
      <div className="max-w-[940px]">
        <SettingsHeader title="Workspace" subtitle="Manage your workspace and team." />
        <Tabs tabs={["Overview", "Members"]} active={tab} onSelect={setTab} />
        {tab === 0 ? <Overview /> : <Members />}
      </div>
    </div>
  );
};
