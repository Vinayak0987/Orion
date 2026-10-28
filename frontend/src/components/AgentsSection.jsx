// Section 5: Agents — content only; navigation lives in the sidebar.
// Agents has NO sidebar subtabs: clicking "Agents" opens Overview directly.
// Create / Templates / Testing / Performance / Builder / Settings are all
// reached from inside the Overview page and show a "Back to Agents" bar.
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { ViewAgents } from "./views/ViewAgents.jsx";
import { ViewCreateAgent } from "./views/ViewCreateAgent.jsx";
import { ViewAgentBuilder } from "./views/ViewAgentBuilder.jsx";
import { ViewAgentTemplates } from "./views/ViewAgentTemplates.jsx";
import { ViewAgentTesting } from "./views/ViewAgentTesting.jsx";
import { ViewAgentPerformance } from "./views/ViewAgentPerformance.jsx";
import { ViewAgentSettings } from "./views/ViewAgentSettings.jsx";

// A thin back bar shown above any contextual (non-overview) agent view.
// Flex column: the bar is fixed at top, the child view keeps its own scroll.
const BackBar = ({ onBack, children }) => (
  <div className="neu-surface h-full flex flex-col min-h-0">
    <div className="px-6 pt-4 pb-1 sm:px-8 shrink-0">
      <button onClick={onBack}
        className="neu-btn-ghost inline-flex items-center gap-2 h-9 px-3.5 text-[13px] font-semibold text-[#5b6678]">
        <ArrowLeft size={16} /> Back to Agents
      </button>
    </div>
    <div className="flex-1 min-h-0">{children}</div>
  </div>
);

export const AgentsSection = ({ tab: controlledTab, onTabChange }) => {
  const [localTab, setLocalTab] = useState("overview");
  const [focusAgent, setFocusAgent] = useState(null); // agent id carried across tabs
  const tab = controlledTab ?? localTab;
  const setTab = (id) => { setLocalTab(id); onTabChange?.(id); };

  const openAgent = (a) => { setFocusAgent(a.id); setTab("settings"); };
  const testAgent = (a) => { setFocusAgent(a.id); setTab("testing"); };
  const editInBuilder = (id) => { setFocusAgent(id); setTab("builder"); };
  const back = () => { setFocusAgent(null); setTab("overview"); };

  switch (tab) {
    case "create":
      return <BackBar onBack={back}><ViewCreateAgent onCreated={back} /></BackBar>;
    case "builder":
      return <BackBar onBack={back}><ViewAgentBuilder presetAgentId={focusAgent} /></BackBar>;
    case "templates":
      return <BackBar onBack={back}><ViewAgentTemplates onCreated={back} /></BackBar>;
    case "testing":
      return <BackBar onBack={back}><ViewAgentTesting presetAgentId={focusAgent} /></BackBar>;
    case "performance":
      return <BackBar onBack={back}><ViewAgentPerformance presetAgentId={focusAgent} /></BackBar>;
    case "settings":
      return <BackBar onBack={back}><ViewAgentSettings presetAgentId={focusAgent} onDeleted={back} onEditBuilder={editInBuilder} /></BackBar>;
    case "overview":
    default:
      return (
        <ViewAgents
          onCreateAgent={() => setTab("create")}
          onOpenAgent={openAgent}
          onTestAgent={testAgent}
          onTemplates={() => setTab("templates")}
          onPerformance={(a) => { setFocusAgent(a.id); setTab("performance"); }}
        />
      );
  }
};
