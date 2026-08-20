"""
Document 1 - "Orion: An AI Business Operating System"

Architecture explainer for one project with two layers: a generation layer that
produces a company's opening state, and an operating layer that runs it onward.
Product voice, present tense.
"""

from datetime import date

from orion_style import html_document
import orion_figures_dark as fd
import orion_figures_light as fl

TITLE = "Orion: An AI Business Operating System"

_fig_n = 0


def figure(svg, caption, lead=None):
    global _fig_n
    _fig_n += 1
    head = f"<b>Figure {_fig_n}{('  ' + lead) if lead else ''}</b> — "
    return f'<figure>{svg}<figcaption>{head}{caption}</figcaption></figure>'


def h2(n, t):
    return f'<h2><span class="num">{n}</span>{t}</h2>'


def problem(name, symptom, cause, consequence):
    return (f'<div class="problem"><span class="pname">{name}</span>'
            f'<div class="row"><span class="k">Symptom</span>{symptom}</div>'
            f'<div class="row"><span class="k">Cause</span>{cause}</div>'
            f'<div class="row"><span class="k">Consequence</span>{consequence}</div>'
            f'</div>')


def callout(label, body):
    return f'<div class="callout"><span class="label">{label}</span>{body}</div>'


def invariant(label, body):
    return f'<div class="invariant"><span class="label">{label}</span>{body}</div>'


def title_page():
    return f"""
<div class="title-page">
  <div>
    <div class="title-rule"></div>
    <div class="kicker">Architecture Overview</div>
    <h1>Orion</h1>
    <div class="subtitle">An AI Business Operating System — five departments that
      generate a company's opening state, then operate it continuously under human
      supervision, without optimising themselves into failure.</div>
  </div>
  <div class="title-meta">
    <strong>Vinayak Maurya</strong><br>
    Department of Computer Engineering · University of Mumbai<br>
    {date.today().strftime('%d %B %Y')}<br>
    <span class="spec-note">This document describes the Orion architecture as
      specified. Figures marked <em>measured</em> report data from the evaluation
      harness; figures marked <em>prospective</em> illustrate a design intent that
      has not yet been measured.</span>
  </div>
</div>"""


