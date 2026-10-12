// Agents Overview — converted from the standalone
// orion_agents_overview_LAST_GOOD_DOTTED_LAYOUT_TABLE_UPDATED.html
// Only the page CONTENT is kept here; the app's own Sidebar/Topbar are reused.
// All styling is scoped under the `.agents-page` wrapper (see index.css).

const UserGlyph = () => (
  <svg viewBox="0 0 32 32">
    <circle cx="16" cy="10.5" r="4.5" />
    <path d="M7 26c.7-5.5 3.7-8 9-8s8.3 2.5 9 8" />
  </svg>
);

const DEPARTMENTS = [
  { key: "marketing", name: "Marketing", count: "4 agents", color: "pink" },
  { key: "finance", name: "Finance", count: "5 agents", color: "green" },
  { key: "research", name: "Research", count: "4 agents", color: "purple" },
  { key: "operations", name: "Operations", count: "6 agents", color: "orange" },
  { key: "hr", name: "HR", count: "3 agents", color: "blue" },
];

const AGENT_ROWS = [
  {
    name: "Marketing Agent",
    dept: "Marketing",
    status: "active",
    statusLabel: "Active",
    missions: 12,
    rate: "96%",
    last: "2 min ago",
    iconClass: "icon-marketing",
    icon: (
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="8" r="3.2" />
        <path d="M5.5 19c.5-4 2.7-6 6.5-6s6 2 6.5 6" />
      </svg>
    ),
  },
  {
    name: "Content Creator",
    dept: "Marketing",
    status: "running",
    statusLabel: "Running",
    missions: 4,
    rate: "92%",
    last: "5 min ago",
    iconClass: "icon-content",
    icon: (
      <svg viewBox="0 0 24 24">
        <path d="M6 4h12v16H6z" />
        <path d="M9 8h6M9 12h6M9 16h4" />
      </svg>
    ),
  },
  {
    name: "Financial Analyst",
    dept: "Finance",
    status: "active",
    statusLabel: "Active",
    missions: 8,
    rate: "94%",
    last: "12 min ago",
    iconClass: "icon-finance",
    icon: (
      <svg viewBox="0 0 24 24">
        <path d="M5 19V9M10 19V5M15 19v-7M20 19V3" />
      </svg>
    ),
  },
  {
    name: "Risk Monitor",
    dept: "Finance",
    status: "idle",
    statusLabel: "Idle",
    missions: 3,
    rate: "88%",
    last: "1 hour ago",
    iconClass: "icon-risk",
    icon: (
      <svg viewBox="0 0 24 24">
        <path d="M12 3 20 7v5c0 4.7-3.1 7.6-8 9-4.9-1.4-8-4.3-8-9V7z" />
        <path d="M12 8v4M12 16h.01" />
      </svg>
    ),
  },
  {
    name: "Research Agent",
    dept: "Research",
    status: "active",
    statusLabel: "Active",
    missions: 10,
    rate: "91%",
    last: "3 hours ago",
    iconClass: "icon-research",
    icon: (
      <svg viewBox="0 0 24 24">
        <circle cx="10.5" cy="10.5" r="5.5" />
        <path d="m15 15 5 5" />
        <path d="M8 10.5h5M10.5 8v5" />
      </svg>
    ),
  },
];

const DeptGroup = ({ dept }) => (
  <div className={`dept-group ${dept.key}-group`}>
    <div className="dept-circle">
      <div className="dept-name">{dept.name}</div>
      <div className="dept-count">{dept.count}</div>
    </div>
    {["a1", "a2", "a3"].map((slot) => (
      <div key={slot} className={`agent-node ${dept.color} ${slot}`}>
        <div className="agent-inner">
          <UserGlyph />
        </div>
      </div>
    ))}
  </div>
);

export const ViewAgents = ({ onCreateAgent }) => (
  <div className="agents-page">
    <section className="content">
      <div className="page-head">
        <div>
          <div className="kicker"></div>
          <h1>Agents Overview</h1>
          <div className="subtitle">All agents across your workspace</div>
        </div>
        <button className="primary" onClick={onCreateAgent}>Create Agent</button>
      </div>

      {/* Stat cards */}
      <div className="stats">
        <div className="card stat">
          <div className="stat-label">Total Agents</div>
          <div className="stat-value">24</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Active</div>
          <div className="stat-value green">
            <span className="dot"></span>18
          </div>
        </div>
        <div className="card stat">
          <div className="stat-label">Running</div>
          <div className="stat-value blue">
            <span className="dot"></span>6
          </div>
        </div>
        <div className="card stat">
          <div className="stat-label">Needs Attention</div>
          <div className="stat-value red">2</div>
        </div>
      </div>

      {/* View toggle */}
      <div className="views">
        <div className="view selected">Organization View</div>
        <div className="view">List View</div>
      </div>

      {/* Organization map */}
      <div className="workspace exact-org">
        <svg className="org-map-svg" viewBox="0 0 1000 650" preserveAspectRatio="none">
          <path d="M500 280 C420 225 325 155 205 95" />
          <path d="M500 280 C580 225 675 155 795 95" />
          <path d="M500 280 C385 325 245 385 105 435" />
          <path d="M500 280 C615 325 755 385 895 435" />
          <path d="M500 280 C500 390 500 500 500 585" />
        </svg>

        {DEPARTMENTS.map((dept) => (
          <DeptGroup key={dept.key} dept={dept} />
        ))}

        {/* Orion Workspace center */}
        <div className="center-node">
          <div className="center-icon">
            <div className="center-icon-inner">
              <svg viewBox="0 0 32 32">
                <rect x="7" y="7" width="18" height="18" rx="3" />
                <rect x="11" y="11" width="10" height="10" rx="1.5" />
              </svg>
            </div>
          </div>
          <div className="center-title">Orion</div>
          <div className="center-sub">Workspace</div>
        </div>
      </div>

      {/* Agents table */}
      <div className="table-card">
        <div className="filters">
          <div className="select">
            All Departments <span>⌄</span>
          </div>
          <div className="search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="11" cy="11" r="6" />
              <path d="m16 16 4 4" />
            </svg>
            Search agents...
            <span style={{ marginLeft: "auto", color: "#a1a9b5" }}>⌄</span>
          </div>
          <div className="view-icons">
            <div className="square-icon selected">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <rect x="4" y="4" width="6" height="6" />
                <rect x="14" y="4" width="6" height="6" />
                <rect x="4" y="14" width="6" height="6" />
                <rect x="14" y="14" width="6" height="6" />
              </svg>
            </div>
            <div className="square-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M5 7h14M5 12h14M5 17h14" />
              </svg>
            </div>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Department</th>
              <th>Status</th>
              <th>Missions</th>
              <th>Success Rate</th>
              <th>Last Active</th>
            </tr>
          </thead>
          <tbody>
            {AGENT_ROWS.map((row) => (
              <tr key={row.name}>
                <td>
                  <div className="agent-cell">
                    <span className={`mini-icon ${row.iconClass}`}>{row.icon}</span>
                    {row.name}
                  </div>
                </td>
                <td>{row.dept}</td>
                <td>
                  <span className={`badge ${row.status}`}>{row.statusLabel}</span>
                </td>
                <td>{row.missions}</td>
                <td>{row.rate}</td>
                <td>{row.last}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="bottom-action">
          View all agents <span className="arrow">→</span>
        </div>
      </div>
    </section>
  </div>
);
