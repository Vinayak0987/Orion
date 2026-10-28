import { useEffect, useState } from "react";
import { Sidebar } from "./components/layout/Sidebar.jsx";
import { Topbar } from "./components/layout/Topbar.jsx";
import { ViewDashboard } from "./components/views/ViewDashboard.jsx";
import { ViewCommandCenter } from "./components/views/ViewCommandCenter.jsx";
import { ViewMissions } from "./components/views/ViewMissions.jsx";
import { ViewMissionDetails } from "./components/views/ViewMissionDetails.jsx";
import { ViewApprovals } from "./components/views/ViewApprovals.jsx";
import { ViewNotifications } from "./components/views/ViewNotifications.jsx";
import { AgentsSection } from "./components/AgentsSection.jsx";
import { ToolsSection } from "./components/ToolsSection.jsx";
import { ViewCreateDepartment } from "./components/views/ViewCreateDepartment.jsx";
import { ViewDepartments } from "./components/views/ViewDepartments.jsx";
import { ViewDepartmentDetail } from "./components/views/ViewDepartmentDetail.jsx";
import { ViewKnowledgeBase } from "./components/views/ViewKnowledgeBase.jsx";
import { ViewUploadSources } from "./components/views/ViewUploadSources.jsx";
import { ViewMemoryOverview } from "./components/views/ViewMemoryOverview.jsx";
import { ViewMemoryDetails } from "./components/views/ViewMemoryDetails.jsx";
import { ViewMemorySettings } from "./components/views/ViewMemorySettings.jsx";
import { ViewOperationsOverview } from "./components/views/operations/ViewOperationsOverview.jsx";
import { ViewFinance as ViewFinanceOps } from "./components/views/operations/ViewFinance.jsx";
import { ViewSales } from "./components/views/operations/ViewSales.jsx";
import { ViewInventory } from "./components/views/operations/ViewInventory.jsx";
import { ViewMarketingCampaigns } from "./components/views/operations/ViewMarketingCampaigns.jsx";
import { ViewCustomersCRM } from "./components/views/operations/ViewCustomersCRM.jsx";
import { ViewEmployeesHR } from "./components/views/operations/ViewEmployeesHR.jsx";
import { ViewResearch } from "./components/views/operations/ViewResearch.jsx";
import { ViewSuppliers } from "./components/views/operations/ViewSuppliers.jsx";
import { ViewWebsite } from "./components/views/operations/ViewWebsite.jsx";
import { ViewObsDashboard } from "./components/views/observability/ViewObsDashboard.jsx";
import { ViewObsRuns } from "./components/views/observability/ViewObsRuns.jsx";
import { ViewObsTrace } from "./components/views/observability/ViewObsTrace.jsx";
import { ViewObsTools } from "./components/views/observability/ViewObsTools.jsx";
import { ViewObsLLM } from "./components/views/observability/ViewObsLLM.jsx";
import { ViewObsErrors } from "./components/views/observability/ViewObsErrors.jsx";
import { ViewObsEvaluations } from "./components/views/observability/ViewObsEvaluations.jsx";
import { ViewObsAudit } from "./components/views/observability/ViewObsAudit.jsx";
import { ViewObsWebsite } from "./components/views/observability/ViewObsWebsite.jsx";
import { SettingsSection } from "./components/SettingsSection.jsx";
import { ToastProvider } from "./components/ui/Toast.jsx";

