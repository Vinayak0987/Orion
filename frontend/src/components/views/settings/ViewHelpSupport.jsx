import {
  BookOpen,
  PlayCircle,
  Users,
  Headphones,
  ChevronRight,
  MessageSquareText,
  Clock,
  Timer,
} from "lucide-react";
import {
  SettingsHeader,
  PrimaryButton,
  IconTile,
  pageShellCls,
  cardCls,
} from "./SettingsShared.jsx";

const quickLinks = [
  { icon: BookOpen, title: "Documentation", sub: "Read guides and docs" },
  { icon: PlayCircle, title: "Video Tutorials", sub: "Watch step-by-step videos" },
  { icon: Users, title: "Community", sub: "Join the Orion community" },
  { icon: Headphones, title: "Contact Support", sub: "Get in touch with our team" },
];

const topicsLeft = ["Getting Started with Orion", "How to Create an Agent", "API Documentation"];
const topicsRight = ["Billing and Subscriptions", "Troubleshooting", "Security Best Practices"];

const TopicItem = ({ label, last }) => (
  <button
    className={`w-full flex items-center gap-3 py-3.5 text-left ${
      !last ? "border-b border-[#eef2f8]" : ""
    } group`}
  >
    <span className="w-1.5 h-1.5 rounded-full bg-[#4f46e5] shrink-0" />
    <span className="flex-1 text-[14px] font-medium text-[#334155] group-hover:text-[#4f46e5]">
      {label}
    </span>
    <ChevronRight size={16} className="text-[#94a3b8] group-hover:text-[#4f46e5]" />
  </button>
);

export const ViewHelpSupport = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1180px]">
      <SettingsHeader title="Help & Support" subtitle="Get help and support for Orion." />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">
        <div>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] mb-4">Quick Links</h2>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
            {quickLinks.map(({ icon: Icon, title, sub }) => (
              <button
                key={title}
                className={`${cardCls} p-4 text-left hover:border-[#c7d2fe] transition-colors flex items-start gap-3`}
              >
                <IconTile>
                  <Icon size={19} strokeWidth={2} />
                </IconTile>
                <div className="min-w-0">
                  <p className="text-[14px] font-bold text-[#0b1220] leading-tight">{title}</p>
                  <p className="text-[12.5px] text-[#64748b] mt-1">{sub}</p>
                </div>
              </button>
            ))}
          </div>

          <h2 className="text-[18px] font-extrabold text-[#0b1220] mb-4">Popular Topics</h2>
          <div className={`${cardCls} px-5 grid grid-cols-1 md:grid-cols-2 gap-x-8`}>
            <div>
              {topicsLeft.map((t, i) => (
                <TopicItem key={t} label={t} last={i === topicsLeft.length - 1} />
              ))}
            </div>
            <div>
              {topicsRight.map((t, i) => (
                <TopicItem key={t} label={t} last={i === topicsRight.length - 1} />
              ))}
            </div>
          </div>
        </div>

        <aside className={`${cardCls} p-6 h-fit`}>
          <div className="flex flex-col items-center text-center mb-5">
            <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center mb-3">
              <MessageSquareText size={26} strokeWidth={1.8} />
            </span>
            <p className="text-[16px] font-extrabold text-[#0b1220]">Need more help?</p>
            <p className="text-[13px] text-[#64748b] mt-1.5">
              Our support team is here to help you.
            </p>
          </div>
          <PrimaryButton className="w-full mb-5">Contact Support</PrimaryButton>

          <div className="flex items-start gap-3 py-3 border-t border-[#eef2f8]">
            <Clock size={18} className="text-[#4f46e5] mt-0.5 shrink-0" />
            <div>
              <p className="text-[13.5px] font-bold text-[#0b1220]">Support Hours</p>
              <p className="text-[12.5px] text-[#64748b] mt-0.5">Mon – Fri, 9:00 AM – 6:00 PM (IST)</p>
            </div>
          </div>
          <div className="flex items-start gap-3 py-3 border-t border-[#eef2f8]">
            <Timer size={18} className="text-[#4f46e5] mt-0.5 shrink-0" />
            <div>
              <p className="text-[13.5px] font-bold text-[#0b1220]">Average Response Time</p>
              <p className="text-[12.5px] text-[#64748b] mt-0.5">&lt; 4 hours</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
);
