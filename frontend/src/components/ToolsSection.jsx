// Tools section — content only; navigation lives in the sidebar.
// Breadcrumb shows directory location (Tools > All Tools, etc.).
import { useState } from "react";
import { ViewToolbox } from "./views/ViewToolbox.jsx";
import { ViewMcpServers } from "./views/ViewMcpServers.jsx";
import { ViewIntegrations } from "./views/ViewIntegrations.jsx";
import { ViewCustomTools } from "./views/ViewCustomTools.jsx";
import { ViewApiKeys } from "./views/ViewApiKeys.jsx";
import { ViewToolDetails } from "./views/ViewToolDetails.jsx";
import { getTool } from "./views/toolsData.js";
import { DirectoryLocation } from "./ui/DirectoryLocation.jsx";
import { TOOLS_SUBTABS } from "../data/navigation.js";

export const ToolsSection = ({ tab: controlledTab, onTabChange }) => {
  const [localTab, setLocalTab] = useState("overview");
  const [selectedTool, setSelectedTool] = useState(null);
  const tab = controlledTab ?? localTab;
  const setTab = (id) => {
    setSelectedTool(null);
    setLocalTab(id);
    onTabChange?.(id);
  };

  const openTool = (key) => setSelectedTool(getTool(key) || null);
  const closeTool = () => setSelectedTool(null);

  const current = TOOLS_SUBTABS.find((t) => t.id === tab) || TOOLS_SUBTABS[0];
  const crumbCurrent = selectedTool?.name || current.label;

  const renderScreen = () => {
    if (selectedTool) {
      return <ViewToolDetails tool={selectedTool} onBack={closeTool} />;
    }

    switch (tab) {
      case "overview":
        return <ViewToolbox onOpenTool={openTool} />;
      case "mcp":
        return <ViewMcpServers />;
      case "integrations":
        return <ViewIntegrations onOpenTool={openTool} />;
      case "custom":
        return <ViewCustomTools />;
      case "api-keys":
        return <ViewApiKeys />;
      default:
        return <ViewToolbox onOpenTool={openTool} />;
    }
  };

  return (
    <div className="tools-section">
      <div className="px-6 pt-5 sm:px-7 pb-0 shrink-0">
        <DirectoryLocation
          className="mb-0"
          items={
            selectedTool
              ? [
                  { label: "Tools", onClick: () => setTab("overview") },
                  { label: current.label, onClick: closeTool },
                  { label: crumbCurrent },
                ]
              : [
                  { label: "Tools", onClick: () => setTab("overview") },
                  { label: crumbCurrent },
                ]
          }
        />
      </div>
      <div className="tools-subtab-content">{renderScreen()}</div>
    </div>
  );
};
