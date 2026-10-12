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
import { ViewMarketing } from "./components/views/ViewMarketing.jsx";
import { ViewMarketingSettings } from "./components/views/ViewMarketingSettings.jsx";
import { ViewMarketingMembers } from "./components/views/ViewMarketingMembers.jsx";
import { ViewMarketingActivity } from "./components/views/ViewMarketingActivity.jsx";
import { ViewFinanceActivity } from "./components/views/ViewFinanceActivity.jsx";
import { ViewFinanceMembers } from "./components/views/ViewFinanceMembers.jsx";
import { ViewFinanceSettings } from "./components/views/ViewFinanceSettings.jsx";
import { ViewOperationsActivity } from "./components/views/ViewOperationsActivity.jsx";
import { ViewOperationsMembers } from "./components/views/ViewOperationsMembers.jsx";
import { ViewOperationsSettings } from "./components/views/ViewOperationsSettings.jsx";
import { ViewSalesDept } from "./components/views/ViewSalesDept.jsx";
import { ViewSalesActivity } from "./components/views/ViewSalesActivity.jsx";
import { ViewSalesMembers } from "./components/views/ViewSalesMembers.jsx";
import { ViewSalesSettings } from "./components/views/ViewSalesSettings.jsx";
import { ViewHRDept } from "./components/views/ViewHRDept.jsx";
import { ViewHRActivity } from "./components/views/ViewHRActivity.jsx";
import { ViewHRMembers } from "./components/views/ViewHRMembers.jsx";
import { ViewHRSettings } from "./components/views/ViewHRSettings.jsx";
import { ViewResearchDept } from "./components/views/ViewResearchDept.jsx";
import { ViewResearchActivity } from "./components/views/ViewResearchActivity.jsx";
import { ViewResearchMembers } from "./components/views/ViewResearchMembers.jsx";
import { ViewResearchSettings } from "./components/views/ViewResearchSettings.jsx";
import { ViewFinanceDept } from "./components/views/ViewFinanceDept.jsx";
import { ViewOperations } from "./components/views/ViewOperations.jsx";
import { ViewKnowledgeBase } from "./components/views/ViewKnowledgeBase.jsx";
import { ViewUploadSources } from "./components/views/ViewUploadSources.jsx";
import { ViewDocumentViewer } from "./components/views/ViewDocumentViewer.jsx";
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

export default function PlatformApp({ onLogout }) {
  const [activeView, setActiveView] = useState("dashboard");
  const [viewingDetails, setViewingDetails] = useState(false);
  const [agentsTab, setAgentsTab] = useState("overview");
  const [toolsTab, setToolsTab] = useState("overview");
  const [settingsTab, setSettingsTab] = useState("settings");

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
    if (viewingDetails) return <ViewMissionDetails />;

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
        return <ViewMissions onViewDetails={() => setViewingDetails(true)} />;
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
            onOpen={() => go("department-marketing")}
            onCreate={() => go("create-department")}
            onDepartmentClick={(deptName) => {
              const deptRoutes = {
                "Marketing": "department-marketing",
                "Finance": "department-finance",
                "Operations": "department-operations",
                "Sales": "department-sales",
                "HR": "department-hr",
                "Research": "department-research"
              };
              const route = deptRoutes[deptName];
              if (route) go(route);
            }}
          />
        );
      case "department-marketing":
        return <ViewMarketing onTabChange={(route) => go(route)} />;
      case "marketing-activity":
        return <ViewMarketingActivity />;
      case "marketing-members":
        return <ViewMarketingMembers />;
      case "marketing-settings":
        return <ViewMarketingSettings />;
      case "department-finance":
        return <ViewFinanceDept onTabChange={(route) => go(route)} />;
      case "finance-activity":
        return <ViewFinanceActivity />;
      case "finance-members":
        return <ViewFinanceMembers />;
      case "finance-settings":
        return <ViewFinanceSettings />;
      case "department-operations":
        return <ViewOperations onTabChange={(route) => go(route)} />;
      case "operations-activity":
        return <ViewOperationsActivity />;
      case "operations-members":
        return <ViewOperationsMembers />;
      case "operations-settings":
        return <ViewOperationsSettings />;
      case "department-sales":
        return <ViewSalesDept onTabChange={(route) => go(route)} />;
      case "sales-activity":
        return <ViewSalesActivity />;
      case "sales-members":
        return <ViewSalesMembers />;
      case "sales-settings":
        return <ViewSalesSettings />;
      case "department-hr":
        return <ViewHRDept onTabChange={(route) => go(route)} />;
      case "hr-activity":
        return <ViewHRActivity />;
      case "hr-members":
        return <ViewHRMembers />;
      case "hr-settings":
        return <ViewHRSettings />;
      case "department-research":
        return <ViewResearchDept onTabChange={(route) => go(route)} />;
      case "research-activity":
        return <ViewResearchActivity />;
      case "research-members":
        return <ViewResearchMembers />;
      case "research-settings":
        return <ViewResearchSettings />;

      // Knowledge & Memory
      case "knowledge":
        return (
          <ViewKnowledgeBase
            onOpenDoc={() => go("knowledge-document")}
            onUpload={() => go("knowledge-upload")}
          />
        );
      case "knowledge-upload":
        return <ViewUploadSources />;
      case "knowledge-document":
        return <ViewDocumentViewer onBack={() => go("knowledge")} />;
      case "knowledge-memory-overview":
        return <ViewMemoryOverview />;
      case "knowledge-memory-details":
        return <ViewMemoryDetails />;
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
        <Topbar onLogout={onLogout} />
        <div className="flex-1 overflow-auto bg-[#F8FAFC]">{renderContent()}</div>
      </main>
    </div>
  );
}
