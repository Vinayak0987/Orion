// LandingPage — faithful React port of the reference orionai-landing.html.
// Single scrollable page, 9 sections, shown between the intro splash and login.
// Interactions (theme, billing period, industry filter, resource tabs + search,
// how-it-works active step) are React state. Nav CTAs are lifted via props:
//   onGetStarted -> /signup, onSignIn -> /login.

import { useMemo, useState } from "react";

import useAuthTheme from "../auth/useAuthTheme";
import LandingCircuit from "./LandingCircuit";
import { Badges, Ic, IconSprite, Shield } from "./landingVisuals";
import "./landing.css";

// -------- data ----------------------------------------------------------- //
const INDUSTRIES = [
  ["bag", "Retail & eCommerce", "Market research, inventory, customer insights"],
  ["activity", "Healthcare", "Research, compliance, operations planning"],
  ["landmark", "Finance", "Analysis, risk assessment, report generation"],
  ["home", "Real Estate", "Market analysis, property research, investment planning"],
  ["factory", "Manufacturing", "Supply chain, operations, process optimization"],
  ["cap", "Education", "Research, content creation, learning experiences"],
  ["bed", "Hospitality", "Market analysis, operations, customer insights"],
  ["sparkles", "Custom Solution", "Create your own industry workflow"],
];

const FEATURES = [
  ["workflow", "Multi-Agent System", "Teams of specialized AI agents."],
  ["todo", "Dynamic Planning", "Turn any goal into a structured plan."],
  ["plug", "Tool Integration", "Connect 100+ tools and APIs."],
  ["db", "Memory & Knowledge", "Agents remember and learn over time."],
  ["users", "Collaboration", "Work with your team and AI together."],
  ["eye", "Observability", "Track performance, costs and results."],
  ["shield-check", "Security & Compliance", "Enterprise-ready and secure."],
  ["layers", "Custom Workflows", "Build your own agents and workflows."],
];

const STEPS = [
  ["doc", "1. Define", "Tell Orion what you want to achieve."],
  ["chart", "2. Plan", "Orion breaks it down and creates a strategy."],
  ["play", "3. Execute", "AI agents use tools and data to get work done."],
  ["chart", "4. Get Results", "Track progress and achieve your goals."],
];

const PLANS = [
  { n: "Free", s: "Get started with Orion", m: 0, y: 0, f: ["Basic agents", "Community support", "Limited tool access"], cta: "Get Started" },
  { n: "Starter", s: "For individuals", m: 1999, y: 1599, f: ["More agents", "More tool integrations", "Basic analytics", "Email support"], cta: "Get Started" },
  { n: "Pro", s: "For growing teams", m: 4999, y: 3999, pop: true, f: ["Unlimited agents", "Advanced analytics", "Team collaboration", "Priority support"], cta: "Get Started" },
  { n: "Enterprise", s: "For large organizations", custom: true, f: ["Custom solutions", "Dedicated support", "Advanced security", "SLA & compliance"], cta: "Contact Sales" },
];

const RES = [
  { c: "Guide", t: "Getting Started with Orion", d: "Learn the basics and set up your first agents.", m: "5 min read", th: 1, tab: "Guides" },
  { c: "Blog", t: "How AI Agents Transform Businesses", d: "Real-world examples and insights.", m: "8 min read", th: 2, tab: "Blog" },
  { c: "Case Study", t: "Scaling Operations with Orion", d: "How a retail brand reduced costs by 60%.", m: "6 min read", th: 3, tab: "Case Studies" },
  { c: "Webinar", t: "Building Custom Agents", d: "Live demo and Q&A session.", m: "45 min", th: 4, tab: "Webinars" },
  { c: "Docs", t: "Orion Documentation", d: "Setup, agents, tools and API reference.", m: "Reference", th: 1, tab: "Documentation", extra: true },
];
const TABS = ["All", "Blog", "Guides", "Documentation", "Case Studies", "Webinars"];

