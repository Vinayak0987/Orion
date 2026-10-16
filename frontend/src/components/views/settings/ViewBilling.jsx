import { Check, KeyRound, Infinity as InfinityIcon } from "lucide-react";

import {
  neuShellCls,
  SettingsHeader,
  NeuSectionTitle,
  NeuPrimaryButton,
  NeuChip,
} from "./SettingsShared.jsx";

const included = [
  "Unlimited missions — run as many as you like",
  "All built-in agents and tools",
  "Bring your own LLM keys (Groq, Gemini, OpenAI)",
  "Local Ollama fallback — zero cost",
  "Full observability and history",
];

export const ViewBilling = ({ onManageKeys }) => (
  <div className={neuShellCls}>
    <div className="max-w-[820px]">
      <SettingsHeader title="Billing" subtitle="Orion is free — you bring your own API keys." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
        <div className="neu-card p-7">
          <div className="flex items-center gap-3.5 mb-5">
            <span className="neu-circle w-12 h-12 rounded-2xl grid place-items-center text-[#4f46e5]">
              <InfinityIcon size={22} strokeWidth={2} />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-[15px] font-semibold text-[#334155]">Free</p>
                <NeuChip className="!text-[#16a34a]">Active</NeuChip>
              </div>
              <p className="text-[11.5px] text-[#9aa6b8] font-medium uppercase tracking-wide mt-0.5">Current Plan</p>
            </div>
          </div>
          <p className="text-[30px] font-semibold text-[#334155] mb-2 tracking-[-0.5px]">
            ₹0 <span className="text-[14px] font-medium text-[#9aa6b8]">/ forever</span>
          </p>
          <p className="text-[13px] text-[#8792a6] mb-6 leading-relaxed">
            Orion runs on free-tier LLM providers. Add your own API keys, or run a local model with Ollama.
          </p>
          <NeuPrimaryButton className="w-full" onClick={onManageKeys}>
            <KeyRound size={16} /> Manage API Keys
          </NeuPrimaryButton>
        </div>

        <div className="neu-card p-7">
          <NeuSectionTitle className="mb-5">What's included</NeuSectionTitle>
          <ul className="flex flex-col gap-3.5">
            {included.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <span className="neu-circle w-6 h-6 rounded-full grid place-items-center text-[#16a34a] shrink-0 mt-0.5">
                  <Check size={12} strokeWidth={3} />
                </span>
                <span className="text-[13.5px] text-[#5b6678] leading-snug">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <p className="text-[12.5px] text-[#9aa6b8] mt-5 leading-relaxed">
        No credit card, no subscription, no invoices. Usage is limited only by your own API providers' free tiers.
      </p>
    </div>
  </div>
);
