"""
Two-page briefs condensing each full document.

Brief 1 — the architecture, for a reader with two minutes.
Brief 2 — the research proposal, for a reviewer deciding whether to read on.

Both are strictly two pages. Content is drawn from the full documents; nothing
is claimed here that is not claimed there.
"""

from datetime import date

from orion_style import (
    html_document, ACCENT, INK, INK_MUTED, RULE, PANEL_BG, FONT_STACK,
)
import orion_figures_light as fl
import orion_figures_dark as fd

BRIEF_CSS = f"""
<style>
@page {{ size: A4; margin: 14mm 14mm 13mm 14mm; }}
body {{ font-size: 8.5pt; line-height: 1.34; }}
h2 {{ font-size: 11pt; margin: 9px 0 4px 0; padding-bottom: 3px; }}
h3 {{ font-size: 9pt; margin: 7px 0 3px 0; }}
p {{ margin: 0 0 4px 0; }}
table {{ font-size: 7.5pt; margin: 4px 0 6px 0; }}
th {{ font-size: 7.1pt; padding: 3.5px 6px 3.5px 0; }}
td {{ padding: 3px 6px 3px 0; line-height: 1.3; }}
figure {{ margin: 5px 0 6px 0; }}
figcaption {{ font-size: 7.1pt; margin-top: 3px; line-height: 1.3; }}
.fig-sm svg {{ width: 66%; display: block; margin: 0 auto; }}
.fig-md svg {{ width: 86%; display: block; margin: 0 auto; }}
.callout {{ padding: 6px 9px; margin: 5px 0; font-size: 8.2pt; }}
.invariant {{ padding: 7px 10px; margin: 5px 0; font-size: 8.3pt; }}
.brief-head {{
  border-bottom: 2.5px solid {ACCENT};
  padding-bottom: 8px; margin-bottom: 10px;
}}
.brief-head .kicker {{
  font-size: 7.4pt; letter-spacing: 2px; text-transform: uppercase;
  color: {INK_MUTED}; font-weight: 700;
}}
.brief-head h1 {{
  font-size: 19pt; color: {ACCENT}; margin: 3px 0 3px 0; font-weight: 700;
  letter-spacing: -0.5px; line-height: 1.12;
}}
.brief-head .sub {{ font-size: 9.4pt; color: {INK}; line-height: 1.35; }}
.brief-head .meta {{ font-size: 7.4pt; color: {INK_MUTED}; margin-top: 5px; }}
.cols {{ display: flex; gap: 13px; }}
.cols > div {{ flex: 1; }}
.kv {{ font-size: 8.2pt; margin-bottom: 3px; }}
.kv b {{ color: {ACCENT}; }}
.status {{
  display: inline-block; font-size: 6.8pt; font-weight: 700; padding: 1px 5px;
  border-radius: 2px; letter-spacing: 0.5px; text-transform: uppercase;
}}
.st-built {{ background: #E3F5EC; color: #1E8A5F; }}
.st-spec {{ background: #F2F4FD; color: {ACCENT}; }}
.st-prov {{ background: #FDF3E3; color: #B07A26; }}
ul {{ margin: 0 0 5px 0; padding-left: 15px; }}
li {{ margin-bottom: 2.5px; }}
.rq {{ margin: 0 0 6px 0; font-size: 8.3pt; }}
.rq .tag {{ font-size: 7pt; padding: 1px 5px; margin-right: 5px; }}
.rq .falsify {{ font-size: 7.6pt; margin-top: 2px; padding-left: 9px; }}
</style>
"""


def head(kicker, title, sub, extra=""):
    return f"""
<div class="brief-head">
  <div class="kicker">{kicker}</div>
  <h1>{title}</h1>
  <div class="sub">{sub}</div>
  <div class="meta">Vinayak Maurya · Department of Computer Engineering ·
    University of Mumbai · {date.today().strftime('%d %B %Y')}{extra}</div>
</div>"""


# ============================== BRIEF 1 ====================================

