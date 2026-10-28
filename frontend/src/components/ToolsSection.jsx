// Tools section — content only; navigation lives in the sidebar.
import { ViewToolbox } from "./views/ViewToolbox.jsx";
import { ViewMcpServers } from "./views/ViewMcpServers.jsx";
import { ViewIntegrations } from "./views/ViewIntegrations.jsx";
import { ViewCustomTools } from "./views/ViewCustomTools.jsx";
import { ViewApiKeys } from "./views/ViewApiKeys.jsx";

export const ToolsSection = ({ tab: controlledTab, onTabChange }) => {
  const tab = controlledTab ?? "overview";
  const go = (id) => onTabChange?.(id);
  switch (tab) {
    case "mcp":
      return <ViewMcpServers />;
    case "integrations":
      return <ViewIntegrations />;
    case "custom":
      return <ViewCustomTools />;
    case "api-keys":
      return <ViewApiKeys />;
    case "overview":
    default:
      return <ViewToolbox onNavigate={go} />;
  }
};
