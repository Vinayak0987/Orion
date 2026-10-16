import { useEffect, useRef, useState } from "react";
import { Camera, Mail, Briefcase, CheckCircle2 } from "lucide-react";

import { authApi } from "../../../auth/authApi.js";
import { useToast } from "../../ui/Toast.jsx";
import { SettingsHeader, NeuField, neuInput, NeuPrimaryButton } from "./SettingsShared.jsx";

function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p[1]?.[0] || "")).toUpperCase() || "?";
}

function Avatar({ url, name, size = 72, text = "text-[20px]" }) {
  const s = { width: size, height: size };
  if (url) return <img src={url} alt={name} style={s} className="rounded-full object-cover" />;
  return (
    <div style={s} className={`rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center ${text} font-semibold text-white`}>
      {initials(name)}
    </div>
  );
}

export const ViewSettingsProfile = () => {
  const toast = useToast();
  const [form, setForm] = useState({ fullName: "", email: "", jobTitle: "", bio: "" });
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    authApi.me()
      .then((u) => {
        setForm({ fullName: u.full_name || "", email: u.email || "", jobTitle: u.job_title || "", bio: u.bio || "" });
        setAvatarUrl(u.avatar_url || null);
      })
      .catch((e) => toast.error(e.message || "Could not load your profile."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setSaving(true);
    try {
      const u = await authApi.updateMe({ fullName: form.fullName, email: form.email, jobTitle: form.jobTitle, bio: form.bio });
      setForm({ fullName: u.full_name, email: u.email, jobTitle: u.job_title || "", bio: u.bio || "" });
      toast.success("Profile saved.");
    } catch (e) {
      toast.error(e.message || "Could not save your profile.");
    } finally {
      setSaving(false);
    }
  }

  async function onPhoto(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const u = await authApi.uploadAvatar(file);
      setAvatarUrl(u.avatar_url || null);
      toast.success("Photo updated.");
    } catch (e) {
      toast.error(e.message || "Could not upload photo.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-9 sm:py-8">
      <div className="max-w-[940px]">
        <SettingsHeader
          title="Profile"
          subtitle="Manage your personal information."
          action={
            <NeuPrimaryButton onClick={save} disabled={saving || loading}>
              <CheckCircle2 size={16} /> {saving ? "Saving…" : "Save Changes"}
            </NeuPrimaryButton>
          }
        />

        <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-7">
          {/* Form — neumorphic card */}
          <div className="neu-card p-7">
            <h2 className="text-[15px] font-semibold text-[#334155]">Personal Information</h2>
            <p className="text-[13px] text-[#8792a6] mt-0.5 mb-6">This appears across your workspace.</p>

            {/* Avatar strip */}
            <div className="flex items-center gap-5 pb-6 mb-6">
              <div className="relative">
                {/* inset well framing the photo */}
                <div className="neu-avatar-well p-1.5 rounded-full">
                  <Avatar url={avatarUrl} name={form.fullName} size={72} />
                </div>
                <NeuIconButtonCamera onClick={() => fileRef.current?.click()} disabled={uploading} />
                <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={onPhoto} />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-[#334155]">{form.fullName || "Your name"}</p>
                <p className="text-[12.5px] text-[#8792a6] mt-0.5">
                  {uploading ? "Uploading…" : "PNG, JPEG, WebP or GIF · up to 10 MB"}
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-5">
              <NeuField label="Full Name">
                <input className={neuInput} value={form.fullName} onChange={(e) => set("fullName", e.target.value)} disabled={loading} placeholder="Your name" />
              </NeuField>
              <NeuField label="Email">
                <input className={neuInput} type="email" value={form.email} onChange={(e) => set("email", e.target.value)} disabled={loading} placeholder="you@example.com" />
              </NeuField>
              <NeuField label="Job Title">
                <input className={neuInput} value={form.jobTitle} onChange={(e) => set("jobTitle", e.target.value)} disabled={loading} placeholder="e.g. AI/ML Engineer" />
              </NeuField>
              <NeuField label="Bio">
                <textarea rows={3} className={`${neuInput} h-auto py-3 resize-none`} value={form.bio} onChange={(e) => set("bio", e.target.value)} disabled={loading} placeholder="A short bio about yourself." />
              </NeuField>
            </div>
          </div>

          {/* Preview — neumorphic card */}
          <div className="neu-card p-7 h-fit">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[15px] font-semibold text-[#334155]">Preview</h2>
              <span className="neu-raised text-[11px] font-semibold text-[#8792a6] rounded-full px-3 py-1">Live</span>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="neu-avatar-well p-2 rounded-full">
                <Avatar url={avatarUrl} name={form.fullName} size={92} text="text-[26px]" />
              </div>
              <p className="text-[17px] font-semibold text-[#334155] mt-5">{form.fullName || "Your Name"}</p>
              {form.jobTitle && (
                <span className="inline-flex items-center gap-1.5 text-[13px] text-[#4f46e5] font-medium mt-1.5">
                  <Briefcase size={13} /> {form.jobTitle}
                </span>
              )}
            </div>

            <div className="neu-inset mt-6 p-4 flex items-center gap-3">
              <span className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#4f46e5] shrink-0">
                <Mail size={15} />
              </span>
              <span className="text-[13px] text-[#5b6678] truncate">{form.email || "—"}</span>
            </div>

            {form.bio && (
              <div className="neu-inset mt-3 p-4">
                <p className="text-[13px] text-[#5b6678] leading-relaxed">{form.bio}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

/* Camera FAB — raised circle that presses in. */
function NeuIconButtonCamera({ onClick, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title="Change photo"
      className="neu-circle absolute -bottom-1 -right-1 w-9 h-9 rounded-full grid place-items-center text-[#4f46e5] disabled:opacity-60"
    >
      <Camera size={15} />
    </button>
  );
}
