// Section 5: Agents — content only; navigation lives in the sidebar.
// Breadcrumb shows directory location (Agents > Overview, etc.).
import { useState } from "react";
import { ViewAgents } from "./views/ViewAgents.jsx";
import { ViewCreateAgent } from "./views/ViewCreateAgent.jsx";
import { ViewAgentBuilder } from "./views/ViewAgentBuilder.jsx";
import { ViewAgentTemplates } from "./views/ViewAgentTemplates.jsx";
import { ViewAgentTesting } from "./views/ViewAgentTesting.jsx";
import { ViewAgentPerformance } from "./views/ViewAgentPerformance.jsx";
import { ViewAgentSettings } from "./views/ViewAgentSettings.jsx";
import { DirectoryLocation } from "./ui/DirectoryLocation.jsx";
import { AGENTS_SUBTABS } from "../data/navigation.js";

export const AgentsSection = ({ tab: controlledTab, onTabChange }) => {
  const [localTab, setLocalTab] = useState("overview");
  const tab = controlledTab ?? localTab;
  const setTab = (id) => {
    setLocalTab(id);
    onTabChange?.(id);
  };

  const current = AGENTS_SUBTABS.find((t) => t.id === tab) || AGENTS_SUBTABS[0];

  const renderScreen = () => {
    switch (tab) {
      case "overview":
        return <ViewAgents onCreateAgent={() => setTab("create")} />;
      case "create":
        return <ViewCreateAgent />;
      case "builder":
        return <ViewAgentBuilder />;
      case "templates":
        return <ViewAgentTemplates />;
      case "testing":
        return <ViewAgentTesting />;
      case "performance":
        return <ViewAgentPerformance />;
      case "settings":
        return <ViewAgentSettings />;
      default:
        return <ViewAgents onCreateAgent={() => setTab("create")} />;
    }
  };

  return (
    <div className="agents-section">
      <div className="px-6 pt-5 sm:px-7 pb-0 shrink-0">
        <DirectoryLocation
          className="mb-0"
          items={[
            { label: "Agents", onClick: () => setTab("overview") },
            { label: current.label },
          ]}
        />
      </div>
      <div className="agents-subtab-content">{renderScreen()}</div>
    </div>
  );
};
