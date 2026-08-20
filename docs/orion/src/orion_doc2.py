"""
Document 2 - "Research Proposal: Graph-of-Loops Control for Continuous
Autonomous Business Operation"

An extension of an existing evaluated architecture. RQ1-RQ3 are retained with
their measured status; RQ4-RQ7 are proposed. Investigative voice throughout.
"""

from datetime import date

from orion_style import html_document
import orion_figures_light as fl

TITLE = "Research Proposal — Graph-of-Loops Control"

_fig_n = 0


def figure(svg, caption):
    global _fig_n
    _fig_n += 1
    return (f'<figure>{svg}<figcaption><b>Figure {_fig_n}</b> — {caption}'
            f'</figcaption></figure>')


def h2(n, t):
    return f'<h2><span class="num">{n}</span>{t}</h2>'


def callout(label, body):
    return f'<div class="callout"><span class="label">{label}</span>{body}</div>'


def rq(tag, question, note_):
    return (f'<div class="rq"><span class="tag">{tag}</span>'
            f'<b>{question}</b><div class="falsify">{note_}</div></div>')


def hyp(tag, statement, falsify):
    return (f'<div class="rq"><span class="tag">{tag}</span>{statement}'
            f'<div class="falsify"><b>Would be refuted if:</b> {falsify}</div>'
            f'</div>')


def title_page():
    return f"""
<div class="title-page">
  <div>
    <div class="title-rule"></div>
    <div class="kicker">Research Proposal — Extension</div>
    <h1>Graph-of-Loops Control for Continuous Autonomous Business Operation</h1>
    <div class="subtitle">An investigation into whether mutually-checking control
      loops, anchored in code-computed measurement, hard constraints and human
      judgement, can sustain a business operated by the department architecture we
      have already built and evaluated.</div>
  </div>
  <div class="title-meta">
    <strong>Vinayak Maurya</strong><br>
    Department of Computer Engineering · University of Mumbai<br>
    B.E. Computer Engineering — Final Year Major Project<br>
    {date.today().strftime('%d %B %Y')}<br>
    <span class="spec-note">This document describes the Orion architecture as
      specified. It extends an existing evaluated system; §3 states precisely what
      is already measured and what is not.</span>
  </div>
</div>"""