def body():
    p = []

    # 1 -------------------------------------------------------------------
    p.append(h2(1, "Executive Summary"))
    p.append("""<p class="lead">Orion is an operating system for a company. Five
      departments — Strategy, Finance, Branding, Marketing and Operations, staffed
      by twenty-one specialised agents — generate a complete founding plan from a
      single sentence, and then keep operating the business that plan describes.</p>""")
    p.append("""<p>The system has two layers. The <strong>generation layer</strong>
      turns a natural-language prompt into a founding plan: market positioning,
      unit economics, brand, customer acquisition and day-to-day operations,
      grounded where possible in retrieved real-world data. The
      <strong>operating layer</strong> treats that plan not as the deliverable but
      as the company's opening state, and runs the same five departments on
      cadences thereafter — planning, executing, remembering and adapting, with
      humans supervising the decisions that matter.</p>""")
    p.append("""<p>Building the generation layer produced two findings that shape
      everything above it. First, cross-agent constraints expressed as prompt
      instructions were ignored repeatedly, even when they contained explicit
      numeric bounds; constraints that matter have to be enforced in code. Second,
      decomposing a quantitative estimate across dependent agents compounds
      variance: on financial accuracy the pipeline's best run beat a single-LLM
      baseline's best, and its spread was 7.6× against the baseline's 1.8×. It is
      unreliably better rather than reliably worse.</p>""")
    p.append("""<p>Both findings say the same thing in different registers.
      <strong>An agent cannot be trusted to assert a quantity it is judged on.</strong>
      The generation layer's answer was local: where two agents assert the same
      value, the derived figure wins. The operating layer generalises it. Every
      number by which the business judges itself is computed by code from an
      append-only record, and no agent has a write path to one. Departments may
      propose anything; what they cannot do is author the measure of their own
      success.</p>""")
    p.append(callout("In one sentence", """<p>Orion generates a company and then
      operates it, built so that the parts which check the work cannot be captured
      by the parts doing it.</p>"""))

    # 2 -------------------------------------------------------------------
    p.append(h2(2, "The Idea in Plain Language"))
    p.append("""<p>An entrepreneur opening a small business needs a plan covering
      positioning, unit economics, brand, acquisition and operations. Professional
      consulting for this costs a great deal. Templates give structure without
      analysis. General-purpose prompting produces text that reads well and does
      not survive arithmetic — a revenue projection above the market size the same
      document just calculated.</p>""")
    p.append("""<p>Orion's generation layer addresses that by giving each
      analytical concern its own agent and forcing all of them through one shared
      state object, so that disagreements between them become visible instead of
      being silently resolved by whichever agent wrote last.</p>""")
    p.append("""<p>But a plan is a photograph. The business it describes changes
      the day after it is written. So the operating layer keeps the same five
      departments running: the plan becomes the configuration, not the output, and
      the company acquires a state that persists — customers, spend, decisions,
      and what it learned last month and why it stopped doing the thing it was
      doing before.</p>""")
    p.append(figure(fl.fig1_pipeline_vs_cycle(),
                    """A one-shot pipeline terminates by design: its output is a
      document. Orion's cycle has no terminal state — work produces outcomes,
      outcomes become record, record informs the next plan."""))

    # 3 -------------------------------------------------------------------
    p.append(h2(3, "The Generation Layer"))
    p.append("""<p>A natural-language prompt passes through a hybrid intent
      classifier — the model extracts business type, sector and location hints,
      while deterministic code parses budget and normalises locality. The split is
      deliberate: every financial projection is anchored to the budget, so if
      budget parsing varied by provider, variance in the output could no longer be
      attributed to the agents.</p>""")
    p.append("""<p>An orchestrator then decides which departments are active and
      compiles an execution graph. Strategy runs first, because Finance prices
      against its competitor set and Marketing targets its personas. Finance,
      Branding and Marketing then run concurrently. Operations joins on all three,
      and is skipped entirely for a business with no physical premises — which is a
      configuration flag rather than a separate code path, so both arms of the
      routing experiment run identical code.</p>""")
    p.append("""<p>Two mechanisms in this layer matter more than the topology, and
      they are the ones the operating layer inherits.</p>""")
    p.append("""<h3>The append-only state contract</h3>
      <p>All agents read and write one shared state object, and an agent may write
      only its own department's section. A cross-department write raises a contract
      violation. This is what makes cross-department agreement measurable at all:
      if any agent could overwrite another's section, a disagreement would be
      resolved by write ordering and the consistency metric would be measuring
      write ordering rather than agreement.</p>""")
    p.append("""<h3>Derived quantities override asserted ones</h3>
      <p>Where two agents assert the same value, the computed figure wins. Cost
      totals are summed from line items rather than taken as stated. Operating
      expense is reconciled against that sum. Revenue is capped by arithmetic on a
      figure the user supplied, so the bound holds regardless of what any agent
      claims. Margins and break-even are computed in Python from six requested
      drivers, not generated as text.</p>""")
    p.append("""<p>Grounding enters through a single hook, so nineteen of the
      twenty-one agents are unmodified. Competitive analysis retrieves nearby
      businesses from a places database; market research retrieves statistics from
      web search. Retrieved data overrides generated data for the same field, and
      every record keeps a source label, which is what lets grounded and
      ungrounded runs be told apart afterwards.</p>""")

    # 4 -------------------------------------------------------------------
    p.append(h2(4, "What Building It Revealed"))
    p.append("""<p>The generation layer was evaluated against a single-LLM baseline
      on four quantitative metrics with three control arms. Two results are
      relevant to everything that follows.</p>""")
    p.append("""<h3>Prompt-level constraints were insufficient</h3>
      <p>The market-sizing prompt contained an explicit numeric sanity range. The
      revenue prompt stated that year-one revenue must not exceed the obtainable
      market. Both were ignored repeatedly by capable models. Five distinct
      conflicts of this kind were found, each corrupting the financial metric, and
      all five were resolved by the same move: stop asking, and compute the value
      instead.</p>""")
    p.append(callout("The general form", """<p>In a multi-agent system,
      cross-agent constraints must be post-conditions enforced in code, not
      requests expressed in prose. A rule in a prompt is a suggestion a
      sufficiently confident model will occasionally reason past.</p>"""))
    p.append("""<h3>Decomposition compounds variance</h3>
      <p>On financial accuracy the single-LLM baseline outperformed the
      multi-agent pipeline — and after five implementation defects had been found
      and fixed, this appears to be structural rather than a defect still
      outstanding. The multi-agent margin sits at the end of a dependency chain:
      market sizing produces an obtainable market, revenue projects against it,
      the P&amp;L derives drivers from that projection, and margin falls out of the
      drivers. Each step carries estimation error and the errors compose. The
      baseline emits a margin in one step with no chain to accumulate along.</p>""")
    p.append(figure(fl.fig10_variance_measured(),
                    """Five runs of an identical prompt per arm. Because the input
      is fixed, all spread is run-to-run variance. The pipeline's best run is more
      accurate than the baseline's best; its distribution is far wider.""",
                    lead="Measured"))
    p.append("""<p>The signature is instability, not bias — which is why a
      single-shot comparison would have shown only that the baseline had a better
      mean and missed the reason entirely. Deterministic reconciliation at each
      junction reduced the variance substantially and did not remove it.</p>""")
    p.append("""<p>This finding constrains the operating layer in a specific and
      useful way. If a chain of agent estimates is unreliable, then the numbers a
      business judges itself by must not be produced that way. They have to be
      computed from a record of what actually happened.</p>""")

    # 5 -------------------------------------------------------------------
    p.append(h2(5, "Why Continuous Operation Is Harder"))
    p.append("""<p>A system that answers once needs to be clever once. A system
      that runs a business needs four things cleverness does not supply.</p>""")
    p.append("""<p><strong>Durable state.</strong> A company is a set of
      relationships that change. A customer exists because a deal closed; that deal
      exists because a campaign reached someone. Held as free text, those
      relationships dissolve and no one can ask which campaigns produced customers
      who are still here a year later.</p>""")
    p.append("""<p><strong>Its own schedule.</strong> Businesses operate on
      cadences. Something must wake up, assess, decide and act without being
      prompted. A system that acts only when asked is a tool; a system that acts on
      its own cadence is an organisation.</p>""")
    p.append("""<p><strong>Institutional rather than session memory.</strong> When
      a person leaves a company, the company usually retains what they learned.
      When a context window closes, everything in it is gone.</p>""")
    p.append("""<p><strong>A boundary of authority.</strong> Some decisions should
      never be made by software — whether a strategy is ethical, whether an
      irreversible payment is warranted. The boundary has to be explicit and
      enforced, not left to the model's discretion in the moment.</p>""")

    # 6 -------------------------------------------------------------------
    p.append(h2(6, "The Problems Orion Addresses"))
    p.append("""<p>Once a system operates continuously, a fifth problem appears
      that a one-shot pipeline never encounters. The failures below are the ordinary
      pathologies of any managed organisation. What changes is speed: a human
      department drifts over quarters, a software department over days, and nobody
      is in the room to notice.</p>""")
    p.append(problem(
        "Proxy capture — the measure becomes the target",
        """A department is asked to improve something hard to measure, so something
        easy is measured instead. The easy number rises steeply while the thing it
        stood for deteriorates.""",
        """The department optimises the number it is judged on. Actions that raise
        the proxy while decoupling it from the objective are indistinguishable, to
        the loop, from actions that do both.""",
        """Every reported metric improves while the business declines. The failure
        is invisible precisely because the instruments say otherwise."""))
    p.append(problem(
        "Objective non-interrogation",
        """A navigation system finds the fastest route flawlessly and routes you
        onto a flooded road, because it was never asked whether the road should be
        used.""",
        """The objective is exogenous. The loop optimises within it and has no
        mechanism for questioning it, so "grow the customer base" is executed
        faithfully long after each new customer costs more than they return.""",
        """The organisation becomes excellent at pursuing something it should have
        abandoned. Competence at the wrong task takes longer to notice than
        incompetence."""))
    p.append(problem(
        "Inter-department conflict",
        """Marketing discounts to raise volume. Finance cuts the budget line that
        would have addressed the resulting churn. Operations absorbs a surge of
        low-value orders.""",
        """Objectives are assigned per department and nothing is accountable for
        the interaction between them. Every unit is behaving correctly by its own
        instructions.""",
        """Five departments each report success while the company gets worse.
        There is no single point at which the failure appears, which is why it
        survives."""))
    p.append(problem(
        "Measurement decay",
        """A threshold calibrated at launch still reports acceptable performance
        after the market it described has moved.""",
        """A stale value returns a number rather than an error, so staleness
        produces no signal. Confidence outlives validity.""",
        """The system is most dangerous when it is most certain, because certainty
        is calibrated against conditions that no longer hold."""))

    # 7 -------------------------------------------------------------------
    p.append(h2(7, "The Orion Model"))
    p.append("""<div class="hierarchy">Business → Departments → Projects → Tasks
      → Workers → Decisions → Execution → Memory → Reflection → <b>Continuous
      Operation</b></div>""")
    p.append("""<p>Read left to right this is delegation. Read as a loop it is
      learning: execution produces outcomes, outcomes are recorded, reflection turns
      records into lessons, lessons change the next plan. The rightmost term is not
      a stage — it is the observation that there is no last stage.</p>""")
    p.append("""<p>Two properties matter more than the sequence. Decisions are a
      distinct step between planning and execution, which is where human
      supervision attaches. And memory is a first-class stage rather than a side
      effect, because a company that does not record what happened cannot learn
      from it.</p>""")
    p.append(figure(fl.fig_two_layers(),
                    """The generation layer runs once and produces the opening
      state. The operating layer runs the same five departments indefinitely. The
      two principles the generation layer established are what the operating layer
      generalises."""))

    # 8 -------------------------------------------------------------------
    p.append(h2(8, "System Architecture"))
    p.append(figure(fl.fig2_layers(),
                    """Work flows downward; evidence flows upward. The shared state
      contract restricts each agent to its own department's section, and every
      anchor metric is derived from the append-only record by code."""))
    p.append("""<h3>Business Operating Core</h3>
      <p>The kernel: intent classification, routing, cadence scheduling,
      governance, and the registry defining which loops exist and how they may
      connect. It schedules and arbitrates; it does not think.</p>""")
    p.append("""<h3>Provider abstraction</h3>
      <p>No agent imports a vendor SDK. Every call walks a fallback chain across
      hosted providers and terminates at a local model, which is what allows a run
      to complete when hosted free tiers are exhausted. The chain records which
      provider served each request, so cost and latency figures are reproducible
      from stored telemetry rather than by re-running the pipeline.</p>""")

    # 9 -------------------------------------------------------------------
    p.append(h2(9, "Department Architecture"))
    p.append("""<p>In most agent systems the agent is the primary object. Orion
      makes the <em>department</em> primary: an agent is an invocation, a department
      is a unit with a name, a history, a budget and obligations that survives the
      replacement of any individual worker.</p>""")
    p.append("""<table class="compact">
      <tr><th style="width:13%">Department</th>
      <th style="width:31%">Stage 1 — concurrent</th>
      <th style="width:26%">Stage 2</th>
      <th>What its memory accumulates</th></tr>
      <tr><td><b>Strategy</b></td><td>market research · competitive analysis ·
        location intelligence</td><td>business planning · risk analysis</td>
        <td>market findings, competitor sets, risks that materialised</td></tr>
      <tr><td><b>Finance</b></td><td>revenue model · cost structure</td>
        <td>funding strategy · P&amp;L forecast</td>
        <td>forecast error, cost structure over time, budget outcomes</td></tr>
      <tr><td><b>Branding</b></td><td>brand naming</td>
        <td>brand identity · brand voice · visual design</td>
        <td>naming decisions and the reasoning behind them</td></tr>
      <tr><td><b>Marketing</b></td><td>buyer persona</td>
        <td>digital plan · campaign plan · SEO content</td>
        <td>campaign outcomes, message performance, channel economics</td></tr>
      <tr><td><b>Operations</b></td><td>supply chain · staffing plan · tech
        stack</td><td>process flow</td>
        <td>workflow performance, failure modes, throughput limits</td></tr>
      </table>""")
    p.append("""<p>The staging encodes real dependencies rather than convenience.
      Business planning sizes the market against research that has already run. The
      P&amp;L agent requires revenue and cost figures to exist. The three branding
      agents all reference the name that was selected. Process flow assigns each
      workflow step to a role the staffing agent actually created — an assignment
      that is checkable, and which is checked.</p>""")
    p.append(figure(fl.fig3_department_anatomy(),
                    """The nine parts of a department under continuous operation.
      The manager owns outcomes, the planner decomposes goals, workers execute; the
      remaining six give the department the persistence that makes it an
      organisational unit rather than a function call."""))

    # 10 ------------------------------------------------------------------
    p.append(h2(10, "Memory Architecture"))
    p.append("""<p>A single shared memory fails three ways at once. Retrieval
      becomes noisy as unrelated departments' histories compete for relevance.
      Volume eventually exceeds what any context can hold. And because everything
      is attributed to everyone, no department's learning can be measured
      separately, so there is no way to tell which parts of the organisation are
      improving.</p>""")
    p.append(figure(fl.fig4_memory_scoping(),
                    """Left: one pool every department writes into and reads from.
      Right: one store per department, each holding four distinct kinds of memory,
      with retrieval scoped to the owner."""))
    p.append("""<table><tr><th style="width:16%">Type</th><th style="width:36%">
      What it holds</th><th>The question it answers</th></tr>
      <tr><td><b>Episodic</b></td><td>Specific events with timestamps and
        outcomes</td><td>What happened, and when?</td></tr>
      <tr><td><b>Semantic</b></td><td>Consolidated facts and durable
        conclusions</td><td>What do we know to be true?</td></tr>
      <tr><td><b>Procedural</b></td><td>Sequences that worked, as reusable
        method</td><td>How do we do this?</td></tr>
      <tr><td><b>Reflective</b></td><td>Judgements about performance, grounded in
        measured outcomes</td><td>What should we do differently?</td></tr>
      </table>""")
    p.append("""<p>Memory does not only grow. Repeated episodes consolidate into
      semantic conclusions and unretrieved entries decay, so a department that ran
      the same campaign eleven times carries one conclusion rather than eleven
      anecdotes competing for attention.</p>""")

    # 11 ------------------------------------------------------------------
    p.append(h2(11, "Governance Architecture"))
    p.append("""<p>Governance is usually described as the tax paid for autonomy.
      Here it is the opposite: it is what makes autonomy permissible. A system that
      cannot be stopped cannot be trusted with anything worth doing.</p>""")
    p.append(figure(fl.fig5_gate_chain(),
                    """Every consequential action traverses the same five stages.
      Three of them can halt it. The audit trail records the passage regardless of
      outcome, including the halts."""))
    p.append("""<p><strong>Policy rules</strong> are evaluated at the approval gate
      and are configurable — spend thresholds, which categories need review, who
      signs off. These are business decisions and they change.</p>""")
    p.append("""<p><strong>Hard constraints</strong> — the Constitution — are
      enforced in code at the execution gate. Never exceed the daily spend cap.
      Never delete customer data. Never release a payment without verification.
      Never take an irreversible action without approval. These are not described
      to the departments; they are conditions the departments cannot make
      false.</p>""")
    p.append(callout("Why this distinction is not stylistic", """<p>It is the
      generation layer's finding applied to authority. Numeric bounds stated in
      prompts were ignored repeatedly by capable models. There is no reason to
      expect a spend cap stated in a prompt to fare better. The Constitution can be
      changed only by a human-signed change to the code itself.</p>"""))
    p.append("""<p>Alongside the gates sits a classifier for subjective questions.
      Whether a payment exceeds a threshold is arithmetic. Whether a brand voice is
      right, whether a strategy is ethical, whether copy is any good — these are
      matters of judgement and are routed to a human by rule. Departments draft;
      they do not ratify.</p>""")

    # 12 ------------------------------------------------------------------
    p.append(h2(12, "The Graph of Loops"))
    p.append("""<p>Everything so far is substrate. It makes a business possible to
      operate. It does not make the operation trustworthy, because a
      well-engineered single loop still optimises its proxy. The remedy is not a
      better metric. It is more than one loop.</p>""")
    p.append("""<p>A car is not safe because its engine is good. It is safe because
      it has brakes, anti-lock braking, airbags, seatbelts, crumple zones and
      warning lights — independent systems, each covering the others' failures. None
      is expected to be sufficient alone.</p>""")
    p.append("""<p>The clearest existing example of the pattern is not in business
      software. It is the standard way a machine-learning system is operated in
      production.</p>""")
    p.append(figure(fd.fig6_ml_reference(),
                    """A production ML system. Several loops run at once: a
      challenger is evaluated against an incumbent, drift is monitored against live
      traffic, thresholds trigger rollback, a training loop feeds improvements back.
      It is reliable because the loops are independent, not because any one is
      excellent.""",
                    lead="Reference case"))
    p.append("""<p>Note the node at the right. The held-out evaluation set is
      locked, and the edge from the training loop is crossed out and labelled
      <em>never seen</em>. Every practitioner accepts this, and the reason is worth
      stating precisely: <strong>if the training loop could see the evaluation set,
      the evaluation score would stop measuring anything.</strong> It would become a
      target, and it would be met.</p>""")
    p.append("""<p>That crossed edge is proxy capture prevented by architecture
      rather than by discipline. Nobody is trusted not to peek; peeking is made
      structurally impossible. It is also, exactly, the generation layer's
      derived-over-asserted rule — generalised from one contested field to the whole
      company's measure of itself.</p>""")

    # 13 ------------------------------------------------------------------
    p.append(h2(13, "Anchors"))
    p.append(figure(fd.fig7_orion_loop_graph(),
                    """The Orion loop graph — the same topology in a business. A
      proposed plan is compared against anchors before it replaces the active
      playbook. Operations write to the record. The anchors are locked, and
      reflection may not optimise against them.""",
                    lead="Derived"))
    p.append("""<table class="compact"><tr>
      <th style="width:34%">In a production ML system</th><th>In Orion</th></tr>
      <tr><td>Incumbent model</td><td>Active playbook — the plan in force</td></tr>
      <tr><td>Challenger model</td><td>Proposed plan from the department's
        planner</td></tr>
      <tr><td>Head-to-head evaluation</td><td>Plan compared against anchors before
        adoption</td></tr>
      <tr><td>Live traffic</td><td>Real business operations — tasks executed</td></tr>
      <tr><td>Drift monitor</td><td>Drift &amp; decay monitor loop</td></tr>
      <tr><td>Alert threshold</td><td>Constitution thresholds and severity
        rubric</td></tr>
      <tr><td>Automatic rollback</td><td>Revert the playbook, or halt at the
        execution gate</td></tr>
      <tr><td>Training loop</td><td>Reflection and knowledge evolution</td></tr>
      <tr><td><b>Held-out eval set</b> — locked, never seen</td>
        <td><b>Anchor metrics</b> derived from the append-only record — no
        department writes one, and reflection never optimises against one</td></tr>
      </table>""")
    p.append("<h3>Three kinds of anchor</h3>")
    p.append("""<p><strong>Objective numbers, computed by code.</strong> Cash,
      revenue, contribution margin, retention, churn, acquisition cost, lifetime
      value, service-level breaches — each derived deterministically from the
      append-only record. No department reports these; the record captures what
      happened and the numbers are recomputed from it.</p>""")
    p.append("""<p><strong>Hard constraints the departments cannot change.</strong>
      The Constitution, enforced in code as described above.</p>""")
    p.append("""<p><strong>Human judgement on subjective questions.</strong>
      Aesthetics, tone, ethics, strategic direction — routed by classification, not
      by a department's own assessment of its competence.</p>""")
    p.append(invariant("The anchor invariant", """<p><em>No department, planner,
      worker or reflection process may write an anchor metric, and no learning
      process may optimise directly against one. Anchors are computed, never
      reported.</em></p>"""))
    p.append(figure(fd.fig8_anchor_immutability(),
                    """The boundary. Everything in the agent runtime can read
      anchors and none of it can write them — not because policy forbids it, but
      because no such path exists."""))
    p.append("<h3>Why more loops is not automatically better</h3>")
    p.append("""<p>Oversight can produce the appearance of rigour without the
      substance. If agent A reviews B, B reviews C and C reviews A, there are three
      review steps, extensive documentation, everyone approving everyone — and no
      point at which anything is compared against reality. A mistake introduced
      anywhere is ratified everywhere. That is not a graph of loops; it is one
      larger loop with more participants and more confidence.</p>""")
    p.append("""<p>Orion therefore validates its own topology. When a loop
      registers, two conditions are checked. <strong>Termination:</strong> every
      cycle must contain at least one node that is a code-computed anchor or a human
      decision. <strong>Independence:</strong> a monitor may not be evaluated by, or
      share a reward signal with, the loop it monitors — an auditor rewarded by the
      number it audits will not report that the number has been captured.</p>""")
    p.append(figure(fd.fig9_cycle_validity(),
                    """Left: three agents checking one another with nothing outside
      the cycle — rejected at registration. Right: the same shape with one node
      replaced by a code-computed anchor. A human decision node satisfies the
      condition equally well."""))

    # 14 ------------------------------------------------------------------
    p.append(h2(14, "Evidence So Far"))
    p.append("""<p>The generation layer is measured. The operating layer is
      specified and its monitor loops are not yet evaluated. The distinction is
      maintained throughout this document and is worth stating plainly.</p>""")
    p.append("""<table><tr><th style="width:30%">Metric</th>
      <th style="width:14%">Direction</th><th style="width:18%">Multi-agent</th>
      <th style="width:18%">Single-LLM baseline</th><th>Reading</th></tr>
      <tr><td>Plan completeness</td><td>higher better</td><td class="yes">100.0</td>
        <td>80.8</td><td>Decomposition wins decisively</td></tr>
      <tr><td>Consistency</td><td>higher better</td><td>97.8</td>
        <td class="part">100.0</td><td>Effectively tied</td></tr>
      <tr><td>Financial accuracy (MAPE)</td><td>lower better</td><td>~132</td>
        <td class="yes">~41</td><td>Baseline wins — see §4</td></tr>
      <tr><td>Routing efficiency</td><td>saving</td><td class="yes">17.3% tokens</td>
        <td>n/a</td><td>0.0 pp completeness delta</td></tr>
      </table>""")
    p.append("""<p>Three caveats belong with those numbers rather than in a
      footnote. The figures come from a five-prompt smoke run, not the full
      thirty-five-prompt sweep. Financial accuracy divides by sector margin
      benchmarks that are not yet sourced, so its absolute values are provisional —
      comparisons between arms are less affected, since both arms divide by the same
      benchmark. And competitor coverage, the intended headline metric for
      grounding, is not yet measurable because it requires hand-verified ground
      truth that has not been collected.</p>""")
    p.append("""<p>One unplanned observation is worth recording. The multi-agent
      arm completed every run; the baseline completed three of five, both failures
      being free-tier rate limiting. That is partly an artefact of pinning the
      baseline to one named provider for experimental control, so the defensible
      claim is narrower than it first appears: a multi-provider fallback chain
      confers measurable resilience under free-tier constraints.</p>""")

    # 15 ------------------------------------------------------------------
    p.append(h2(15, "A Prospective Scenario"))
    p.append("""<p>The following has not been observed. It describes what the
      operating layer is built to catch, using the same business as the variance
      experiment — a small ice cream shop in Andheri West with a fifteen-lakh
      budget.</p>""")
    p.append("""<div style="display:flex; gap:18px; align-items:flex-start;">
      <div style="flex:1.30;">""")
    p.append("""<p>Marketing is measured on footfall. It runs discount promotions
      and footfall rises. The discounts are deep enough that each additional
      customer contributes less than the cost of attracting them, so net margin
      falls while reported performance improves. Because Marketing is judged on
      footfall, its loop registers success and does more of what produced it.
      <em>This is proxy capture.</em></p>
      <p>Nobody asks whether footfall is still the right objective when additional
      footfall is loss-making. <em>This is objective
      non-interrogation.</em></p>
      <p>Finance, watching cash fall, trims the supplier quality budget. Operations
      absorbs longer queues at lower ticket values. Each department's own measure
      improves. <em>This is conflict.</em></p>
      <p>The margin benchmark the dashboard compares against was set at founding
      and never revised. <em>This is decay.</em></p>""")
    p.append("""</div><div style="flex:1;">""")
    p.append(figure(fl.fig_goodhart_prospective(),
                    """The divergence pattern the operating layer is designed to
      surface. <b>Prospective</b> — not measured."""))
    p.append("</div></div>")
    p.append(figure(fd.fig11_kaapi_caught(),
                    """Marketing still claims success; the difference is that the
      claim is checkable against a number Marketing cannot write. The detector does
      not need to understand ice cream — only that a claimed improvement has no
      corresponding anchor movement.""",
                    lead="Prospective"))

    # 16 ------------------------------------------------------------------
    p.append(h2(16, "How Orion Learns, and What It Produces"))
    p.append("""<p>Each department periodically reflects: what worked, what did
      not, what should change, what is worth keeping. The mechanism is
      unremarkable; the constraint on it is not. Reflection is grounded in measured
      anchor deltas, not in the department's account of its own performance. A
      department that believes it had an excellent month, in a month where margin
      fell, produces a negative reflection. It is not permitted to be the source of
      evidence about itself — the same reasoning as the held-out evaluation set,
      applied to learning rather than scoring.</p>""")
    p.append("""<p>What reflection produces is retained reusably. Completed
      projects yield plan templates; recurring conclusions become playbook entries.
      A department facing a familiar situation retrieves the method that worked
      instead of reasoning from first principles again.</p>""")
    p.append("""<p>Orion's outputs are living objects rather than exports: the
      business strategy, the financial model, the marketing plan, the product
      roadmap, the customer database. Each is versioned by the department
      responsible, and each revision carries the anchor movement that prompted
      it.</p>""")
    p.append(figure(fl.fig12_living_object(),
                    """A plan across a quarter. Each version records the anchor
      movement that caused the revision, so the reasoning behind the plan currently
      in force stays inspectable months later."""))
    p.append("""<p>The practical consequence is that "why are we doing this?"
      always has an answer. A document exported in January is a photograph of a
      decision whose reasoning is already lost.</p>""")
    p.append(figure(fl.fig13_sequence(),
                    """One cadence, end to end. The department consults its own
      memory, plans, submits decisions for governance, executes only what is
      approved, records outcomes, and the anchors are recomputed from the record
      rather than reported by the worker."""))

    # 17 ------------------------------------------------------------------
    p.append(h2(17, "How Orion Compares"))
    p.append("""<table class="compact">
      <tr><th style="width:20%">System</th>
      <th>Persistent<br>org state</th><th>Dept-scoped<br>memory</th>
      <th>Continuous<br>operation</th><th>Human<br>gates</th>
      <th>Reflection</th><th>Business<br>domain model</th>
      <th>Resists<br>metric capture</th></tr>
      <tr><td><b>CrewAI</b></td><td class="no">No</td><td class="no">No</td>
        <td class="no">No</td><td class="part">Minimal</td><td class="no">No</td>
        <td class="no">No</td><td class="no">No</td></tr>
      <tr><td><b>AutoGen</b></td><td class="no">No</td><td class="no">No</td>
        <td class="no">No</td><td class="part">Minimal</td><td class="no">No</td>
        <td class="no">No</td><td class="no">No</td></tr>
      <tr><td><b>LangGraph</b></td><td class="part">Checkpoints</td>
        <td class="no">No</td><td class="no">No</td><td class="part">Interrupts</td>
        <td class="no">No</td><td class="no">No</td><td class="no">No</td></tr>
      <tr><td><b>MetaGPT</b></td><td class="part">Artefacts</td><td class="no">No</td>
        <td class="no">No</td><td class="part">Minimal</td><td class="no">No</td>
        <td class="part">SWE roles</td><td class="no">No</td></tr>
      <tr><td><b>Microsoft Copilot</b></td><td class="part">Tenant data</td>
        <td class="no">No</td><td class="part">Reactive</td><td class="yes">Yes</td>
        <td class="no">No</td><td class="part">Partial</td><td class="no">No</td></tr>
      <tr><td><b>Agentforce</b></td><td class="part">CRM</td><td class="no">No</td>
        <td class="part">Triggered</td><td class="yes">Yes</td><td class="no">No</td>
        <td class="part">CRM only</td><td class="no">No</td></tr>
      <tr><td><b>Temporal</b></td><td class="yes">Durable</td><td>n/a</td>
        <td class="yes">Yes</td><td class="part">Signals</td><td class="no">No</td>
        <td class="no">No</td><td class="no">No</td></tr>
      <tr><td><b>Camunda / BPM</b></td><td class="yes">Yes</td><td class="no">No</td>
        <td class="yes">Yes</td><td class="yes">Yes</td><td class="no">No</td>
        <td class="part">Process</td><td class="no">No</td></tr>
      <tr style="background:#F2F4FD;"><td><b>Orion</b></td>
        <td class="yes">Yes</td><td class="yes">Yes</td><td class="yes">Yes</td>
        <td class="yes">Yes</td><td class="yes">Yes</td><td class="yes">Yes</td>
        <td class="yes">By design</td></tr></table>""")
    p.append("""<p><strong>Inherits.</strong> Role specialisation with structured
      intermediate artefacts, from MetaGPT. Durable, restart-tolerant execution,
      from workflow engines. Approval gates and auditability, from business process
      management. The independent-monitor pattern and the locked evaluation set,
      from production machine learning.</p>""")
    p.append("""<p><strong>Improves.</strong> Memory moves from a flat shared
      context to per-department stores with distinct types and consolidation.
      Governance moves from tool-level permission — may this function be called? —
      to business-decision level: should this commitment be made, and on whose
      authority?</p>""")
    p.append("""<p><strong>Introduces.</strong> The enforced append-only state
      contract, which makes cross-agent disagreement measurable rather than masked
      by write ordering. The anchor invariant, which makes a company's measure of
      itself unwritable by that company. And topology validation, which refuses to
      run an oversight structure that would only ever agree with itself.</p>""")
    p.append("""<p>The final column is marked <em>by design</em> rather than
      <em>yes</em> deliberately. The mechanism is specified and the invariant is
      checkable; whether it produces the intended effect is a question for
      measurement, not for a table.</p>""")

    # 18 ------------------------------------------------------------------
    p.append(h2(18, "Risks, Limitations and What Comes Next"))
    p.append("""<p><strong>Variance compounding is not solved.</strong> It is the
      generation layer's measured negative result, and deterministic reconciliation
      reduced it without removing it. Any quantity the operating layer derives
      through a chain of agent estimates inherits the problem, which is the reason
      anchors are computed from a record of events rather than from an estimation
      chain.</p>""")
    p.append("""<p><strong>Sample size and benchmark provenance.</strong> Present
      results are a five-prompt smoke run against unsourced sector benchmarks.
      Neither the absolute financial figures nor any single-metric claim should be
      treated as established until the full sweep is run and the benchmarks are
      cited.</p>""")
    p.append("""<p><strong>Weak ground truth.</strong> Work on code-generating
      agents can execute unit tests. Business plan quality has no comparable
      oracle. These metrics are proxies, and a plan can satisfy all of them while
      still being commercially poor — which is, uncomfortably, the same class of
      problem the operating layer exists to detect.</p>""")
    p.append("""<p><strong>Model throughput bounds the cadence.</strong> Five
      execution loops and four monitor loops contending for local inference
      constrain how frequently departments can act. Cadences are staggered and much
      monitor logic is ordinary computation rather than inference, but the
      constraint sets the pace of the company.</p>""")
    p.append("""<p><strong>External data is an attack surface.</strong> A retrieved
      page is untrusted input and may contain text addressed to the model.
      Retrieved content is tagged with provenance, delimited, denied tool authority
      and structurally prevented from moving an anchor. The anchor invariant limits
      the consequence of a successful injection; it does not eliminate the
      concern.</p>""")
    p.append("""<p><strong>Single geography, no human evaluation.</strong>
      Gazetteer, funding schemes, salary bands and benchmarks are India-specific.
      Persuasiveness and practical usefulness are not measured at all, deliberately,
      to keep every metric reproducible.</p>""")
    p.append("""<h3>What comes next</h3>
      <p>Complete the full prompt sweep and source the benchmarks. Collect
      competitor ground truth so the grounding question can be answered directly.
      Instrument the monitor loops and measure whether they detect divergence
      earlier than a composite health view. Investigate variance reduction by
      ensembling the estimation chain rather than individual agents. Extend beyond
      one geography.</p>""")
    p.append(callout("The through-line", """<p>Every extension above preserves one
      property: the company never becomes the author of its own measure. If a future
      capability required relaxing that, the correct decision would be to forgo the
      capability.</p>"""))
    p.append("""<p style="font-size:8.4pt; color:#5A6072; font-style:italic;">
      Implementation note. The codebase, database and test artefacts use the
      identifier <code>mabgp</code>, from the generation layer's original name. The
      identifier is retained for continuity with existing artefacts and test
      suites; it refers to the same system described here.</p>""")

    return "\n".join(p)


def render():
    return html_document(TITLE, title_page() + body())