const NODES = [
  { icon: "plan", label: "Plan", style: { left: "22%", top: "20%" } },
  { icon: "search", label: "Research", style: { left: "67%", top: "12%" } },
  { icon: "users", label: "Collaborate", below: true, style: { left: "10%", top: "50%" } },
  { icon: "shield-check", label: "Operate", style: { left: "83%", top: "49%" } },
  { icon: "trend", label: "Grow", style: { left: "22%", top: "81%" } },
  { icon: "zap", label: "Automate", style: { left: "70%", top: "85%" } },
];

const inr = (n) => "\u20B9" + n.toLocaleString("en-IN");

export default function LandingPage({ onGetStarted, onSignIn }) {
  const { theme, setTheme } = useAuthTheme();
  const isDark = theme !== "light";

  const [period, setPeriod] = useState("m");
  const [industry, setIndustry] = useState("all");
  const [tab, setTab] = useState("All");
  const [query, setQuery] = useState("");
  const [activeStep, setActiveStep] = useState(0);

  const solutions = useMemo(
    () => INDUSTRIES.filter((i) => industry === "all" || i[1] === industry || i[1] === "Custom Solution"),
    [industry]
  );

  const resources = useMemo(() => {
    const term = query.trim().toLowerCase();
    return RES.filter((r) => {
      const inTab = tab === "All" ? !r.extra : r.tab === tab;
      const inQ = !term || (r.t + " " + r.d + " " + r.c).toLowerCase().includes(term);
      return inTab && inQ;
    });
  }, [tab, query]);

  return (
    <div className="landing-page" id="top">
      <IconSprite />

      {/* -------- Navigation -------- */}
      <header className="nav">
        <div className="wrap nav-in">
          <a className="brand" href="#top" aria-label="OrionAI home"><Ic n="logo" />OrionAI</a>
          <nav className="links" aria-label="Primary">
            <a href="#product">Product</a>
            <a href="#solutions">Solutions</a>
            <a href="#resources">Resources</a>
            <a href="#pricing">Pricing</a>
            <a href="#about">Company</a>
          </nav>
          <div className="nav-r">
            <button className="icon-btn" type="button" aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"} onClick={() => setTheme(isDark ? "light" : "dark-black")}>
              <Ic n={isDark ? "sun" : "moon"} />
            </button>
            <button className="btn btn-ghost btn-sm btn-signin" type="button" onClick={onSignIn}>Sign in</button>
            <button className="btn btn-primary btn-sm" type="button" onClick={onGetStarted}>Get Started <Ic n="arrow" /></button>
          </div>
        </div>
      </header>

      <main>
        {/* -------- 1. Hero -------- */}
        <section className="sec hero" id="home">
          <LandingCircuit variant="a" />
          <div className="wrap hero-grid">
            <div>
              <span className="pill"><Ic n="sparkles" />The Agentic Operating System</span>
              <h1 className="h1">From idea to<br />execution.<br />All in one place.</h1>
              <p className="lede">Orion is an agentic operating system that plans, researches, and operates with a team of AI agents to help your business grow.</p>
              <div className="cta-row">
                <button className="btn btn-primary" type="button" onClick={onGetStarted}>Get Started <Ic n="arrow" /></button>
                <a className="btn btn-ghost" href="#how"><Ic n="play-c" />Watch Demo</a>
              </div>
              <div className="checks">
                <span><Ic n="check" />No credit card required</span>
                <span><Ic n="check" />Setup in minutes</span>
                <span><Ic n="check" />Built for teams</span>
              </div>
            </div>

            <div className="orbit" role="img" aria-label="Orion at the center of Plan, Research, Operate, Automate, Grow and Collaborate">
              <svg className="rings" viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="27" />
                <circle className="spin" cx="50" cy="50" r="38" strokeDasharray="1.2 2.2" />
                <circle cx="50" cy="50" r="47" />
                <circle className="dot" cx="17" cy="33" r=".9" />
                <circle className="dot" cx="80" cy="24" r=".9" />
                <circle className="dot" cx="88" cy="70" r=".9" />
                <circle className="dot" cx="36" cy="92" r=".9" />
              </svg>
              <div className="orb">
                <Ic n="logo" />
                <b>Orion</b>
                <small>Your AI Workforce</small>
              </div>
              {NODES.map((nd) => (
                <div className={`node${nd.below ? " below" : ""}`} style={nd.style} key={nd.label}>
                  <div className="tile"><Ic n={nd.icon} /></div>
                  <span>{nd.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------- 2. Product overview -------- */}
        <section className="sec" id="product">
          <LandingCircuit variant="b" />
          <div className="wrap">
            <div className="po-grid">
              <div>
                <span className="eyebrow">Product Overview</span>
                <h2 className="h2">One platform.<br />Infinite possibilities.</h2>
                <p className="lede">Orion brings together planning, research, execution and monitoring in a single agentic system.</p>
                <div className="cta-row">
                  <button className="btn btn-primary" type="button" onClick={onGetStarted}>Get Started <Ic n="arrow" /></button>
                  <a className="btn btn-ghost" href="#how">See it in action</a>
                </div>
              </div>
              <div className="stackwrap">
                <div className="stack">
                  <div className="lrow"><span className="tile sm"><Ic n="logo" /></span><div><b>User Goal</b><small>Expand my business to a new city</small></div></div>
                  <div className="lrow"><span className="tile sm"><Ic n="plan" /></span><div><b>Plan</b><small>Break down goals into tasks</small></div></div>
                  <div className="lrow"><span className="tile sm"><Ic n="bot" /></span><div><b>Agents</b><small>Create and coordinate AI agents</small></div></div>
                  <div className="lrow"><span className="tile sm"><Ic n="wrench" /></span><div><b>Tools</b><small>Use external tools &amp; data sources</small></div></div>
                  <div className="lrow"><span className="tile sm"><Ic n="play-c" /></span><div><b>Execute</b><small>Run, monitor and optimize</small></div></div>
                </div>
                <div className="results" aria-label="Real results chart">
                  <small>Real Results</small>
                  <div className="bars"><i style={{ height: "30%" }} /><i style={{ height: "52%" }} /><i style={{ height: "76%" }} /><i style={{ height: "100%" }} /></div>
                </div>
              </div>
            </div>
            <div className="stats">
              <div className="stat"><span className="tile"><Ic n="gauge" /></span><div><b>10x</b><small>Faster execution</small></div></div>
              <div className="stat"><span className="tile"><Ic n="percent" /></span><div><b>60%</b><small>Lower operational cost</small></div></div>
              <div className="stat"><span className="tile"><Ic n="check-c" /></span><div><b>95%</b><small>Task success rate</small></div></div>
              <div className="stat"><span className="tile"><Ic n="clock" /></span><div><b>24/7</b><small>AI workforce</small></div></div>
            </div>
          </div>
        </section>

        {/* -------- 3. How it works -------- */}
        <section className="sec center" id="how">
          <LandingCircuit variant="c" />
          <div className="wrap">
            <span className="pill-plain">How it works</span>
            <h2 className="h2" style={{ marginTop: 20 }}>Turn your goals into real results<br />in four simple steps.</h2>
            <p className="lede">Orion handles the complexity. You focus on what matters.</p>
            <div className="steps">
              {STEPS.map((s, i) => (
                <div
                  className={`step${activeStep === i ? " active" : ""}`}
                  key={s[1]}
                  onMouseEnter={() => setActiveStep(i)}
                  onClick={() => setActiveStep(i)}
                >
                  <div className="circ"><Ic n={s[0]} /></div>
                  <b>{s[1]}</b>
                  <small>{s[2]}</small>
                </div>
              ))}
            </div>
            <div className="track" aria-hidden="true"><i /><i className="on" /><i /><i className="on" /><i /></div>
            <div className="how-cta"><a className="btn btn-blue" href="#features">See it in action <Ic n="arrow" /></a></div>
          </div>
        </section>

        {/* -------- 4. Solutions -------- */}
        <section className="sec" id="solutions">
          <LandingCircuit variant="d" />
          <div className="wrap">
            <div className="head">
              <div>
                <span className="eyebrow">Solutions</span>
                <h2 className="h2">Built for every industry.<br />Ready for what's next.</h2>
                <p className="lede">Orion adapts to your business needs with industry-specific workflows and agents.</p>
              </div>
              <div className="select">
                <select value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Filter by industry">
                  <option value="all">All Industries</option>
                  {INDUSTRIES.slice(0, 7).map((i) => <option key={i[1]} value={i[1]}>{i[1]}</option>)}
                </select>
                <Ic n="chev-d" />
              </div>
            </div>
            <div className="grid4">
              {solutions.map((i) => (
                <div className="card" key={i[1]}>
                  <div className="top"><span className="tile"><Ic n={i[0]} /></span><Ic n="chev-r" className="chev" /></div>
                  <h3>{i[1]}</h3>
                  <p>{i[2]}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------- 5. Features -------- */}
        <section className="sec" id="features">
          <LandingCircuit variant="e" />
          <div className="wrap">
            <div className="head">
              <div>
                <span className="eyebrow">Features</span>
                <h2 className="h2">Everything you need<br />to operate smarter.</h2>
                <p className="lede">Powerful capabilities to plan, build, and run your business with AI agents.</p>
              </div>
              <a className="btn btn-ghost btn-sm" href="#features">See all features <Ic n="arrow" /></a>
            </div>
            <div className="grid4">
              {FEATURES.map((f) => (
                <div className="card" key={f[1]}>
                  <div className="top"><span className="tile"><Ic n={f[0]} /></span><Ic n="chev-r" className="chev" /></div>
                  <h3>{f[1]}</h3>
                  <p>{f[2]}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------- 6. Pricing -------- */}
        <section className="sec" id="pricing">
          <LandingCircuit variant="c" />
          <div className="wrap">
            <div className="head">
              <div>
                <span className="eyebrow">Pricing</span>
                <h2 className="h2">Simple, transparent pricing.</h2>
                <p className="lede">Choose the plan that fits your needs. Scale as you grow.</p>
              </div>
              <div className="seg" role="group" aria-label="Billing period">
                <button type="button" className={period === "m" ? "on" : ""} onClick={() => setPeriod("m")}>Monthly</button>
                <button type="button" className={period === "y" ? "on" : ""} onClick={() => setPeriod("y")}>Yearly</button>
                <span className="save">Save 20%</span>
              </div>
            </div>
            <div className="plans">
              {PLANS.map((p) => (
                <div className={`plan${p.pop ? " pop" : ""}`} key={p.n}>
                  {p.pop && <span className="badge-pop">Popular</span>}
                  <h3>{p.n}</h3>
                  <div className="sub">{p.s}</div>
                  <div className="price">
                    {p.custom ? <b>Custom</b> : <><b>{inr(p[period])}</b><small>/month</small></>}
                  </div>
                  <ul>
                    {p.f.map((x) => <li key={x}><Ic n="check" />{x}</li>)}
                  </ul>
                  <button className={`btn ${p.pop ? "btn-primary" : "btn-ghost"}`} type="button" onClick={onGetStarted}>{p.cta}</button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------- 7. Resources -------- */}
        <section className="sec" id="resources">
          <LandingCircuit variant="b" />
          <div className="wrap">
            <div className="head">
              <div>
                <span className="eyebrow">Resources</span>
                <h2 className="h2">Learn, build, and grow<br />with Orion.</h2>
                <p className="lede">Guides, documentation, and insights to help you get the most out of Orion.</p>
              </div>
              <label className="search"><Ic n="search" /><input type="search" placeholder="Search resources..." aria-label="Search resources" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
            </div>
            <div className="tabs" role="tablist">
              {TABS.map((t) => (
                <button key={t} type="button" role="tab" aria-selected={tab === t} className={`tab${tab === t ? " on" : ""}`} onClick={() => setTab(t)}>{t}</button>
              ))}
            </div>
            <div className="grid4">
              {resources.length ? resources.map((r) => (
                <article className="card rcard" key={r.t}>
                  <div className={`thumb th${r.th}`} />
                  <div className="rb">
                    <span className="chip">{r.c}</span>
                    <h3>{r.t}</h3>
                    <p>{r.d}</p>
                    <div className="meta"><Ic n="clock" />{r.m}</div>
                  </div>
                </article>
              )) : (
                <div className="empty">No resources match your search. Try a different keyword or pick another category.</div>
              )}
            </div>
          </div>
        </section>

        {/* -------- 8. About -------- */}
        <section className="sec" id="about">
          <LandingCircuit variant="d" />
          <div className="wrap about-grid">
            <div>
              <span className="eyebrow">About Us</span>
              <h2 className="h2">Building the future<br />with AI agents.</h2>
              <p className="lede">Orion was founded with a simple mission: to make advanced AI accessible to every business. We believe in a world where anyone can turn their ideas into reality with the help of AI agents.</p>
              <div className="astats">
                <div><b>2024</b><small>Founded</small></div>
                <div><b>50K+</b><small>Users</small></div>
                <div><b>100+</b><small>Integrations</small></div>
                <div><b>Global</b><small>Remote Team</small></div>
              </div>
            </div>
            <div className="visual">
              <div className="sphere-wrap">
                <svg className="ring" viewBox="0 0 100 100" aria-hidden="true">
                  <circle cx="50" cy="50" r="46" /><circle cx="50" cy="50" r="38" strokeDasharray="1 2" />
                  <line x1="14" y1="30" x2="28" y2="44" /><line x1="86" y1="64" x2="72" y2="58" /><line x1="24" y1="82" x2="34" y2="70" />
                  <circle className="dot" cx="14" cy="30" r="1.2" /><circle className="dot" cx="86" cy="64" r="1.2" /><circle className="dot" cx="24" cy="82" r="1.2" /><circle className="dot" cx="80" cy="22" r="1" />
                </svg>
                <div className="sphere"><Ic n="logo" /><b>OrionAI</b></div>
                <span className="mini" style={{ width: 14, height: 14, left: "-6%", top: "22%" }} />
                <span className="mini" style={{ width: 20, height: 20, right: "-8%", top: "52%" }} />
                <span className="mini" style={{ width: 12, height: 12, left: "6%", bottom: "-2%" }} />
              </div>
              <blockquote className="quote" style={{ margin: 0 }}>“Our vision is a world where every business has an AI workforce.”<small>— Orion Team</small></blockquote>
            </div>
          </div>
        </section>

        {/* -------- 9. Security & Privacy -------- */}
        <section className="sec" id="security">
          <LandingCircuit variant="e" />
          <div className="wrap sec-grid">
            <div>
              <span className="eyebrow">Security &amp; Privacy</span>
              <h2 className="h2">Your data. Your control.</h2>
              <p className="lede">We take security, privacy, and compliance seriously so you can build with confidence.</p>
              <div className="list">
                <div className="lrow"><span className="tile sm"><Ic n="lock" /></span><div><b>Data Protection</b><small>Your data is encrypted end-to-end.</small></div><Ic n="chev-r" className="chev" /></div>
                <div className="lrow"><span className="tile sm"><Ic n="file-check" /></span><div><b>Compliance</b><small>SOC 2, GDPR and industry standards.</small></div><Ic n="chev-r" className="chev" /></div>
                <div className="lrow"><span className="tile sm"><Ic n="key" /></span><div><b>Access Control</b><small>Role-based permissions and SSO.</small></div><Ic n="chev-r" className="chev" /></div>
                <div className="lrow"><span className="tile sm"><Ic n="shield-check" /></span><div><b>Privacy by Design</b><small>We never use your data to train models.</small></div><Ic n="chev-r" className="chev" /></div>
              </div>
            </div>
            <div className="sec-r">
              <Shield />
              <div className="trust">
                <h3>Trusted &amp; Compliant</h3>
                <Badges />
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="foot">
        <div className="wrap">
          <span>© {new Date().getFullYear()} OrionAI. All rights reserved.</span>
          <nav aria-label="Footer"><a href="#how">How it works</a><a href="#features">Features</a><a href="#security">Security</a></nav>
        </div>
      </footer>
    </div>
  );
}
