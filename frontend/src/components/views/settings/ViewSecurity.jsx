import { Lock, ShieldCheck, KeyRound, MonitorSmartphone, Bell, Timer, Globe, ChevronDown } from "lucide-react";
import {
  SettingsHeader,
  SaveButton,
  Toggle,
  GhostButton,
  IconTile,
  pageShellCls,
  cardCls,
} from "./SettingsShared.jsx";

const Row = ({ icon: Icon, title, sub, right, last }) => (
  <div className={`flex items-center gap-4 py-5 ${!last ? "border-b border-[#eef2f8]" : ""}`}>
    <IconTile>
      <Icon size={19} strokeWidth={2} />
    </IconTile>
    <div className="flex-1 min-w-0">
      <p className="text-[15px] font-bold text-[#0b1220]">{title}</p>
      <p className="text-[13px] text-[#64748b] mt-0.5">{sub}</p>
    </div>
    <div className="flex items-center gap-3 shrink-0">{right}</div>
  </div>
);

export const ViewSecurity = () => (
  <div className={pageShellCls}>
    <div className="max-w-[920px]">
      <SettingsHeader
        title="Security"
        subtitle="Secure your account and manage access controls."
        action={<SaveButton />}
      />

      <div className="flex flex-col gap-5">
        <section className={`${cardCls} px-6`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] pt-6 mb-1">Authentication</h2>
          <Row
            icon={Lock}
            title="Password"
            sub="Set a new password to secure your account"
            right={<GhostButton>Change Password</GhostButton>}
          />
          <Row
            icon={ShieldCheck}
            title="Two Factor Authentication"
            sub="Add an extra layer of security"
            right={
              <>
                <Toggle on />
                <span className="text-[13.5px] font-semibold text-[#64748b]">Enabled</span>
                <GhostButton>Configure</GhostButton>
              </>
            }
          />
          <Row
            icon={KeyRound}
            title="Passkeys"
            sub="Use biometric or security keys"
            right={<GhostButton>Set Up</GhostButton>}
          />
          <Row
            icon={MonitorSmartphone}
            title="Active Sessions"
            sub="Manage your active sessions"
            right={<GhostButton>View Sessions</GhostButton>}
            last
          />
        </section>

        <section className={`${cardCls} px-6`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] pt-6 mb-1">Access Control</h2>
          <Row
            icon={Bell}
            title="Login Notifications"
            sub="Get notified of new logins"
            right={<Toggle on />}
          />
          <Row
            icon={Timer}
            title="Session Timeout"
            sub="Auto logout after inactivity"
            right={
              <button className="h-9 w-40 px-3 rounded-lg border border-[#e6ebf2] bg-white text-[13.5px] text-[#334155] flex items-center justify-between hover:bg-[#f5f8fc]">
                30 minutes <ChevronDown size={15} className="text-[#94a3b8]" />
              </button>
            }
          />
          <Row
            icon={Globe}
            title="IP Restriction"
            sub="Restrict access to specific IP addresses"
            right={<Toggle on={false} />}
            last
          />
        </section>
      </div>
    </div>
  </div>
);