def brief1():
    p = [BRIEF_CSS]
    p.append(head(
        "Architecture Brief · 2 pages",
        "Orion",
        "An AI Business Operating System. Five departments generate a company's "
        "opening state, then operate it continuously under human supervision — "
        "built so the parts that check the work cannot be captured by the parts "
        "doing it.",
        " · Full architecture document: 16 pp"))

    p.append('<h2>What it is</h2>')
    p.append("""<p>Orion has two layers. The <b>generation layer</b> turns one
      sentence into a complete founding business plan — positioning, unit
      economics, brand, acquisition, operations — using 21 specialised agents
      across five departments over an enforced append-only state contract. The
      <b>operating layer</b> treats that plan as the company's opening state
      rather than its output, and runs the same five departments on cadences
      thereafter.</p>""")
    p.append(figure_two_layers())

    p.append('<h2>The problem it addresses</h2>')
    p.append("""<p>Any system that pursues a goal by measuring its progress will
      eventually improve the measurement rather than the goal. A department
      rewarded for footfall buys footfall that does not convert; the dashboard
      stays green while the business deteriorates. Three related failures follow:
      the objective is never questioned, departments optimise against each other,
      and thresholds silently expire. In a system operating on daily cadences with
      nobody in the room, these appear in days rather than quarters.</p>""")

    p.append('<h2>Two findings from building the generation layer</h2>')
    p.append("""<p><b>Prompt-level constraints were insufficient.</b> A market
      prompt carrying an explicit numeric sanity range, and a revenue prompt
      stating that year-one revenue must not exceed the obtainable market, were
      both ignored repeatedly. Five such conflicts were found; all five resolved
      once the value was computed rather than requested.</p>""")
    p.append("""<p><b>Decomposition compounds variance.</b> Over five runs of an
      identical prompt, the multi-agent pipeline's financial-accuracy standard
      deviation was 4.9× a single-LLM baseline's, with a 7.6× best-to-worst spread
      against the baseline's 1.8×. Its best run was the more accurate of the two.
      The architecture is unreliably better, not reliably worse.</p>""")
    p.append("""<div class="callout"><span class="label">Both say the same
      thing</span><p>An agent cannot be relied upon to assert a quantity by which
      it is judged. The generation layer's answer was local — where two agents
      assert the same value, the derived figure wins. The operating layer
      generalises it.</p></div>""")

    p.append(figure_variance())

    # ---- page 2 ----
    p.append('<div class="page-break"></div>')

    p.append('<h2>How the operating layer answers it</h2>')
    p.append("""<p>Rather than one loop per department, Orion runs a <b>graph of
      loops that check one another</b>, grounded in three things no department can
      argue with.</p>""")
    p.append("""<div class="cols"><div>
      <div class="kv"><b>Objective numbers, computed by code.</b> Cash, margin,
        retention, churn, acquisition cost — derived deterministically from an
        append-only record of events, never reported by a department.</div>
      <div class="kv"><b>The Constitution.</b> Hard constraints enforced in the
        execution path, not described in prompts — spend caps, no data deletion,
        no irreversible action unapproved. This is the first finding above,
        applied to authority.</div>
      <div class="kv"><b>Human judgement.</b> Aesthetics, tone, ethics and
        strategic direction are routed to a person by classification, not at an
        agent's discretion. Departments draft; they do not ratify.</div>
      </div><div>""")
    p.append("""<div class="invariant"><span class="label">The anchor
      invariant</span><p><em>No department, planner, worker or reflection process
      may write an anchor metric, and no learning process may optimise directly
      against one. Anchors are computed, never reported.</em></p></div>""")
    p.append("""<p style="font-size:8.2pt;">The precedent is the held-out
      evaluation set in production machine learning: locked, never trained on. If
      the learner could reach it, the score would stop measuring anything. Same
      reasoning, applied to a company's measure of itself.</p>""")
    p.append("</div></div>")

    p.append(figure_anchor())

    p.append("""<p><b>Adding oversight is not sufficient on its own.</b> If agent A
      reviews B, B reviews C and C reviews A, everyone approves everyone and
      nothing touches reality. Orion therefore validates its own topology at
      registration: every cycle must contain a code-computed anchor or a human
      decision, and no monitor may share an evaluation signal with the loop it
      monitors.</p>""")

    p.append('<h2>What is built, and what is specified</h2>')
    p.append("""<table><tr><th style="width:26%">Component</th>
      <th style="width:13%">Status</th><th>Evidence</th></tr>
      <tr><td>21 agents, five departments</td>
        <td><span class="status st-built">Built</span></td>
        <td>Plan completeness 100% of a 26-field rubric vs 80.8% for a single-LLM
        baseline</td></tr>
      <tr><td>Append-only state contract</td>
        <td><span class="status st-built">Built</span></td>
        <td>Cross-department writes raise a contract violation; makes agreement
        measurable at all</td></tr>
      <tr><td>Derived-over-asserted reconciliation</td>
        <td><span class="status st-built">Built</span></td>
        <td>Resolved all five identified cross-agent conflicts</td></tr>
      <tr><td>Dynamic routing</td>
        <td><span class="status st-built">Built</span></td>
        <td>17.3% token saving, 0.0 pp completeness delta</td></tr>
      <tr><td>External grounding</td>
        <td><span class="status st-prov">Partial</span></td>
        <td>OpenStreetMap in use; competitor ground truth not yet collected, so
        the grounding question is unanswered</td></tr>
      <tr><td>Anchors · Constitution · monitor loops · cadences</td>
        <td><span class="status st-spec">Specified</span></td>
        <td>Not yet implemented or measured</td></tr>
      </table>""")
    p.append("""<p style="font-size:8.2pt;"><b>Caveats that travel with those
      numbers.</b> They come from a five-prompt smoke run, not the full
      thirty-five-prompt sweep. Financial accuracy divides by sector benchmarks
      that are not yet sourced, so its absolute values are provisional —
      between-arm comparisons are less affected. Business quality has no oracle
      comparable to a unit test, so every metric here is a proxy, which is an
      uncomfortable observation for a system about proxy capture and is stated
      rather than left implicit.</p>""")

    p.append('<h2>Where it stands against comparable systems</h2>')
    p.append("""<p style="font-size:8.3pt;">Orion inherits role specialisation
      with structured artefacts from MetaGPT, durable execution from workflow
      engines, approval gates from business process management, and the
      independent-monitor and locked-evaluation-set patterns from production
      machine learning. It improves memory from a flat shared context to
      per-department typed stores, and governance from tool-level permission to
      business-decision level. What it introduces is the enforced state contract
      that makes cross-agent disagreement measurable, the anchor invariant, and
      topology validation that refuses an oversight structure which would only
      ever agree with itself.</p>""")
    p.append("""<p style="font-size:7.8pt; color:#5A6072; font-style:italic;">
      Codebase, database and test artefacts use the identifier
      <code>mabgp</code>, from the generation layer's original name, retained for
      continuity with existing test suites. Full architecture document: 16 pp,
      15 figures. Research proposal: 14 pp.</p>""")
    return html_document("Orion — Architecture Brief", "\n".join(p))


