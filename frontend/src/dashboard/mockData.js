// Mock data for the OrionAI dashboard screens. The backend endpoints for this
// product surface do not exist yet; these fixtures let the UI render exactly as
// designed and are the single place to swap in live `api` calls later.

export const KPIS = [
  { icon: "missions", label: "Active Missions", value: "12", delta: "+20%", up: true },
  { icon: "agents", label: "Agents Online", value: "28", delta: "+12%", up: true },
  { icon: "approvals", label: "Pending Approvals", value: "5", delta: "-40%", up: false },
  { icon: "activity", label: "System Health", value: "98%", delta: "All systems operational", up: true, plain: true },
];

export const AGENT_NETWORK = [
  { id: "research", label: "Research" },
  { id: "finance", label: "Finance" },
  { id: "operations", label: "Operations" },
  { id: "product", label: "Product" },
  { id: "hr", label: "HR" },
  { id: "legal", label: "Legal" },
  { id: "marketing", label: "Marketing" },
];

export const RECENT_ACTIVITY = [
  { icon: "check", tone: "green", title: "Market research completed", sub: "Cafe location analysis", time: "10m ago" },
  { icon: "plus", tone: "blue", title: "New subtask generated", sub: "Competitor deep dive", time: "12m ago" },
  { icon: "alert", tone: "amber", title: "Approval requested", sub: "Marketing budget Q4", time: "28m ago" },
  { icon: "rocket", tone: "blue", title: "Agent deployed", sub: "Financial analyst agent", time: "1h ago" },
  { icon: "check", tone: "green", title: "Mission completed", sub: "Brand positioning study", time: "3h ago" },
];

export const KEY_INSIGHTS = [
  { text: "Thane shows 35% lower rent compared to Mumbai on average", time: "2h ago" },
  { text: "Competitor analysis reveals 3 untapped customer segments", time: "4h ago" },
];

export const PENDING_APPROVALS = [
  { title: "Marketing budget approval", sub: "₹2,50,000 for Q4 campaign", level: "High", tone: "red" },
  { title: "Hire data analyst agent", sub: "For market research", level: "Medium", tone: "amber" },
  { title: "Tool access request", sub: "Web scraping for research", level: "Low", tone: "green" },
];

export const CHAT_PLAN = [
  "Research prime locations in Thane",
  "Analyze competitors and market trends",
  "Study rental costs and property options",
  "Create pricing strategy and financial model",
  "Develop complete execution plan",
  "Identify required licenses and permits",
];

export const RUNNING_AGENTS = [
  { icon: "missions", name: "Research Agent", status: "Finding location data…", pct: 72 },
  { icon: "trend", name: "Analysis Agent", status: "Analyzing market trends…", pct: 54 },
  { icon: "building", name: "Finance Agent", status: "Building financial model…", pct: 38 },
  { icon: "missions", name: "Strategy Agent", status: "Planning execution roadmap…", pct: 21 },
];

export const QUICK_ACTIONS = ["Deep Research", "Create Plan", "Analyze Data", "Generate Strategy"];

export const MISSIONS = [
  { id: 1, name: "Expand to New City (Thane)", sub: "Research and execution plan", type: "Planning", agents: 3, progress: 70, status: "In Progress", last: "2 hours ago" },
  { id: 2, name: "Grocery Recommendation System", sub: "Build and deploy ML model", type: "Research", agents: 3, progress: 45, status: "In Progress", last: "5 hours ago" },
  { id: 3, name: "Competitor Analysis", sub: "Analyze top 5 competitors", type: "Research", agents: 4, progress: 100, status: "Completed", last: "1 day ago" },
  { id: 4, name: "User Research Study", sub: "Customer behaviour analysis", type: "Research", agents: 2, progress: 60, status: "In Progress", last: "2 days ago" },
  { id: 5, name: "Funding Strategy", sub: "Investor outreach and deck", type: "Planning", agents: 3, progress: 35, status: "In Progress", last: "3 days ago" },
  { id: 6, name: "Operations Optimization", sub: "Improve internal workflows", type: "Operations", agents: 3, progress: 20, status: "Not Started", last: "4 days ago" },
  { id: 7, name: "Brand Positioning", sub: "Develop new brand strategy", type: "Planning", agents: 2, progress: 100, status: "Completed", last: "5 days ago" },
  { id: 8, name: "Market Entry - Pune", sub: "Research and go-to-market plan", type: "Planning", agents: 3, progress: 0, status: "Not Started", last: "6 days ago" },
];

export const MISSION_TABS = ["All (12)", "Research (4)", "Planning (3)", "Operations (3)", "Completed (2)"];

