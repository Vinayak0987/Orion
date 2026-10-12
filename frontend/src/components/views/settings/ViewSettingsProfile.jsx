import { Pencil } from "lucide-react";
import {
  pageShellCls,
  cardCls,
  inputCls,
  Field,
  SettingsHeader,
  SaveButton,
  PrimaryButton,
} from "./SettingsShared.jsx";

export const ViewSettingsProfile = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1100px]">
      <SettingsHeader
        title="Profile"
        subtitle="Manage your personal information and preferences."
        action={<SaveButton />}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr] gap-5">
        <section className={`${cardCls} p-6`}>
          <div className="flex items-center gap-5 mb-7">
            <div className="w-20 h-20 rounded-full bg-[#4f46e5] grid place-items-center text-[22px] font-bold text-white shrink-0 shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
              AM
            </div>
            <PrimaryButton className="h-11 px-5 text-[14px]">Change Photo</PrimaryButton>
          </div>

          <div className="flex flex-col gap-5">
            <Field label="Full Name">
              <input className={inputCls} defaultValue="Abhishek Mishra" />
            </Field>
            <Field label="Email">
              <input className={inputCls} defaultValue="abhishek@example.com" />
            </Field>
            <Field label="Job Title">
              <input className={inputCls} defaultValue="AI/ML Engineer" />
            </Field>
            <Field label="Bio">
              <textarea
                rows={3}
                className={`${inputCls} h-auto py-3 resize-none`}
                defaultValue="Passionate about building AI agents and automation systems."
              />
            </Field>
          </div>
        </section>

        <section className={`${cardCls} p-6 h-fit`}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-[18px] font-extrabold text-[#0b1220]">Profile Preview</h2>
            <button className="flex items-center gap-1.5 text-[13px] font-semibold text-[#64748b] hover:text-[#4f46e5]">
              <Pencil size={14} /> Edit
            </button>
          </div>

          <div className="flex flex-col items-center text-center pt-2">
            <div className="w-24 h-24 rounded-full bg-[#4f46e5] grid place-items-center text-[26px] font-bold text-white mb-4 shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
              AM
            </div>
            <p className="text-[18px] font-bold text-[#0b1220]">Abhishek Mishra</p>
            <p className="text-[14px] text-[#64748b] mt-1">AI/ML Engineer</p>
            <p className="text-[14px] text-[#64748b] leading-relaxed mt-4 max-w-[240px]">
              Passionate about building AI agents and automation systems.
            </p>
          </div>
        </section>
      </div>
    </div>
  </div>
);