export default function PlatformApp({ onLogout }) {
  const [activeView, setActiveView] = useState("dashboard");
  const [viewingDetails, setViewingDetails] = useState(false);
  const [detailMissionId, setDetailMissionId] = useState(null);
  const [agentsTab, setAgentsTab] = useState("overview");
  const [toolsTab, setToolsTab] = useState("overview");
  const [settingsTab, setSettingsTab] = useState("settings");
  const [memoryEntry, setMemoryEntry] = useState(null);
  const [activeDeptId, setActiveDeptId] = useState(null);

  // Match dist/index.html body classes while Platform is mounted.
  useEffect(() => {
    const cls = ["bg-[#F8FAFC]", "text-slate-800", "h-screen", "w-screen", "overflow-hidden"];
    document.body.classList.add(...cls);
    return () => document.body.classList.remove(...cls);
  }, []);

  const go = (id) => {
    setActiveView(id);
    setViewingDetails(false);
  };

  const handleNavClick = (id) => {
    if (id === "settings" || id.startsWith("settings-")) {
      setSettingsTab(id);
      setActiveView("settings");
      setViewingDetails(false);
      return;
    }
    // Agents is a flat nav item (no subtabs): always land on its Overview.
    if (id === "agents") setAgentsTab("overview");
    go(id);
  };

  const handleAgentsTabClick = (tabId) => {
    setActiveView("agents");
    setViewingDetails(false);
    setAgentsTab(tabId);
  };

  const handleToolsTabClick = (tabId) => {
    setActiveView("tools");
    setViewingDetails(false);
    setToolsTab(tabId);
  };

  const handleSettingsTabChange = (tabId) => {
    setSettingsTab(tabId);
    setActiveView("settings");
    setViewingDetails(false);
  };

  const renderContent = () => {
    if (viewingDetails) return <ViewMissionDetails missionId={detailMissionId} onBack={() => setViewingDetails(false)} onNavigate={go} onViewDetails={(id) => { setDetailMissionId(id); setViewingDetails(true); }} />;

    // Settings opened via Orion Workspace — in-page sidebar handles sub-pages
    if (activeView === "settings") {
      return <SettingsSection tab={settingsTab} onTabChange={handleSettingsTabChange} onLogout={onLogout} />;
    }

    switch (activeView) {
      case "dashboard":
        return <ViewDashboard />;
      case "command-center":
        return <ViewCommandCenter />;
      case "missions":
        return <ViewMissions onViewDetails={(id) => { setDetailMissionId(id); setViewingDetails(true); }} onNavigate={go} />;
      case "approvals":
        return <ViewApprovals />;
      case "notifications":
        return <ViewNotifications />;
      case "agents":
        return <AgentsSection tab={agentsTab} onTabChange={setAgentsTab} />;
      case "tools":
        return <ToolsSection tab={toolsTab} onTabChange={setToolsTab} />;

      // Departments
      case "create-department":
        return <ViewCreateDepartment onCreate={() => go("departments")} />;
      case "departments":
        return (
          <ViewDepartments
            onCreate={() => go("create-department")}
            onDepartmentClick={(d) => { setActiveDeptId(d.id); go("department-detail"); }}
          />
        );
      case "department-detail":
        return <ViewDepartmentDetail departmentId={activeDeptId} onBack={() => go("departments")} />;

      // Knowledge & Memory
      case "knowledge":
        return <ViewKnowledgeBase onUpload={() => go("knowledge-upload")} />;
      case "knowledge-upload":
        return <ViewUploadSources />;
      case "knowledge-memory-overview":
        return (
          <ViewMemoryOverview
            onOpenEntry={(entry) => { setMemoryEntry(entry); go("knowledge-memory-details"); }}
          />
        );
      case "knowledge-memory-details":
        return (
          <ViewMemoryDetails
            entry={memoryEntry}
            onBack={() => go("knowledge-memory-overview")}
            onDeleted={() => { setMemoryEntry(null); go("knowledge-memory-overview"); }}
          />
        );
      case "knowledge-memory-settings":
        return <ViewMemorySettings />;

      // Operations
      case "operations":
        return <ViewOperationsOverview />;
      case "operations-finance":
        return <ViewFinanceOps />;
      case "operations-sales":
        return <ViewSales />;
      case "operations-inventory":
        return <ViewInventory />;
      case "operations-marketing":
        return <ViewMarketingCampaigns />;
      case "operations-crm":
        return <ViewCustomersCRM />;
      case "operations-hr":
        return <ViewEmployeesHR />;
      case "operations-research":
        return <ViewResearch />;
      case "operations-suppliers":
        return <ViewSuppliers />;
      case "operations-website":
        return <ViewWebsite />;

      // Observability
      case "observability":
        return <ViewObsDashboard />;
      case "observability-runs":
        return <ViewObsRuns onOpenTrace={() => go("observability-trace")} />;
      case "observability-trace":
        return <ViewObsTrace onBack={() => go("observability-runs")} />;
      case "observability-tools":
        return <ViewObsTools />;
      case "observability-llm":
        return <ViewObsLLM />;
      case "observability-errors":
        return <ViewObsErrors />;
      case "observability-evaluations":
        return <ViewObsEvaluations />;
      case "observability-audit":
        return <ViewObsAudit />;
      case "observability-website":
        return <ViewObsWebsite />;

      default:
        return <ViewDashboard />;
    }
  };

  return (
    <ToastProvider>
      <div className="flex h-screen bg-[#F8FAFC]">
        <Sidebar
          activeView={activeView}
          viewingDetails={viewingDetails}
          onNavClick={handleNavClick}
          agentsTab={agentsTab}
          onAgentsTabClick={handleAgentsTabClick}
          toolsTab={toolsTab}
          onToolsTabClick={handleToolsTabClick}
          settingsOpen={activeView === "settings"}
        />
        <main className="flex-1 flex flex-col h-full min-w-0 bg-[#F8FAFC]">
          <Topbar onLogout={onLogout} onNavigate={handleNavClick} />
          <div className="flex-1 overflow-auto bg-[#F8FAFC]">{renderContent()}</div>
        </main>
      </div>
    </ToastProvider>
  );
}