def body():
    p = []

    # Abstract ------------------------------------------------------------
    p.append('<h2>Abstract</h2>')
    p.append("""<p>We have built and evaluated a department-structured multi-agent
      architecture that generates a complete founding business plan from one
      sentence, using twenty-one agents across five departments over an enforced
      append-only state contract. Two measured findings from that work motivate this
      proposal. First, cross-agent constraints expressed as prompt instructions
      containing explicit numeric bounds were ignored repeatedly, and had to be
      re-implemented as post-conditions in code. Second, decomposing a quantitative
      estimate across dependent agents compounded variance: on financial accuracy
      the pipeline's standard deviation was 4.9× a single-LLM baseline's over
      repeated identical inputs, with a 7.6× best-to-worst spread against the
      baseline's 1.8×. Both findings indicate that an agent cannot be relied upon to
      assert a quantity by which it is judged. We propose to generalise the local
      remedy — derived figures override asserted ones — into a control architecture
      for <em>continuous</em> operation, in which every measure the business is
      judged by is computed by code from an append-only record and is unwritable by
      any agent, hard constraints are enforced in the execution path, and monitor
      loops are constrained by two topological invariants. We propose to evaluate
      this by extending our existing four-arm harness with four further arms,
      retaining all current metrics and adding five, and measuring proxy-anchor
      divergence over an operating horizon. We pre-commit to reporting null and
      refuting outcomes on the same terms as supporting ones.</p>""")

    # 1 -------------------------------------------------------------------
    p.append(h2(1, "Introduction and Motivation"))
    p.append("""<p>Multi-agent systems built on large language models can decompose
      an objective, assign roles and produce coordinated output. Our own prior work
      establishes that such decomposition reliably improves coverage of a
      specification: a twenty-one-agent pipeline filled 100% of a twenty-six-field
      rubric where a single-LLM baseline reached roughly 81%.</p>""")
    p.append("""<p>That work also produced a result we did not expect and did not
      tune away. On the one metric that required a quantitative estimate to travel
      through a chain of dependent agents, the single-LLM baseline outperformed the
      pipeline — not by being more accurate at its best, but by being far more
      stable. The pipeline's best run was the more accurate of the two; its
      distribution was 4.9× wider. We characterise the architecture as unreliably
      better rather than reliably worse.</p>""")
    p.append("""<p>We suggest that this observation, together with the finding that
      prompt-level numeric constraints were ignored, points to something more
      general than a defect in our implementation. In both cases the system produced
      a number that served as its own evidence. When we removed that arrangement —
      computing the value from line items the agents had already produced rather
      than accepting the value they asserted — every one of five conflicts
      resolved.</p>""")
    p.append("""<p>The question this proposal takes up is whether that principle
      scales from a single contested field to an entire operating business. If a
      plan becomes a company's opening state rather than its final output, then the
      company acquires measures of its own performance, and the same problem
      recurs at a larger scale and over a longer horizon. We do not take the answer
      as established; it is the proposition motivating the work.</p>""")

    # 2 -------------------------------------------------------------------
    p.append(h2(2, "Problem Statement"))
    p.append(callout("Central question", """<p>Can a graph of mutually-checking
      control loops, anchored in code-computed measurement, hard constraints and
      human judgement, sustain the continuous autonomous operation of a business
      without proxy capture — under conditions where a single goal-measure-act loop
      per department does not?</p>"""))
    p.append("""<p>Three sub-problems follow. A <em>measurement</em> problem: the
      quantities by which the system judges itself must be constructed so that it
      cannot influence them except by changing the world they describe. Our prior
      variance finding sharpens this — it is not sufficient that a measure be
      well-chosen if it is produced by the chain being measured. A
      <em>topology</em> problem: adding oversight does not automatically add
      rigour, since components that check one another may converge on mutual
      agreement rather than accuracy, and the conditions distinguishing these cases
      require specification. And an <em>authority</em> problem: some judgements are
      not reducible to measurement, and the boundary between what is delegated and
      what is reserved must be explicit, enforced, and sustainable within a
      realistic human attention budget.</p>""")
    p.append("""<p>We note at the outset that we do not expect a positive result to
      show the elimination of proxy capture. The more plausible outcome, if the
      hypotheses hold at all, is that capture becomes detectable sooner and to a
      measurable degree.</p>""")

    # 3 -------------------------------------------------------------------
    p.append(h2(3, "What Is Already Established"))
    p.append("""<p>This proposal extends an evaluated system rather than describing
      a new one. Stating the current evidentiary position precisely is necessary,
      because the proposed work reuses the same harness, arms and prompt set.</p>""")
    p.append("""<table><tr><th style="width:9%">RQ</th><th style="width:36%">
      Question</th><th style="width:16%">Status</th><th>Position</th></tr>
      <tr><td><b>RQ1</b></td><td>Does a multi-agent pipeline beat a single-LLM
        baseline on accuracy, completeness and consistency?</td>
        <td class="part">Partly measured</td>
        <td>Completeness favours decomposition decisively; consistency is
        effectively tied; financial accuracy favours the baseline</td></tr>
      <tr><td><b>RQ2</b></td><td>Does dynamic routing improve efficiency without
        degrading quality?</td><td class="yes">Supported</td>
        <td>17.3% token saving with a 0.0 pp completeness delta on prompts where a
        department was actually skipped</td></tr>
      <tr><td><b>RQ3</b></td><td>Does grounding in retrieved data improve accuracy
        over parametric knowledge?</td><td class="no">Not yet measurable</td>
        <td>Requires hand-verified competitor ground truth, not yet collected;
        indirect signal only</td></tr>
      </table>""")
    p.append("""<p>Three qualifications apply to all of the above and are carried
      forward unchanged into this proposal. Present figures come from a five-prompt
      smoke run rather than the full thirty-five-prompt sweep. Financial accuracy
      divides by sector margin benchmarks that are not yet sourced, so its absolute
      values are provisional; between-arm comparisons are less affected because both
      arms divide by the same benchmark. And competitor coverage is unmeasured.</p>""")
    p.append("""<p>Two further findings are methodological rather than
      question-specific, and they are the load-bearing inputs to this proposal.</p>""")
    p.append("""<p><strong>M1 — Prompt-level constraints were insufficient.</strong>
      A market-sizing prompt containing an explicit numeric sanity range, and a
      revenue prompt stating that year-one revenue must not exceed the obtainable
      market, were both ignored repeatedly. Five conflicts of this kind were
      identified, each corrupting the financial metric.</p>""")
    p.append("""<p><strong>M2 — Variance compounds along a dependency
      chain.</strong> Over five runs of an identical prompt, the multi-agent arm
      produced MAPE of 290.9, 129.1, 239.2, 96.8 and 38.4 — standard deviation
      103.8 against the baseline's 21.2 on the same prompt. The best pipeline run
      (38.4) beat the best baseline run (50.0). Five implementation defects were
      found and fixed before this conclusion was drawn, reducing MAPE from roughly
      180–450 to roughly 70–200; we stopped there deliberately, on the grounds that
      further adjustment aimed at the metric would be tuning to the measurement.</p>""")
    p.append(figure(fl.fig10_variance_measured(),
                    """The measured basis for M2. All spread is run-to-run
      variance, since the input is identical across runs."""))

    # 4 -------------------------------------------------------------------
    p.append(h2(4, "Related Work"))
    p.append("""<h3>Multi-agent frameworks and business tasks</h3>
      <p>MetaGPT [1] shows that role specialisation with structured intermediate
      artefacts outperforms free-form agent chat; our shared state object plays the
      role of its structured documents. ChatDev [2] reduces hallucination through
      inter-agent dialogue, where we reduce it by making certain quantities
      non-negotiable. AutoGen [3] is a capability layer rather than an architecture
      for a specific task. A recent survey [4] compares agentic frameworks on
      communication, memory and safety. BusiAgent [5] is the closest prior work in
      the business domain, targeting managerial decision support in established
      organisations rather than founding a new enterprise. None of these, in our
      reading, constrains what a unit may measure about itself, or treats the unit
      as a persistent locus of learning across sessions.</p>""")
    p.append("""<h3>Durable execution and business process management</h3>
      <p>Workflow engines such as Temporal [6] provide restart-tolerant long-running
      execution with signals for external intervention; business process management
      systems such as Camunda [7] provide explicit approval gates, role assignment
      and audit trails. Both traditions address continuity and governance
      convincingly and we adopt their mechanisms. Neither, as far as we can
      determine, addresses whether a process's own success measures can be captured
      by that process — the metric is typically taken as given.</p>""")
    p.append("""<h3>Reflection and organisational memory</h3>
      <p>Reflexion [8] establishes that an agent can improve by generating
      natural-language reflections on failure and retrieving them subsequently.
      Generative Agents [9] demonstrates memory streams with retrieval, higher-level
      reflection and planning over extended simulated periods. Both are important
      precedents for our memory and reflection design. In both, reflection is
      grounded in the agent's own record of events. Whether grounding reflection in
      externally computed measurement changes its behaviour is, in our reading,
      open, and it is among the questions we propose to examine.</p>""")
    p.append("""<h3>Proxy capture</h3>
      <p>Goodhart's original observation [10], in Strathern's widely-cited
      formulation [11], holds that a measure ceases to be a good measure once it
      becomes a target. Manheim and Garrabrant [12] decompose the effect into
      distinct variants including regressional, extremal and causal forms. Amodei et
      al. [13] identify reward hacking among the concrete problems of AI safety, and
      Skalse et al. [14] give a formal definition. This literature characterises the
      failure thoroughly. Our reading is that it is less concerned with
      architectural remedies at the level of a multi-unit organisation, which is the
      gap this proposal addresses.</p>""")
    p.append("""<h3>Convergent auditing and capability layers</h3>
      <p>A multi-lens convergent audit methodology [15] sweeps a product inventory
      through deliberately diverse lenses, verifying each candidate finding against
      the code before reporting, and terminating only after consecutive passes yield
      nothing new. Its claim-versus-code lens is the conceptual origin of the
      claim-versus-record check proposed in §8. That project is explicit that its
      convergence is a heuristic bound rather than a proof and that its runs are not
      deterministic; we adopt both the technique and that candour. A separate
      capability layer [16] provides external source access through ordered
      preferred-and-fallback backends per channel with health diagnostics, and
      informs our tool registry. We restrict use to its zero-configuration channels
      and exclude session-credential social scraping, for the reasons in §15.</p>""")

    # 5 -------------------------------------------------------------------
    p.append(h2(5, "Problem Taxonomy"))
    p.append("""<p>We propose to study four failure modes of continuous operation.
      For each: a definition, the mechanism we believe produces it, an instantiation
      in our domain, and — most importantly for the design of the study — how it
      might be measured.</p>""")
    p.append("""<table class="compact"><tr>
      <th style="width:15%">Mode</th><th style="width:28%">Mechanism</th>
      <th style="width:28%">Instantiation in our domain</th>
      <th>Proposed measurement</th></tr>
      <tr><td><b>F1</b><br>Proxy capture</td>
        <td>The evaluated quantity correlates with the objective under ordinary
        conditions; optimisation selects for actions that decouple them</td>
        <td>Marketing evaluated on footfall runs discounts deep enough that each
        additional customer reduces net margin</td>
        <td>Rank correlation between a proxy series and its corresponding anchor
        series over a sliding window</td></tr>
      <tr><td><b>F2</b><br>Objective non-interrogation</td>
        <td>The objective is exogenous to the loop and is never a candidate for
        revision</td>
        <td>"Increase footfall" persists after marginal footfall becomes
        loss-making</td>
        <td>Elapsed operating time during which an objective holds while its
        intended anchor moves adversely; revision lag</td></tr>
      <tr><td><b>F3</b><br>Inter-department conflict</td>
        <td>Objectives are per department; nothing is accountable for their
        interaction</td>
        <td>Finance trims the supplier budget that would have addressed the churn
        Marketing's discounting produced</td>
        <td>Occurrences where two departments' own measures improve while a shared
        anchor moves adversely; detection latency</td></tr>
      <tr><td><b>F4</b><br>Measurement decay</td>
        <td>A stale value returns a number rather than an error, so staleness
        produces no signal</td>
        <td>A margin benchmark set at founding still classifies performance as
        acceptable after sector economics shift</td>
        <td>Metric age at time of use; retrieval-weighted memory age; interval from
        an injected perturbation to threshold revision</td></tr>
      </table>""")
    p.append("""<p>F1 and F3 are the modes our existing consistency metric gestures
      at without capturing. That metric checks agreement between departments within
      a single generated plan. It has no temporal dimension, and it compares
      departments against each other rather than against an external quantity —
      which is precisely the arrangement §2 identifies as insufficient.</p>""")

    # 6 -------------------------------------------------------------------
    p.append(h2(6, "Research Questions"))
    p.append("""<p>RQ1–RQ3 are retained unchanged, with the status recorded in §3.
      RQ4–RQ7 are proposed. The numbering is continuous so that the two bodies of
      work read as one programme.</p>""")
    p.append(rq("RQ4", "Does variance compounding persist when the estimated "
                "quantity is replaced by a quantity computed from a record of "
                "events?",
                "This connects the proposed architecture directly to M2. It is the "
                "question we consider most likely to yield a clean answer, because "
                "the comparison is against an already-measured baseline."))
    p.append(rq("RQ5", "Does proxy-anchor divergence arise systematically under "
                "single-loop control in a continuously operated business, and if "
                "so, how quickly?",
                "Establishes whether the phenomenon is present and measurable in "
                "this setting at all. If it does not arise, RQ6 and RQ7 are moot "
                "and we would report that."))
    p.append(rq("RQ6", "Do independent monitor loops detect divergence earlier "
                "than a composite business-health indicator?",
                "Compares detection latency between monitors reading anchors and a "
                "conventional aggregate health view."))
    p.append(rq("RQ7", "Are the proposed graph invariants — cycle termination at "
                "an anchor or human, and monitor independence — necessary for "
                "detection, or merely sufficient?",
                "Examined by relaxing each invariant individually. We regard this "
                "as the most theoretically interesting question and the least "
                "likely to yield a clean answer, since relaxing a structural "
                "invariant may change several things at once."))
    p.append("""<p>A fifth question concerns feasibility rather than mechanism, and
      we treat it as a first-class object of study rather than an assumption:
      <b>what human decision load does the governance arrangement impose, and does
      it remain within a plausible attention budget?</b> A governance design that
      produces more decisions than a person would genuinely review is not viable
      however sound its logic.</p>""")

    # 7 -------------------------------------------------------------------
    p.append(h2(7, "Hypotheses and Falsification Conditions"))
    p.append("""<p>Each hypothesis is stated so that a specific observation would
      refute it. We commit to these conditions before running the arms, and to
      reporting the outcome under them whatever it is.</p>""")
    p.append(hyp("H1", """We hypothesise that <b>a margin computed from a record of
      transactions will exhibit materially lower run-to-run variance than the same
      margin estimated through the agent dependency chain, on identical
      inputs.</b>""",
                 """the computed quantity's standard deviation over repeated
      identical runs is not materially below the 103.8 already measured for the
      estimated quantity."""))
    p.append(hyp("H2", """We hypothesise that <b>under single-loop control with
      proxy metrics, proxy and anchor series will diverge systematically over an
      operating horizon, with proxies improving while anchors deteriorate.</b>""",
                 """the two series remain positively rank-correlated across the
      majority of seeded runs, or divergence appears without consistent direction —
      which would indicate noise rather than capture."""))
    p.append(hyp("H3", """We hypothesise that <b>under the full loop-graph
      topology, terminal proxy-anchor divergence will be materially smaller than
      under single-loop control, given identical seeds, models and starting
      state.</b>""",
                 """terminal divergence under the full topology is statistically
      indistinguishable from the single-loop arm, or larger."""))
    p.append(hyp("H4", """We hypothesise that <b>monitor loops reading anchors will
      detect a synthetically induced capture scenario earlier than a composite
      business-health indicator.</b>""",
                 """monitor detection latency is equal to or greater than that of
      the composite indicator across induced scenarios."""))
    p.append(hyp("H5", """We hypothesise that <b>relaxing cycle-termination —
      permitting cycles composed only of agents — will degrade detection of induced
      capture relative to the full topology.</b>""",
                 """detection performance is unchanged when the invariant is
      relaxed, which would indicate the invariant is not doing the work we
      attribute to it."""))
    p.append(hyp("H6", """We hypothesise that <b>department-scoped memory will
      retain retrieval precision as the corpus grows across operating cycles,
      whereas a shared context will degrade.</b>""",
                 """precision degrades at a comparable rate under both
      arrangements, or shared context matches scoped memory at the largest corpus
      sizes tested."""))
    p.append(callout("Expected strength, stated in advance", """<p>We regard H1 and
      H6 as the most likely to be supported, H2 as likely but possibly slow to
      appear within a bounded horizon, H3 and H4 as genuinely uncertain, and H5 as
      the most likely to yield an ambiguous outcome. We record these expectations
      now so that they can be compared against what we find.</p>"""))

    # 8 -------------------------------------------------------------------
    p.append(h2(8, "Proposed Architecture as Intervention"))
    p.append("""<p>The architecture below is the independent variable. Its value to
      this work is that it can be ablated, and that three of its four components
      already exist in a measured form.</p>""")
    p.append(figure(fl.d2_fig1_loop_graph(),
                    """The proposed control topology. The five execution loops are
      the departments already implemented; the four monitor loops and the anchor
      layer are the proposed addition."""))
    p.append("""<h3>Anchors — a generalisation of an existing mechanism</h3>
      <p>Our current system already computes rather than accepts certain
      quantities: cost totals are summed from line items, operating expense is
      reconciled against that sum, margins and break-even are computed in Python
      from six requested drivers. The proposal generalises this to every quantity
      the business is judged by, derived from an append-only record of events, with
      the invariant that no component of the agent runtime holds a write path to an
      anchor and no learning process optimises directly against one. The intended
      analogy is the held-out evaluation set, whose value as a measure is
      conventionally attributed to its inaccessibility to the training process.</p>""")
    p.append(figure(fl.d2_fig2_anchor_boundary(),
                    """The proposed asymmetry: readable by every component, writable
      by none. We propose that this asymmetry, rather than any property of the
      metrics themselves, is what allows them to remain measures."""))
    p.append("""<h3>Constitution — a generalisation of M1</h3>
      <p>M1 established that numeric bounds stated in prompts were ignored, and
      that the same bounds enforced as post-conditions held. The Constitution
      applies that result to operating constraints — spend caps, irreversibility,
      data deletion — enforced at the execution path rather than described in
      prompts. Whether this produces a measurable difference in constraint
      violation rates under continuous operation is a subsidiary question we intend
      to record.</p>""")
    p.append("""<h3>Graph invariants</h3>""")
    p.append(figure(fl.d2_fig3_invariants(),
                    """The two proposed invariants and the rationale for each.
      Whether they are necessary, or only sufficient, is the subject of RQ7."""))
    p.append("""<p>The motivation for the first invariant is that a set of
      components which evaluate one another may reach agreement without reference to
      any external quantity. We describe such a configuration as a larger single
      loop rather than a graph of loops. The invariant attempts to state formally
      what distinguishes the two, and we acknowledge that our formulation may prove
      too strong, too weak, or the wrong frame entirely.</p>""")

    # 9 -------------------------------------------------------------------
    p.append(h2(9, "Methodology"))
    p.append("""<p>We propose to extend the existing harness rather than replace
      it. The four current arms are retained unmodified, so results already obtained
      remain valid and comparable; four arms are added for the operating layer.</p>""")
    p.append(figure(fl.d2_fig4_ablation(),
                    """Existing arms retained; proposed arms added. All arms share
      the seed, the model, the prompt set and the starting state."""))
    p.append("""<h3>Baseline fairness</h3>
      <p>The credibility of the comparison rests on the single-loop arm being a fair
      representative of ordinary practice rather than a weakened straw comparison.
      Our existing baseline discipline is instructive here and is carried forward:
      the current single-LLM control receives the stronger model, an explicit
      enumeration of every rubric field, and the same deterministic intent
      classifier, and is pinned to one named provider after an earlier
      implementation silently served a "Gemini baseline" from a local
      three-billion-parameter model.</p>
      <p>Applying the same discipline: the single-loop arm will receive the same
      memory, planning and execution machinery as the full-graph arm, differing only
      in control topology; its proxy metrics will be drawn from measures actually
      used in comparable business functions rather than chosen for exploitability;
      and its specification will be fixed and documented before any arm is run. We
      regard this as the principal methodological risk of the study, and we would
      rather report a null result against a strong baseline than a positive one
      against a weak baseline.</p>""")
    p.append("""<h3>Environment</h3>
      <p>Operation requires an environment that responds to the company's actions.
      We propose a stochastic model in which customers arrive, convert, retain or
      churn according to parameters known to the harness and not to the agents. This
      is what makes anchors computable and the study possible, and it imposes the
      external-validity limit discussed in §12. The prompt set, gazetteer and sector
      structure are reused unchanged.</p>""")
    p.append("""<h3>Induced scenarios</h3>
      <p>Two families of perturbation at predetermined points. <em>Capture
      scenarios</em> make a proxy improvable by an action that damages the
      corresponding anchor, allowing detection to be timed against a known onset.
      <em>Decay scenarios</em> shift environment parameters so that calibrated
      thresholds silently lose validity. Onset times are known to the harness, which
      converts detection into a measurable latency rather than a judgement.</p>""")

    # 10 ------------------------------------------------------------------
    p.append(h2(10, "Metrics and Instrumentation"))
    p.append("""<p>The five existing metrics are retained with their definitions
      unchanged. Five are proposed.</p>""")
    p.append("""<table class="compact"><tr><th style="width:8%">ID</th>
      <th style="width:26%">Metric</th><th style="width:38%">Definition</th>
      <th>Status</th></tr>
      <tr><td>F54</td><td>Financial accuracy</td><td>MAPE of projected steady-state
        net margin against sector benchmark</td><td class="part">Existing —
        provisional benchmarks</td></tr>
      <tr><td>F55</td><td>Competitor coverage</td><td>Verified competitors found
        over hand-collected ground truth within 2 km</td><td class="no">Existing —
        not yet measurable</td></tr>
      <tr><td>F56</td><td>Plan completeness</td><td>Expected fields present and
        substantive over a 26-field rubric</td><td class="yes">Existing —
        measured</td></tr>
      <tr><td>F57</td><td>Consistency</td><td>Proportion of applicable
        cross-department checks passing</td><td class="yes">Existing —
        measured</td></tr>
      <tr><td>F58</td><td>Routing efficiency</td><td>Token and time saving against
        the forced-all control, with completeness delta</td><td class="yes">Existing
        — measured</td></tr>
      <tr><td><b>F59</b></td><td><b>Proxy-anchor divergence</b></td><td>Rank
        correlation between a proxy series and its corresponding anchor series over
        a sliding window</td><td>Proposed</td></tr>
      <tr><td><b>F60</b></td><td><b>Detection latency</b></td><td>Operating time
        from the known onset of an induced scenario to the first finding citing the
        affected anchor</td><td>Proposed</td></tr>
      <tr><td><b>F61</b></td><td><b>Conflict incident rate</b></td><td>Occurrences
        where two departments' measures improve while a shared anchor moves
        adversely</td><td>Proposed</td></tr>
      <tr><td><b>F62</b></td><td><b>Objective staleness</b></td><td>Time an
        objective holds while its intended anchor moves adversely; revision
        lag</td><td>Proposed</td></tr>
      <tr><td><b>F63</b></td><td><b>Human decision load</b></td><td>Decisions
        escalated per operating day and their severity
        distribution</td><td>Proposed</td></tr>
      </table>""")
    p.append("""<p>Every proposed metric is computed by the harness from the
      append-only record. None is derived from any agent's account of its own
      performance. We consider this a methodological requirement rather than an
      implementation preference: if the instrument for detecting proxy capture could
      itself be influenced by the departments under study, the study would exhibit
      the failure it proposes to measure. This is the point on which we would most
      welcome scrutiny.</p>""")
    p.append("""<p>The existing refusal-to-impute policy is retained. A metric that
      cannot be computed records <code>applicable=false</code> with a reason rather
      than a zero, and the generated report lists all unscored measurements grouped
      by reason. We note that this policy is what currently prevents F55 from being
      reported as a misleading figure, and we regard it as more valuable than any
      single result it withholds.</p>""")

    # 11 ------------------------------------------------------------------
    p.append(h2(11, "Experimental Protocol"))
    p.append("""<p><b>Episode structure.</b> An episode is a fixed number of
      operating cycles over one seeded company, initialised from a generated plan.
      Each arm runs on an identical seed set, so comparisons are paired rather than
      between independent samples.</p>""")
    p.append("""<p><b>Repetition.</b> Because model behaviour is non-deterministic
      — the point M2 makes quantitatively — each seed is run repeatedly and per-seed
      distributions rather than point values are reported. The repetition count will
      be fixed after a pilot establishes run-to-run variance, following the same
      practice that produced M2.</p>""")
    p.append("""<p><b>Pre-registration.</b> Hypotheses, falsification conditions,
      metric definitions, the single-loop arm specification and the analysis plan
      will be recorded and timestamped before the arms are run. Any deviation will
      be reported as a deviation rather than presented as original intent.</p>""")
    p.append("""<p><b>Artefact.</b> The existing artefact runs entirely on free-tier
      infrastructure with a test suite that provably consumes no API quota, enforced
      by a socket guard. That property is retained. Harness, seeds, record exports
      and analysis scripts are intended for release so that reported figures can be
      recomputed from raw records by a third party.</p>""")
    p.append("""<p><b>Reporting.</b> Aggregate results will be accompanied by
      per-seed traces, including runs that behave contrary to the aggregate. Given
      non-determinism the distribution is more informative than the mean, and
      selective presentation of favourable runs would be the most likely way for
      this study to mislead.</p>""")
    p.append("""<p><b>Outstanding prerequisites.</b> Three items from the existing
      work must be closed before the proposed arms can be interpreted: the full
      thirty-five-prompt sweep, sourced sector benchmarks, and collected competitor
      ground truth. Until they are, F54 remains provisional and F55 remains
      unmeasurable, and any operating-layer result resting on them inherits that
      status.</p>""")

    # 12 ------------------------------------------------------------------
    p.append(h2(12, "Threats to Validity"))
    p.append("""<h3>Construct validity</h3>
      <p>The central construct is that proxy-anchor divergence captures what
      Goodhart's Law describes. This may be too coarse. Divergence can arise from
      ordinary lag between an action and its effect, from mis-specification of which
      anchor a proxy serves, or from noise — and M2 establishes that noise in this
      system is substantial. Manheim and Garrabrant's decomposition [12] suggests
      several mechanistically distinct effects would be conflated by a single
      divergence measure. We propose to require directionality and persistence
      rather than any single-window divergence, and to report variants separately
      where instrumentation permits. We do not expect to resolve this fully, and we
      regard it as the most serious threat.</p>""")
    p.append("""<h3>Internal validity</h3>
      <p>Non-determinism is a confound: an observed difference between arms may
      reflect sampling rather than topology. Paired seeds, repetition and
      distributional reporting are the mitigations, and M2 gives us a calibrated
      sense of the variance to expect. A second concern is that arms differ in more
      than the nominal variable — the full topology performs additional inference,
      so any advantage might be attributable to additional computation rather than
      structure. We propose a compute-matched control in which the single-loop arm
      receives equivalent inference budget spent within its own loop, and we note
      that designing this fairly is not straightforward.</p>""")
    p.append("""<h3>External validity</h3>
      <p>The operating environment is simulated. Anchors would be computed honestly
      from a record of what the system did, but a simulated customer's decision to
      churn is a modelling assumption rather than an observation. Findings would
      therefore speak to the behaviour of control topologies under a specified
      environment model. A further limit is inherited: the existing prompt set is
      Indian, mostly Mumbai, in English, and the gazetteer, funding schemes, salary
      bands and benchmarks are all India-specific.</p>""")
    p.append("""<h3>Reflexivity</h3>
      <p>The most uncomfortable threat is that the same author designs the
      architecture, selects the anchors, defines divergence, specifies the baseline
      and interprets the results. No amount of procedural care fully removes this.
      Pre-registration, artefact release and a documented baseline specification are
      partial mitigations; independent replication would be stronger, and we regard
      the artefact release as primarily serving that end rather than serving the
      presentation of these results.</p>""")
    p.append("""<h3>Weak ground truth</h3>
      <p>Inherited and unresolved. Work on code-generating agents can execute unit
      tests; business quality has no comparable oracle. Our metrics are proxies —
      which is an uncomfortable observation for a study about proxy capture, and we
      state it rather than leave it implicit.</p>""")

    # 13 ------------------------------------------------------------------
    p.append(h2(13, "Anticipated Contributions"))
    p.append("""<p>Stated conditionally, since they depend on outcomes not yet
      obtained. <em>If</em> the hypotheses are supported, the contributions would
      be:</p>""")
    p.append("""<ol>
      <li><b>A loop-graph formalism</b> for multi-unit autonomous operation, in
        which loops are first-class objects with declared inputs, outputs, cadence
        and evaluation signal, and topology is validated rather than assumed.</li>
      <li><b>The anchor-immutability invariant</b> — that an organisation's measure
        of itself should be structurally unwritable by that organisation —
        generalising a mechanism we have already found necessary at the scale of a
        single contested field.</li>
      <li><b>Two topology constraints</b>, cycle termination and monitor
        independence, offered as a formal statement of what distinguishes a graph of
        mutually-checking loops from one larger loop.</li>
      <li><b>An extension of variance compounding to the operating regime</b>, and
        evidence on whether computing a quantity from a record rather than
        estimating it through a chain removes the effect.</li>
      <li><b>A reproducible testbed</b> for studying proxy capture in autonomous
        multi-unit systems, released with seeds and records.</li>
      </ol>""")
    p.append("""<p>Contribution 4 does not depend on the loop graph working. If H1
      is supported and H3 is not, the study still establishes something useful about
      where decomposition variance can and cannot be removed.</p>""")

    # 14 ------------------------------------------------------------------
    p.append(h2(14, "Expected Outcomes, Including Negative Results"))
    p.append("""<p>Three outcomes are possible and we commit in advance to
      reporting whichever obtains, on the same terms. The existing work provides a
      precedent: its central finding is a negative one, reported rather than tuned
      away.</p>""")
    p.append("""<table><tr><th style="width:16%">Outcome</th>
      <th style="width:40%">What we would observe</th>
      <th>How we would report it</th></tr>
      <tr><td><b>Supporting</b></td><td>H2 supported; terminal divergence
        materially lower in the full-graph arm on paired seeds; monitors detect
        induced capture earlier than the composite indicator</td>
        <td>As evidence that control topology affects proxy capture in this setting,
        bounded explicitly by the simulated environment and the scale studied</td></tr>
      <tr><td><b>Null</b></td><td>Divergence arises but arms are
        indistinguishable; or divergence does not arise systematically within the
        horizon</td>
        <td>As a null result, with analysis of whether the horizon was too short,
        the perturbations too weak, or the construct wrong — without recasting the
        study as something it was not</td></tr>
      <tr><td><b>Refuting</b></td><td>The full-graph arm shows equal or greater
        divergence, or its monitors detect systematically later</td>
        <td>As a refutation of H3 and H4, with an account of the likely mechanism.
        Oversight loops adding cost without adding detection would be a substantive
        finding in itself</td></tr></table>""")
    p.append(callout("A commitment", """<p>The architecture is the object of study,
      not a position to be defended. A refuting result would be reported with the
      same prominence as a supporting one, and the pre-registered falsification
      conditions in §7 exist so that this commitment can be checked rather than
      merely asserted.</p>"""))

    # 15 ------------------------------------------------------------------
    p.append(h2(15, "Ethics, Safety and Data Handling"))
    p.append("""<p><b>No real-world financial action.</b> The system operates a
      simulated business. It holds no payment credentials and executes no real
      transaction.</p>""")
    p.append("""<p><b>External data and prompt injection.</b> Retrieved content is
      untrusted input and may contain text addressed to the model. It is tagged with
      provenance, delimited, denied tool authority, and structurally prevented from
      moving an anchor or satisfying a hard constraint. The anchor invariant limits
      the consequence of a successful injection rather than guaranteeing against it.
      We propose to include adversarial injection cases as explicit test scenarios
      and to report failures.</p>""")
    p.append("""<p><b>Sources excluded on principle.</b> External access is
      restricted to zero-configuration public sources. We exclude
      session-credential scraping of social platforms, which would require storing
      personal authentication state and would raise terms-of-service and
      personal-data questions disproportionate to the value added. This is a
      deliberate limit on the evidence base, taken knowingly. We note a related
      finding already recorded: OpenStreetMap proved a usable substitute for
      existence checking and not for price positioning, publishing no ratings and
      omitting sector tags that are common in the Indian market.</p>""")
    p.append("""<p><b>Human oversight.</b> Questions classified as subjective —
      ethical acceptability, strategic direction, brand and tone — are routed to a
      human by rule rather than at an agent's discretion, and the sustainability of
      that load is treated as an object of study.</p>""")
    p.append("""<p><b>Personal data.</b> Simulated customers are synthetic. No
      personal data is collected, and released artefacts contain none.</p>""")
    p.append("""<p><b>Third-party code.</b> Open-source components are used under
      their stated licences, pinned to specific commits, and cited for architecture
      and licensing verified by direct inspection rather than for popularity
      metrics.</p>""")

    # 16 ------------------------------------------------------------------
    p.append(h2(16, "Timeline, Feasibility and Prerequisites"))
    p.append(figure(fl.d2_fig5_timeline(),
                    """Milestones with two decision gates. The gates protect the
      experiment: an ablation run on an unstable substrate would produce
      uninterpretable results."""))
    p.append("""<p>The two gates are consequential. If continuous operation is not
      stable by the first, the proposed arms cannot be run meaningfully and the work
      would be re-scoped to a narrower claim — RQ4, which concerns variance and does
      not require sustained operation, is the natural fallback. If the harness is
      not producing reproducible paired runs by the second, reporting would reduce
      to a characterisation study addressing RQ5 alone.</p>""")
    p.append("""<p>We state these fallbacks explicitly because the most common
      failure of a proposal on this timeline is not that the system does not work,
      but that a weak experiment is run on schedule and reported as though it were a
      strong one.</p>""")
    p.append("""<h3>Feasibility under local inference</h3>
      <p>The work uses hosted free tiers with a local terminal fallback, which
      constrains throughput and therefore the number of episodes. We argue this is
      adequate for the question: the hypotheses concern control structure, and all
      arms use the same provider chain, so differences between arms are attributable
      to topology rather than capability. A weaker model may in fact be a more
      sensitive instrument for F1, being less likely to notice unaided that a proxy
      has decoupled from its objective.</p>
      <p>Two limitations follow and we would state them as such. Absolute business
      performance across all arms will be below what a frontier model would achieve,
      so terminal figures are not comparable to any commercial benchmark. And
      whether a substantially more capable model exhibits F1 to the same degree is
      not something this study can determine — a question noted in §17. We also
      carry forward an existing reproducibility hazard: a model named in our
      original design was retired during development, so we report the models
      actually used rather than those intended.</p>""")

    # 17 ------------------------------------------------------------------
    p.append(h2(17, "Future Work"))
    p.append("""<p><b>Capability scaling.</b> Whether proxy capture attenuates or
      intensifies with model capability, examined by holding topology fixed and
      varying the model. We consider this the most consequential question this work
      raises without answering.</p>""")
    p.append("""<p><b>Variance reduction by ensembling.</b> M2 suggests ensembling
      the estimation chain rather than individual agents. This is orthogonal to the
      loop graph and would compose with it.</p>""")
    p.append("""<p><b>Real-market operation.</b> Replacing simulated anchors with
      observed ones, under narrow scope and full human authority over irreversible
      action, would address the external-validity limit the simulation imposes.</p>""")
    p.append("""<p><b>Learned topology.</b> The loop graph is hand-specified.
      Because it is a first-class validated object, a system that proposes its own
      monitors while remaining subject to the same invariants is a natural
      extension — and raises the question of whether a system can be trusted to
      design its own oversight.</p>""")
    p.append("""<p><b>Additional departments and geographies.</b> Sales, HR and
      Legal are absent from the current five and would extend the conflict surface
      that F61 measures. Extension beyond a single geography is a prerequisite for
      any general claim.</p>""")
    p.append("""<p><b>Formal verification of the invariants.</b> Cycle termination
      and monitor independence are graph properties, checked per instance at
      registration. Proving them for classes of topology appears tractable.</p>""")
    p.append("""<p><b>A qualitative track.</b> An LLM-as-judge or human-rated
      assessment reported separately from the quantitative core, so that the
      reproducible part stays reproducible while persuasiveness and practical
      usefulness become visible.</p>""")

    # References ----------------------------------------------------------
    p.append(h2("", "References"))
    p.append("""<ol class="refs">
      <li>Hong, S. et al. <i>MetaGPT: Meta Programming for a Multi-Agent
        Collaborative Framework.</i> arXiv:2308.00352.</li>
      <li>Qian, C. et al. <i>ChatDev: Communicative Agents for Software
        Development.</i> arXiv:2307.07924.</li>
      <li>Wu, Q. et al. <i>AutoGen: Enabling Next-Gen LLM Applications via
        Multi-Agent Conversation.</i> arXiv:2308.08155.</li>
      <li><i>Agentic AI Frameworks: Architectures, Protocols, and Design
        Challenges.</i> arXiv:2508.10146.</li>
      <li><i>BusiAgent: A Cutting-Edge Multi-Agent LLM Framework for Business
        Excellence.</i> arXiv:2508.15447.</li>
      <li>Temporal Technologies. <i>Temporal documentation</i> — durable execution
        and long-running workflow semantics.</li>
      <li>Camunda. <i>Camunda Platform documentation</i> — process orchestration,
        human task management and approval gates.</li>
      <li>Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., &amp;
        Yao, S. (2023). <i>Reflexion: Language Agents with Verbal Reinforcement
        Learning.</i> NeurIPS 2023. arXiv:2303.11366.</li>
      <li>Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., &amp;
        Bernstein, M. S. (2023). <i>Generative Agents: Interactive Simulacra of
        Human Behavior.</i> arXiv:2304.03442.</li>
      <li>Goodhart, C. A. E. (1975). <i>Problems of Monetary Management: The U.K.
        Experience.</i> Papers in Monetary Economics, Reserve Bank of
        Australia.</li>
      <li>Strathern, M. (1997). "'Improving ratings': audit in the British
        University system." <i>European Review</i>, 5(3), 305–321. The formulation
        "when a measure becomes a target, it ceases to be a good measure" appears at
        p. 308.</li>
      <li>Manheim, D., &amp; Garrabrant, S. (2018). <i>Categorizing Variants of
        Goodhart's Law.</i> arXiv:1803.04585.</li>
      <li>Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., &amp;
        Mané, D. (2016). <i>Concrete Problems in AI Safety.</i>
        arXiv:1606.06565.</li>
      <li>Skalse, J., Howe, N. H. R., Krasheninnikov, D., &amp; Krueger, D. (2022).
        <i>Defining and Characterizing Reward Hacking.</i> NeurIPS 2022.
        arXiv:2209.13085.</li>
      <li>Jain, A. <i>production-audit</i> — a convergent multi-lens audit
        methodology. MIT Licence.
        <span style="font-family:monospace; font-size:8pt;">
        github.com/apoorvjain25/production-audit</span>. Cited for its
        claim-versus-code lens and its stated convergence heuristic.</li>
      <li><i>Agent-Reach</i> — an agent capability layer providing external source
        access via ordered fallback backends with health diagnostics. MIT Licence.
        <span style="font-family:monospace; font-size:8pt;">
        github.com/Panniantong/Agent-Reach</span>. Cited for its channel-routing
        architecture and licence.</li>
      </ol>""")
    p.append("""<p style="font-size:8.6pt; color:#5A6072; font-style:italic;">
      Citation status. References 8–14 were verified against their published records
      during preparation of this document. References 1–5 are carried forward from
      the existing work, where they were verified to exist with the titles and
      identifiers given; author lists and venues should be confirmed from the arXiv
      listing pages before submission. References 6–7 are project documentation,
      cited for capability descriptions rather than empirical claims. References
      15–16 are open-source repositories, cited for architecture and licence terms
      verified by direct inspection. Citations for LangGraph, the model families
      actually used, and the sector benchmark sources remain outstanding.</p>""")

    return "\n".join(p)


def render():
    return html_document(TITLE, title_page() + body())