# ============================== BRIEF 2 ====================================

def brief2():
    p = [BRIEF_CSS]
    p.append(head(
        "Research Proposal Brief · 2 pages",
        "Graph-of-Loops Control for Continuous Autonomous Business Operation",
        "An extension of an already-evaluated department architecture. We ask "
        "whether mutually-checking control loops, anchored in code-computed "
        "measurement, can sustain a business operated by that architecture "
        "without proxy capture.",
        " · Full proposal: 14 pp"))

    p.append('<h2>Central question</h2>')
    p.append("""<div class="callout"><p>Can a graph of mutually-checking control
      loops, anchored in code-computed measurement, hard constraints and human
      judgement, sustain the continuous autonomous operation of a business
      without proxy capture — under conditions where a single goal-measure-act
      loop per department does not?</p></div>""")
    p.append("""<p>We do not expect a positive result to show the elimination of
      proxy capture. The more plausible outcome, if the hypotheses hold at all, is
      that capture becomes detectable sooner and to a measurable degree.</p>""")

    p.append('<h2>What is already established</h2>')
    p.append("""<table><tr><th style="width:7%">RQ</th>
      <th style="width:34%">Question</th><th style="width:16%">Status</th>
      <th>Position</th></tr>
      <tr><td><b>RQ1</b></td><td>Multi-agent vs single-LLM baseline</td>
        <td><span class="status st-prov">Partly measured</span></td>
        <td>Completeness favours decomposition decisively; consistency tied;
        financial accuracy favours the baseline</td></tr>
      <tr><td><b>RQ2</b></td><td>Dynamic routing efficiency</td>
        <td><span class="status st-built">Supported</span></td>
        <td>17.3% token saving, 0.0 pp completeness delta</td></tr>
      <tr><td><b>RQ3</b></td><td>Grounding vs parametric knowledge</td>
        <td><span class="status st-prov">Not measurable</span></td>
        <td>Requires competitor ground truth not yet collected</td></tr>
      </table>""")
    p.append("""<p>Two methodological findings are the load-bearing inputs to this
      proposal. <b>M1:</b> cross-agent constraints stated as prompt instructions
      with explicit numeric bounds were ignored repeatedly, and held only once
      re-implemented as post-conditions in code. <b>M2:</b> variance compounds
      along a dependency chain — over five runs of an identical prompt the
      pipeline's standard deviation was 103.8 against the baseline's 21.2, with
      the pipeline's best run more accurate than the baseline's best.</p>""")

    p.append(figure_variance())

    p.append("""<p style="font-size:8.2pt;">Both findings indicate that an agent
      cannot be relied upon to assert a quantity by which it is judged. We propose
      to generalise the local remedy — derived figures override asserted ones —
      into a control architecture for <em>continuous</em> operation.</p>""")

    # ---- page 2 ----
    p.append('<div class="page-break"></div>')

    p.append('<h2>Proposed questions and hypotheses</h2>')
    p.append("""<div class="rq"><span class="tag">RQ4</span><b>Does variance
      compounding persist when the estimated quantity is replaced by one computed
      from a record of events?</b></div>""")
    p.append("""<div class="rq"><span class="tag">RQ5</span><b>Does proxy-anchor
      divergence arise systematically under single-loop control, and how
      quickly?</b></div>""")
    p.append("""<div class="rq"><span class="tag">RQ6</span><b>Do independent
      monitor loops detect divergence earlier than a composite health
      indicator?</b></div>""")
    p.append("""<div class="rq"><span class="tag">RQ7</span><b>Are the graph
      invariants — cycle termination at an anchor or human, monitor independence —
      necessary for detection, or merely sufficient?</b></div>""")
    p.append("""<p style="font-size:8.2pt;">Six hypotheses are stated in the full
      proposal, each paired with an explicit falsification condition recorded
      before the arms are run. Two examples:</p>""")
    p.append("""<div class="rq"><span class="tag">H1</span>A margin computed from a
      record of transactions will show materially lower run-to-run variance than
      the same margin estimated through the agent chain.
      <div class="falsify"><b>Refuted if:</b> the computed quantity's standard
      deviation is not materially below the 103.8 already measured.</div></div>""")
    p.append("""<div class="rq"><span class="tag">H3</span>Under the full
      loop-graph topology, terminal proxy-anchor divergence will be materially
      smaller than under single-loop control.
      <div class="falsify"><b>Refuted if:</b> terminal divergence is
      statistically indistinguishable from the single-loop arm, or larger.</div>
      </div>""")

    p.append('<h2>Method</h2>')
    p.append("""<p>The existing four-arm harness is extended, not replaced. The
      current arms — <code>multi_agent</code>, <code>baseline</code>,
      <code>all_departments</code>, <code>no_grounding</code> — remain unmodified,
      so results already obtained stay valid. Four arms are added:
      <code>single_loop</code>, <code>anchors_only</code>,
      <code>monitors_only</code>, <code>full_graph</code>. Metrics F54–F58 keep
      their definitions; F59–F63 are proposed: proxy-anchor divergence, detection
      latency, conflict incident rate, objective staleness and human decision
      load.</p>""")
    p.append("""<p>Every proposed metric is computed by the harness from the
      append-only record. None derives from any agent's account of its own
      performance — if the instrument for detecting proxy capture could itself be
      influenced by the departments under study, the study would exhibit the
      failure it proposes to measure.</p>""")
    p.append("""<p><b>Baseline fairness</b> is the principal methodological risk.
      The single-loop arm receives the same memory, planning and execution
      machinery as the full-graph arm, differing only in control topology; its
      proxy metrics are drawn from measures actually used in comparable business
      functions rather than chosen for exploitability; and its specification is
      fixed and documented before any arm runs. We would rather report a null
      result against a strong baseline than a positive one against a weak
      baseline.</p>""")

    p.append('<h2>Pre-committed outcomes</h2>')
    p.append("""<table><tr><th style="width:15%">Outcome</th>
      <th style="width:40%">Observation</th><th>Reporting</th></tr>
      <tr><td><b>Supporting</b></td><td>Divergence materially lower in the
        full-graph arm on paired seeds; monitors detect induced capture
        earlier</td><td>As evidence that control topology affects proxy capture,
        bounded by the simulated environment and scale</td></tr>
      <tr><td><b>Null</b></td><td>Divergence arises but arms are
        indistinguishable, or divergence does not arise within the horizon</td>
        <td>As a null result, with analysis of whether the horizon was short, the
        perturbations weak, or the construct wrong</td></tr>
      <tr><td><b>Refuting</b></td><td>The full-graph arm diverges equally or more,
        or its monitors detect later</td><td>As a refutation. Oversight adding cost
        without adding detection is itself a substantive finding</td></tr>
      </table>""")
    p.append("""<p style="font-size:8.2pt;">The existing work sets the precedent:
      its central finding is a negative one, reported rather than tuned away.</p>""")

    p.append('<h2>Principal threats to validity</h2>')
    p.append("""<ul>
      <li><b>Construct.</b> Divergence may conflate Goodhart effects with ordinary
        action-to-effect lag, anchor mis-specification, or noise — and M2 shows
        noise here is substantial. The most serious threat, and not fully
        resolvable.</li>
      <li><b>Internal.</b> Non-determinism may explain between-arm differences;
        mitigated by paired seeds and distributional reporting. The full topology
        also performs more inference, so a compute-matched control is
        needed.</li>
      <li><b>External.</b> The operating environment is simulated; a churn
        decision is a modelling assumption, not an observation. The prompt set is
        India-specific.</li>
      <li><b>Reflexivity.</b> The same author designs the architecture, selects
        the anchors, defines divergence and interprets results. Pre-registration
        and artefact release are partial mitigations; independent replication
        would be stronger.</li>
      </ul>""")
    p.append("""<p style="font-size:7.8pt; color:#5A6072; font-style:italic;">
      Prerequisites before the proposed arms can be interpreted: the full
      thirty-five-prompt sweep, sourced sector benchmarks, and collected
      competitor ground truth. Until then F54 remains provisional and F55
      unmeasurable, and any operating-layer result resting on them inherits that
      status. Full proposal: 14 pp, 6 figures, 16 references.</p>""")
    return html_document("Orion — Research Proposal Brief", "\n".join(p))


# ------------------------------------------------------------- figure wraps --

def _fig(svg, n, caption, cls=""):
    k = f' class="{cls}"' if cls else ""
    return (f'<figure{k}>{svg}<figcaption><b>Figure {n}</b> — {caption}'
            f'</figcaption></figure>')


def figure_two_layers():
    return _fig(fl.fig_two_layers(), 1,
                "The generation layer runs once and produces the opening state; "
                "the operating layer runs the same five departments "
                "indefinitely.", "fig-md")


def figure_variance():
    return _fig(fl.fig10_variance_measured(), 2,
                "Five runs of an identical prompt per arm. All spread is "
                "run-to-run variance. <b>Measured</b>; absolute values "
                "provisional pending sourced benchmarks.", "fig-md")


def figure_anchor():
    return _fig(fd.fig8_anchor_immutability(), 3,
                "Anchors are readable by every component and writable by none — "
                "not because policy forbids it, but because no such path exists.",
                "fig-sm")
