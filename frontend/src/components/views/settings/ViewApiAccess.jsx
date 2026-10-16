import { useEffect, useState } from "react";
import { Trash2, Zap, Sparkles, Bot, Globe, MapPin, Check } from "lucide-react";

import { missionApi } from "../../../missionApi";
import { useToast } from "../../ui/Toast.jsx";
import {
  neuShellCls,
  SettingsHeader,
  NeuSectionTitle,
  neuInput,
  NeuPrimaryButton,
  NeuDangerButton,
  NeuChip,
} from "./SettingsShared.jsx";

const PROVIDERS = [
  { key: "groq", field: "groq_api_key", label: "Groq", icon: Zap, tint: "text-[#f0790f]", hint: "Primary LLM · 14,400 req/day free", placeholder: "gsk_…" },
  { key: "gemini", field: "gemini_api_key", label: "Google Gemini", icon: Sparkles, tint: "text-[#1a73e8]", hint: "Fallback LLM · 1M tokens/day free", placeholder: "AIza…" },
  { key: "openai", field: "openai_api_key", label: "OpenAI", icon: Bot, tint: "text-[#0a9d6e]", hint: "Optional premium LLM", placeholder: "sk-…" },
  { key: "serper", field: "serper_api_key", label: "Serper", icon: Globe, tint: "text-[#4f46e5]", hint: "Powers web search · 2,500/mo free", placeholder: "…" },
  { key: "google_places", field: "google_places_api_key", label: "Google Places", icon: MapPin, tint: "text-[#16a34a]", hint: "Powers maps lookups", placeholder: "…" },
];

export const ViewApiAccess = () => {
  const toast = useToast();
  const [masked, setMasked] = useState({});
  const [drafts, setDrafts] = useState({});

  const load = () => missionApi.apiKeys().then(setMasked).catch((e) => toast.error(e.message));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  async function saveOne(p) {
    const value = (drafts[p.key] || "").trim();
    if (!value) return;
    try {
      await missionApi.saveApiKeys({ [p.field]: value });
      setDrafts((d) => ({ ...d, [p.key]: "" }));
      toast.success(`${p.label} key saved.`);
      load();
    } catch (e) { toast.error(e.message); }
  }

  async function remove(p) {
    try {
      await missionApi.deleteApiKey(p.key);
      toast.success(`${p.label} key removed.`);
      load();
    } catch (e) { toast.error(e.message); }
  }

  return (
    <div className={neuShellCls}>
      <div className="max-w-[820px]">
        <SettingsHeader
          title="API Access"
          subtitle="Connect your own LLM and tool providers. Keys are encrypted at rest."
        />

        <div className="neu-card p-7">
          <NeuSectionTitle>Provider Keys</NeuSectionTitle>
          <p className="text-[13px] text-[#8792a6] mt-0.5 mb-5">
            Agents run your missions on your own quota. Without any key, Orion falls back to local Ollama.
          </p>

          <div className="flex flex-col gap-5">
            {PROVIDERS.map((p) => {
              const current = masked[p.key];
              return (
                <div key={p.key} className="flex items-center gap-4">
                  <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0 ${p.tint}`}>
                    <p.icon size={18} strokeWidth={2} />
                  </span>
                  <div className="w-[170px] shrink-0">
                    <div className="flex items-center gap-2">
                      <p className="text-[14px] font-semibold text-[#334155]">{p.label}</p>
                      {current && <NeuChip className="!text-[#16a34a]"><Check size={11} strokeWidth={3} /> Set</NeuChip>}
                    </div>
                    <p className="text-[12px] text-[#9aa6b8] mt-0.5 truncate">{p.hint}</p>
                  </div>
                  <div className="flex-1 flex items-center gap-2.5">
                    {current ? (
                      <>
                        <code className="flex-1 neu-inset text-[13px] font-mono text-[#5b6678] px-3.5 py-2.5">{current}</code>
                        <NeuDangerButton onClick={() => remove(p)}><Trash2 size={14} /> Remove</NeuDangerButton>
                      </>
                    ) : (
                      <>
                        <input
                          type="password"
                          className={`${neuInput} flex-1 h-10`}
                          placeholder={p.placeholder}
                          value={drafts[p.key] || ""}
                          onChange={(e) => setDrafts((d) => ({ ...d, [p.key]: e.target.value }))}
                          onKeyDown={(e) => e.key === "Enter" && saveOne(p)}
                        />
                        <NeuPrimaryButton className="h-10 px-4" onClick={() => saveOne(p)}>Save</NeuPrimaryButton>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <p className="text-[12.5px] text-[#9aa6b8] mt-4 leading-relaxed">
          Keys are encrypted and shown masked after saving. They are never sent back to the browser in full.
        </p>
      </div>
    </div>
  );
};
