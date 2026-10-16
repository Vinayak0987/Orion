import { useState } from "react";
import { Lock, ShieldCheck, KeyRound, MonitorSmartphone } from "lucide-react";

import { authApi } from "../../../auth/authApi.js";
import { useToast } from "../../ui/Toast.jsx";
import { Modal } from "../../ui/Modal.jsx";
import {
  neuShellCls,
  SettingsHeader,
  NeuSectionTitle,
  NeuRow,
  NeuGhostButton,
  NeuPrimaryButton,
  NeuChip,
  NeuField,
  neuInput,
} from "./SettingsShared.jsx";

function ChangePasswordModal({ open, onClose }) {
  const toast = useToast();
  const [v, setV] = useState({ current: "", next: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k, val) => setV((s) => ({ ...s, [k]: val }));

  async function submit(e) {
    e?.preventDefault();
    setError("");
    if (v.next !== v.confirm) return setError("New passwords do not match.");
    setBusy(true);
    try {
      await authApi.changePassword({ currentPassword: v.current, newPassword: v.next });
      toast.success("Password changed. Other sessions were signed out.");
      onClose();
      setV({ current: "", next: "", confirm: "" });
    } catch (err) {
      setError(err.message || "Could not change password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Change Password"
      subtitle="Choose a strong password you don't use elsewhere."
      icon={Lock}
      footer={
        <>
          <NeuGhostButton onClick={onClose}>Cancel</NeuGhostButton>
          <NeuPrimaryButton className="h-9 px-4" onClick={submit} disabled={busy}>{busy ? "Changing…" : "Change Password"}</NeuPrimaryButton>
        </>
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-3.5">
        <NeuField label="Current password">
          <input type="password" className={neuInput} value={v.current} onChange={(e) => set("current", e.target.value)} autoFocus />
        </NeuField>
        <NeuField label="New password" hint="At least 8 characters with uppercase, lowercase, and a number.">
          <input type="password" className={neuInput} value={v.next} onChange={(e) => set("next", e.target.value)} />
        </NeuField>
        <NeuField label="Confirm new password">
          <input type="password" className={neuInput} value={v.confirm} onChange={(e) => set("confirm", e.target.value)} />
        </NeuField>
        {error && <p className="text-[13px] text-rose-600 -mt-1">{error}</p>}
      </form>
    </Modal>
  );
}

export const ViewSecurity = () => {
  const [modal, setModal] = useState(false);

  return (
    <div className={neuShellCls}>
      <div className="max-w-[820px]">
        <SettingsHeader title="Security" subtitle="Secure your account and manage access." />

        <div className="neu-card p-7">
          <NeuSectionTitle className="mb-2">Authentication</NeuSectionTitle>
          <div>
            <NeuRow
              icon={Lock}
              title="Password"
              sub="Change the password for your account"
              action={<NeuGhostButton onClick={() => setModal(true)}>Change</NeuGhostButton>}
            />
            <NeuRow
              icon={ShieldCheck}
              title="Two-Factor Authentication"
              sub="Add an extra layer of security to your account"
              action={<NeuChip>Coming soon</NeuChip>}
            />
            <NeuRow
              icon={KeyRound}
              title="Passkeys"
              sub="Sign in with biometrics or a security key"
              action={<NeuChip>Coming soon</NeuChip>}
            />
            <NeuRow
              icon={MonitorSmartphone}
              title="Active Sessions"
              sub="Changing your password signs out all other sessions"
              action={<NeuChip>Coming soon</NeuChip>}
              last
            />
          </div>
        </div>
      </div>

      <ChangePasswordModal open={modal} onClose={() => setModal(false)} />
    </div>
  );
};
