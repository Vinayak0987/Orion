import { useState } from "react";
import {
  BookOpen, Code2, MessageSquareText, Bug, ChevronDown,
  Rocket, Boxes, KeyRound, Wrench, Activity, Mail,
} from "lucide-react";
import {
  neuShellCls,
  SettingsHeader,
  NeuSectionTitle,
  NeuPrimaryButton,
  NeuGhostButton,
  NeuField,
  neuInput,
} from "./SettingsShared.jsx";
import { Modal } from "../../ui/Modal.jsx";
import { useToast } from "../../ui/Toast.jsx";

const quickLinks = [
  { key: "docs", icon: BookOpen, title: "Documentation", sub: "Guides and how-tos",
    body: "Orion's documentation covers getting started, creating agents, connecting tools, and understanding mission traces. Full docs open in a dedicated panel — for now, the FAQ below answers the most common questions." },
  { key: "source", icon: Code2, title: "Source Code", sub: "The Orion repository",
    body: "Orion is built with FastAPI, React, SQLite, ChromaDB and MongoDB — a mission engine, agent runtime, tool registry, and this settings layer. Repository access will be linked here." },
  { key: "issue", icon: Bug, title: "Report an Issue", sub: "Found a bug? Let us know", isForm: true },
  { key: "community", icon: MessageSquareText, title: "Community", sub: "Discuss and get help",
    body: "Join other builders using Orion to share agent setups, tool integrations, and workflows. The community space will be linked here." },
];

const FAQS = [
  { icon: Rocket, q: "How do I run my first mission?", a: "Go to the Command Center, type a goal in plain language (e.g. “Research my top 5 competitors and suggest pricing”), and press send. Orion plans the work into tasks, assigns agents, and runs it live — the result appears in a couple of minutes." },
  { icon: Boxes, q: "What is an agent, and can I create my own?", a: "An agent is an AI worker with a name, instructions, tools it can call, and optional sub-agents. Orion ships with defaults; you'll be able to create and customize your own from the Agents section." },
  { icon: KeyRound, q: "Where do I add my API keys and are they safe?", a: "Settings → API Access. Keys are encrypted at rest and only shown masked. Your missions run on your own quota. Without any key, Orion falls back to a local Ollama model at zero cost." },
  { icon: Wrench, q: "How do tools and MCP servers work?", a: "Tools let agents act in the real world — web search, maps, document search, custom HTTP endpoints. You can also connect MCP servers. Each agent has an allowed list of tools." },
  { icon: Activity, q: "How do I see what an agent actually did?", a: "Every mission records a full execution trace — each LLM and tool call with tokens, latency and cost. Open a mission from the Missions section, or use Observability for aggregate metrics." },
  { icon: Mail, q: "Is Orion really free?", a: "Yes. It runs on free-tier LLM providers plus a local Ollama fallback. No subscription, no card. Your only limits are the free tiers of the API keys you bring." },
];

function ReportIssueForm({ onClose }) {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  function submit() {
    if (!title.trim()) return;
    toast.success("Thanks — your report has been noted.");
    onClose();
  }
  return (
    <>
      <div className="flex flex-col gap-3.5">
        <NeuField label="Summary"><input className={neuInput} placeholder="Short summary of the issue" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus /></NeuField>
        <NeuField label="Details"><textarea rows={4} className={`${neuInput} h-auto py-3 resize-none`} placeholder="What happened? Steps to reproduce, what you expected…" value={details} onChange={(e) => setDetails(e.target.value)} /></NeuField>
      </div>
      <div className="flex items-center justify-end gap-2.5 mt-5">
        <NeuGhostButton onClick={onClose}>Cancel</NeuGhostButton>
        <NeuPrimaryButton className="h-9 px-4" onClick={submit}><Bug size={14} /> Submit</NeuPrimaryButton>
      </div>
    </>
  );
}

function FaqItem({ item, open, onToggle }) {
  const Icon = item.icon;
  return (
    <div className="neu-card overflow-hidden">
      <button type="button" onClick={onToggle} className="w-full flex items-center gap-3 px-5 py-4 text-left">
        <span className={`neu-circle w-9 h-9 rounded-xl grid place-items-center shrink-0 ${open ? "text-[#4f46e5]" : "text-[#7b8699]"}`}>
          <Icon size={16} strokeWidth={2} />
        </span>
        <span className="flex-1 text-[13.5px] font-semibold text-[#334155]">{item.q}</span>
        <ChevronDown size={17} className={`text-[#8792a6] shrink-0 transition-transform duration-200 ${open ? "rotate-180 text-[#4f46e5]" : ""}`} />
      </button>
      <div className={`grid transition-all duration-200 ease-out ${open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
        <div className="overflow-hidden">
          <p className="px-5 pb-5 pl-[68px] text-[13px] text-[#5b6678] leading-relaxed">{item.a}</p>
        </div>
      </div>
    </div>
  );
}

export const ViewHelpSupport = () => {
  const [openFaq, setOpenFaq] = useState(0);
  const [modal, setModal] = useState(null);

  return (
    <div className={neuShellCls}>
      <div className="max-w-[900px]">
        <SettingsHeader title="Help & Support" subtitle="Guides, docs, and answers to common questions." />

        <NeuSectionTitle className="mb-3">Quick Links</NeuSectionTitle>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          {quickLinks.map((l) => {
            const Icon = l.icon;
            return (
              <button key={l.key} onClick={() => setModal(l)} className="neu-card-hover p-4 text-left flex items-center gap-3">
                <span className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#4f46e5] shrink-0">
                  <Icon size={17} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="text-[13px] font-semibold text-[#334155] leading-tight">{l.title}</p>
                  <p className="text-[11.5px] text-[#8792a6] mt-0.5 truncate">{l.sub}</p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex items-end justify-between mb-3">
          <NeuSectionTitle>Frequently Asked Questions</NeuSectionTitle>
          <button type="button" onClick={() => setOpenFaq(openFaq === null ? 0 : null)} className="text-[12.5px] font-semibold text-[#4f46e5] hover:text-[#4338ca] transition-colors">
            {openFaq === null ? "Expand first" : "Collapse all"}
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {FAQS.map((item, i) => (
            <FaqItem key={item.q} item={item} open={openFaq === i} onToggle={() => setOpenFaq(openFaq === i ? null : i)} />
          ))}
        </div>
      </div>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal?.title} subtitle={modal?.sub} icon={modal?.icon}>
        {modal?.isForm ? <ReportIssueForm onClose={() => setModal(null)} /> : <p>{modal?.body}</p>}
      </Modal>
    </div>
  );
};