export const APPROVAL_REQUESTS = [
  {
    id: "a1", title: "Marketing Budget Approval", agent: "Marketing Agent", level: "High", tone: "red",
    icon: "trend", time: "2 hours ago",
    context: "Requesting approval for Q4 2026 marketing campaign to launch in Thane outlet. This includes digital marketing, local advertising, and influencer partnerships.",
    actions: [
      { label: "Digital Advertising", value: "₹1,00,000" },
      { label: "Local Print & Outdoor", value: "₹75,000" },
      { label: "Influencer Partnerships", value: "₹50,000" },
      { label: "Content Creation", value: "₹25,000" },
    ],
    impact: ["Increase brand awareness in Thane by 60%", "Drive 2,000+ footfalls in first quarter", "Est. 10% higher revenue in first quarter"],
    evidence: [
      { name: "marketing_plan.pdf", size: "2.4 MB", icon: "doc" },
      { name: "competitor_benchmarks.xlsx", size: "1.1 MB", icon: "doc" },
      { name: "roi_projection.pdf", size: "800 KB", icon: "doc" },
    ],
  },
  { id: "a2", title: "Hire Data Analyst Agent", agent: "HR Agent", level: "Medium", tone: "amber", icon: "agents", time: "3 hours ago", context: "New team member for market research.", actions: [], impact: [], evidence: [] },
  { id: "a3", title: "Tool Access Request", agent: "Research Agent", level: "Medium", tone: "amber", icon: "tools", time: "5 hours ago", context: "Web scraping for competitor analysis.", actions: [], impact: [], evidence: [] },
  { id: "a4", title: "Content Strategy Plan", agent: "Content Agent", level: "Live", tone: "green", icon: "doc", time: "6 hours ago", context: "Blog and social media plan for launch.", actions: [], impact: [], evidence: [] },
  { id: "a5", title: "Partnership Agreement", agent: "Business Agent", level: "High", tone: "red", icon: "building", time: "1 day ago", context: "Collaboration with local suppliers.", actions: [], impact: [], evidence: [] },
];

export const NOTIF_TABS = ["All (20)", "Missions (8)", "Approvals (5)", "Agents (4)", "System (3)"];

export const NOTIFICATIONS = [
  { id: "n1", icon: "missions", tone: "blue", title: "Mission Update", sub: "Expand to New City progress rose to 70%", time: "2 hours ago", unread: true },
  { id: "n2", icon: "alert", tone: "amber", title: "Approval Required", sub: "Marketing budget approval requested", time: "4 hours ago", unread: true },
  { id: "n3", icon: "agents", tone: "green", title: "Agent Activity", sub: "Research Agent completed data collection", time: "6 hours ago" },
  { id: "n4", icon: "plus", tone: "blue", title: "New Subtask Generated", sub: "Competitor deep dive task created", time: "8 hours ago" },
  { id: "n5", icon: "knowledge", tone: "green", title: "Evidence Found", sub: "12 new documents added to knowledge base", time: "12 hours ago" },
  { id: "n6", icon: "check", tone: "green", title: "Mission Completed", sub: "Brand positioning analysis has been completed", time: "1 day ago" },
  { id: "n7", icon: "observability", tone: "blue", title: "System Update", sub: "New integration available: Shopify", time: "2 days ago" },
  { id: "n8", icon: "approvals", tone: "green", title: "Approval Approved", sub: "Hiring request for Data Analyst approved", time: "3 days ago" },
  { id: "n9", icon: "alert", tone: "red", title: "Agent Error (Recovered)", sub: "Web scraping failed then auto-retry succeeded", time: "3 days ago" },
  { id: "n10", icon: "trend", tone: "blue", title: "Weekly Summary", sub: "Your weekly activity report is ready", time: "1 week ago" },
];

export const NOTIF_DETAIL = {
  title: "Mission Update",
  time: "2 hours ago",
  body: "Expand to New City progress rose to 70%.",
  meta: [
    ["Mission", "Expand to New City (Thane)"],
    ["Status", "In Progress"],
    ["Progress", "70%"],
    ["Updated by", "Orion System"],
  ],
  detail: "The mission has made significant progress. Market research and competitor analysis phases are 80% complete. Financial analysis is in progress.",
  bars: [
    { label: "Market Research", pct: 100 },
    { label: "Competitor Analysis", pct: 80 },
    { label: "Financial Analysis", pct: 50 },
    { label: "Execution Planning", pct: 20 },
  ],
};

export const MISSION_DETAIL = {
  title: "Expand to New City (Thane)",
  sub: "Research market and create go-to-market plan for Thane cafe.",
  status: "In Progress",
  progress: 70,
  tabs: ["Overview", "Tasks", "Agents", "Tools", "Evidence", "Results", "Trace"],
  graph: [
    { id: "market", label: "Market Research", tasks: 3, children: [
      { label: "Location Analysis", state: "Completed" },
      { label: "Competitor Study", state: "In Progress" },
      { label: "Customer Insights", state: "Waiting" },
    ]},
    { id: "finance", label: "Financial Analysis", tasks: 3, children: [
      { label: "Rental Cost Analysis", state: "In Progress" },
      { label: "Pricing Strategy", state: "Waiting" },
      { label: "Revenue Modeling", state: "Waiting" },
    ]},
    { id: "exec", label: "Execution Planning", tasks: 4, children: [
      { label: "Legal Requirements", state: "Waiting" },
      { label: "Operations Setup", state: "Waiting" },
      { label: "Marketing Plan", state: "Waiting" },
      { label: "Launch Timeline", state: "Waiting" },
    ]},
  ],
  task: {
    name: "Competitor Study",
    agent: "Research Agent",
    status: "In Progress",
    started: "10:24 AM",
    percent: 45,
    description: "Analyze top cafes in Thane (pricing, menu, footfall, reviews).",
    tools: [{ name: "Web Search", icon: "globe" }, { name: "Map API", icon: "map" }, { name: "Web Scraper", icon: "tools" }],
    evidence: "12 documents · 3 datasets",
    output: "Found 6 major competitors. Average price range ₹100–₹250. Top 3 locations identified.",
    next: "Complete analysis and generate comparison report.",
  },
};

export const GREETING_DATE = "Thu, 19 Sep 2026";
