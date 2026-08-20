# Build the Orion review deck, replicating the supplied template exactly.
#
#     .venv\Scripts\python.exe scripts\make_deck.py
#
# Structure, layouts, placeholder geometry and image frames are taken from
# "LeadMind_SecondPresentation (1) (1).pptx" slide by slide: 19 slides, the same
# section order, the same picture positions and sizes, the same two literature
# survey tables, the same certifications grid and closing graphic.
#
# The template arrives with LeadMind content. Those slides are removed rather
# than edited; the banner, certification images and closing graphic are reused
# because they belong to this team, and everything else is rewritten for Orion.
import pathlib
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "LeadMind_SecondPresentation (1) (1).pptx"
FIG = ROOT / "docs" / "orion" / "deck_png"
MEDIA = ROOT / "docs" / "orion" / "template_media"
OUT = ROOT / "docs" / "orion" / "Orion_Presentation.pptx"

BLUE = RGBColor(0x42, 0x85, 0xF4)
INK = RGBColor(0x21, 0x21, 0x21)
MUTED = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x1E, 0x8A, 0x5F)

L_TITLE, L_BODY = 0, 2
PROJECT = "Orion"

prs = Presentation(str(TEMPLATE))
lst = prs.slides._sldIdLst
for sld in list(lst):
    rId = sld.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    prs.part.drop_rel(rId)
    lst.remove(sld)

def add(layout=L_BODY):
    return prs.slides.add_slide(prs.slide_layouts[layout])

def mark(slide, width=1.20):
    # the small project-name shape every template slide carries, bottom right
    box = slide.shapes.add_textbox(Inches(8.73 if width <= 1.3 else 8.52),
                                   Inches(5.19), Inches(width), Inches(0.44))
    p = box.text_frame.paragraphs[0]
    p.text = PROJECT
    p.font.size = Pt(11); p.font.bold = True
    p.font.color.rgb = BLUE; p.font.name = "Arial"
    p.alignment = PP_ALIGN.RIGHT
    return box

def title_ph(slide, text, left=0.34, top=0.0, size=22):
    ph = slide.shapes.title
    ph.left, ph.top = Inches(left), Inches(top)
    ph.width, ph.height = Inches(9.32), Inches(0.63)
    tf = ph.text_frame; tf.word_wrap = True
    tf.text = text
    p = tf.paragraphs[0]
    p.font.size = Pt(size); p.font.bold = True
    p.font.color.rgb = INK; p.font.name = "Arial"
    return ph

def heading(slide, text, left, top, size=20):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(9.32), Inches(0.5))
    p = box.text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(size); p.font.bold = True
    p.font.color.rgb = INK; p.font.name = "Arial"
    return box

def body_ph(slide, items, left, top, width, height, size=12, idx=1):
    try:
        ph = slide.placeholders[idx]
        ph.left, ph.top = Inches(left), Inches(top)
        ph.width, ph.height = Inches(width), Inches(height)
        tf = ph.text_frame
    except KeyError:
        box = slide.shapes.add_textbox(Inches(left), Inches(top),
                                       Inches(width), Inches(height))
        tf = box.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        txt, lvl = (item if isinstance(item, tuple) else (item, 0))
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = txt
        p.level = lvl
        p.font.size = Pt(size if lvl == 0 else size - 1)
        p.font.color.rgb = INK if lvl == 0 else MUTED
        p.font.name = "Arial"
    return tf

def textbody(slide, items, left, top, width, height, size=12):
    box = slide.shapes.add_textbox(Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tf = box.text_frame; tf.word_wrap = True
    first = True
    for item in items:
        txt, lvl = (item if isinstance(item, tuple) else (item, 0))
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = txt; p.level = lvl
        p.font.size = Pt(size if lvl == 0 else size - 1)
        p.font.color.rgb = INK if lvl == 0 else MUTED
        p.font.name = "Arial"
    return box

def pic(slide, path, left, top, width, height):
    return slide.shapes.add_picture(str(path), Inches(left), Inches(top),
                                    Inches(width), Inches(height))

def pic_fit(slide, path, left, top, width, height):
    # Place inside the frame preserving the source aspect ratio, centred.
    # The template stretches the certification images by about 15 percent; the
    # frame geometry is kept and the image is fitted within it instead.
    from PIL import Image as _I
    iw, ih = _I.open(str(path)).size
    src_ratio = iw / ih
    frame_ratio = width / height
    if src_ratio > frame_ratio:
        w, h = width, width / src_ratio
    else:
        h, w = height, height * src_ratio
    return slide.shapes.add_picture(str(path), Inches(left + (width - w) / 2),
                                    Inches(top + (height - h) / 2),
                                    Inches(w), Inches(h))

def survey_table(slide, rows, left=0.29, top=0.35, width=9.42, height=4.84):
    shape = slide.shapes.add_table(len(rows), 7, Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tbl = shape.table
    widths = [0.42, 1.62, 1.42, 1.28, 1.72, 1.52, 1.44]
    for i, w in enumerate(widths):
        tbl.columns[i].width = Inches(w)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = str(val)
            cell.margin_left = Inches(0.04); cell.margin_right = Inches(0.04)
            cell.margin_top = Inches(0.02); cell.margin_bottom = Inches(0.02)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(7.0 if r else 7.4)
                p.font.name = "Arial"
                p.font.bold = (r == 0)
                p.font.color.rgb = WHITE if r == 0 else INK
    return tbl

# ============================================================ 1  TITLE =======
s = add(L_TITLE)
pic(s, MEDIA / "slide01_0.jpg", 0.17, 0.17, 9.32, 1.42)
b = s.shapes.add_textbox(Inches(0.99), Inches(1.75), Inches(8.02), Inches(0.82))
p = b.text_frame.paragraphs[0]
p.text = "DEPARTMENT OF COMPUTER ENGINEERING"
p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = INK
p.font.name = "Arial"; p.alignment = PP_ALIGN.CENTER
b = s.shapes.add_textbox(Inches(0.99), Inches(2.55), Inches(8.02), Inches(0.60))
tf = b.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Orion : An AI Business Operating System"
p.font.size = Pt(19); p.font.bold = True; p.font.color.rgb = BLUE
p.font.name = "Arial"; p.alignment = PP_ALIGN.CENTER
ph = s.placeholders[1]
ph.left, ph.top = Inches(0.34), Inches(3.39)
ph.width, ph.height = Inches(9.32), Inches(1.68)
tf = ph.text_frame; tf.word_wrap = True
names = [
    "Student name: Aditya Maskare\t\tRoll no: 102\t\t\t Division: B",
    "Student name: Vinayak Maurya\t\tRoll no: 103\t\t\t Division: B",
    "Student name: Abhishek Mishra\t\tRoll no: 108\t\t\t Division: B",
]
first = True
for n in names:
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    first = False
    p.text = n; p.font.size = Pt(12); p.font.color.rgb = INK; p.font.name = "Arial"

# ================================================ 2  PROBLEM + OBJECTIVE ====
s = add(); mark(s)
title_ph(s, "Problem statement", 0.34, 0.00)
body_ph(s, [
    "A founder needs a plan covering positioning, unit economics, brand, acquisition and operations. Consulting is expensive and templates give structure without analysis. A single LLM pass produces text that reads well but does not hold together: revenue above the market size the same document calculated, marketing budgets above the cost base. And even a correct plan is static, while the business it describes changes the day after it is written.",
], 0.42, 0.53, 9.15, 1.55, 11.5)
heading(s, "Objective", 0.34, 2.18)
textbody(s, [
    "Decomposition: generate a complete founding plan with 21 specialised agents across five departments over an enforced append-only state contract, so cross-agent disagreement becomes measurable instead of masked.",
    "Determinism: reconcile conflicting quantitative claims in code rather than by prompt instruction, computing derived figures instead of accepting asserted ones.",
    "Continuous operation: treat the finished plan as the company's opening state and operate it on department cadences thereafter.",
    "Governed autonomy: route every consequential action through a gate chain, with hard constraints enforced in the execution path and subjective judgement reserved for a human.",
    "Measurement: evaluate the architecture against a single-LLM baseline on quantitative metrics with explicit control arms.",
], 0.34, 2.78, 9.32, 2.30, 11)

# ========================================================== 3  SCOPE ========
s = add(); mark(s)
title_ph(s, "Scope", 0.34, 0.28)
body_ph(s, [
    "Plan generation: a complete founding business plan for a new micro or small enterprise from a single natural-language sentence, anchored to a stated budget and locality.",
    "Department decomposition: Strategy, Finance, Branding, Marketing and Operations, executed as nested graphs with parallelism where agents are independent and explicit staging where they are not.",
    "External grounding: nearby competitors retrieved from a places database and market statistics from web search, with verified data overriding model-generated data for the same field.",
    "Operating layer: an append-only ledger, anchor metrics computed from it by code, code-enforced hard constraints, a five-stage governance chain, four monitor loops, per-department memory and cadence scheduling.",
    "Evaluation: financial accuracy, competitor coverage, plan completeness, cross-department consistency and routing efficiency, over a fixed prompt set with control arms.",
    "Out of scope: real financial transactions, deployment beyond localhost, and geographies outside India in this iteration.",
], 0.34, 0.95, 9.32, 4.05, 11.5)

# ============================================== 4  ARCHITECTURE DIAGRAM =====
s = add(); mark(s)
title_ph(s, "Architecture Diagram", 0.34, 0.00)
pic(s, FIG / "architecture.png", 1.53, 0.34, 6.95, 4.97)

# ======================================================= 5  DFD LEVEL 0 =====
s = add(); mark(s)
title_ph(s, "Data Flow Diagram - DFD Level 0", 0.34, 0.00)
pic(s, FIG / "dfd0.png", 1.50, 0.71, 6.80, 4.40)

# ======================================================= 6  DFD LEVEL 1 =====
s = add(); mark(s)
title_ph(s, "Data Flow Diagram - DFD Level 1", 0.34, 0.00)
pic(s, FIG / "dfd1.png", 0.59, 0.64, 8.65, 4.55)

# ======================================================= 7  DFD LEVEL 2 =====
s = add(); mark(s)
title_ph(s, "Data Flow Diagram - DFD Level 2", 0.34, 0.00)
pic(s, FIG / "dfd2.png", 1.09, 0.65, 7.70, 4.33)

# ==================================================== 8  USE CASE DIAGRAM ===
s = add(); mark(s)
title_ph(s, "Use Case Diagram", 0.34, 0.00)
pic(s, FIG / "usecase.png", 1.50, 0.44, 6.37, 4.39)

# ==================================================== 9  ACTIVITY DIAGRAM ===
s = add(); mark(s)
title_ph(s, "Activity Diagram", 0.34, 0.00)
pic(s, FIG / "activity.png", 2.18, 0.44, 5.64, 5.12)

# ======================================================= 10  TECH STACK =====
s = add(); mark(s)
title_ph(s, "Tech Stack", 0.40, 0.36)
body_ph(s, [
    "Orchestration: LangGraph, stateful multi-agent coordination",
    "LLM core: Groq 70B and 8B, Google Gemini Flash, Ollama local fallback",
    "Backend: Python 3.13, FastAPI, WebSocket streaming",
    "Persistence: SQLite in WAL mode, ChromaDB for the knowledge cache",
    "Grounding: OpenStreetMap Overpass, Serper web search",
    "Frontend: React 18 with Vite, inline SVG only",
    "Evaluation: scipy for paired significance tests, matplotlib for figures",
    "Testing: pytest, 828 tests, fully offline behind a socket guard",
], 0.34, 0.95, 4.54, 3.60, 10.5)
pic(s, FIG / "techstack.png", 4.82, 0.29, 4.97, 4.97)

# ======================================================== 11  SDG GOALS =====
s = add(); mark(s)
title_ph(s, "SDG Goals", 0.34, 0.28)
body_ph(s, [
    "Goal 8: Decent Work and Economic Growth",
    ("Lowers the cost of a credible founding plan for micro and small enterprises, and automates the repetitive analytical work that otherwise blocks a first-time founder.", 1),
    "Goal 9: Industry, Innovation and Infrastructure",
    ("Contributes an architecture for governed autonomous operation, together with a reproducible evaluation harness released as an artefact.", 1),
    "Goal 10: Reduced Inequalities",
    ("Professional business analysis currently costs between ten thousand and one lakh rupees. Running entirely on free tiers and local models removes that barrier.", 1),
    "Goal 12: Responsible Consumption and Production",
    ("Dynamic routing skips departments with no meaningful output, measured at a 17.3 percent token saving with no quality loss, reducing compute per plan.", 1),
], 0.34, 0.95, 9.32, 4.05, 11.5)

# ============================================== 12  LITERATURE SURVEY 1 =====
s = add(); mark(s, 2.30)
title_ph(s, "Literature Survey", 0.12, -0.04)
survey_table(s, [
    ["Sr\nNo.", "Project title", "Technical approach", "Algorithm/\nTechnique",
     "Key findings", "Limitations", "Future Scope"],
    ["1", "MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework (arXiv:2308.00352)",
     "Assigns software engineering roles to agents; passes structured documents between them",
     "Assembly-line SOP encoding, role specialisation",
     "Role specialisation plus structured intermediate artefacts outperforms free-form agent chat",
     "Evaluated on software tasks with executable tests as an oracle",
     "Transfer of the structured-artefact idea to domains with no test oracle"],
    ["2", "ChatDev: Communicative Agents for Software Development (arXiv:2307.07924)",
     "Organises agents into a chat chain across a waterfall of phases",
     "Communicative dehallucination",
     "Inter-agent dialogue reduces hallucination in generated artefacts",
     "Relies on dialogue rather than enforced constraints; quantities remain negotiable",
     "Making contested quantities non-negotiable rather than discussed"],
    ["3", "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation (arXiv:2308.08155)",
     "General framework for conversable, customisable agents with optional human participation",
     "Conversation programming",
     "A flexible capability layer supporting diverse multi-agent topologies",
     "A capability layer, not an architecture for a specific task; execution graph not explicit",
     "Explicit graphs so routing itself can be manipulated and measured"],
    ["4", "BusiAgent: A Multi-Agent LLM Framework for Business Excellence (arXiv:2508.15447)",
     "Multi-agent decision support for established corporate environments",
     "Role-based managerial reasoning",
     "Demonstrates multi-agent viability on business decision tasks",
     "Targets existing organisations; does not generate a founding plan or operate a company",
     "Founding a new enterprise and operating it after creation"],
    ["5", "Agentic AI Frameworks: Architectures, Protocols and Design Challenges (arXiv:2508.10146)",
     "Survey comparing CrewAI, LangGraph, AutoGen, Semantic Kernel and MetaGPT",
     "Comparative analysis of communication, memory and safety",
     "Maps the design space and identifies memory and safety as weak points",
     "Survey only; no measurement of the failure modes it identifies",
     "Empirical measurement of memory scoping and governance"],
])

# ============================================== 13  LITERATURE SURVEY 2 =====
s = add(); mark(s, 2.30)
survey_table(s, [
    ["Sr\nNo.", "Project title", "Technical approach", "Algorithm/\nTechnique",
     "Key findings", "Limitations", "Future Scope"],
    ["6", "Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv:2303.11366, NeurIPS 2023)",
     "Agents write natural-language reflections on failure and retrieve them later",
     "Verbal reinforcement learning, episodic memory buffer",
     "Self-reflection improves task success across sequential decision making, coding and reasoning",
     "Reflection is grounded in the agent's own account of the episode",
     "Grounding reflection in externally computed measurement instead"],
    ["7", "Generative Agents: Interactive Simulacra of Human Behavior (arXiv:2304.03442)",
     "Memory stream with retrieval, higher-level reflection and planning over long horizons",
     "Importance-weighted retrieval, reflection synthesis",
     "Believable individual and emergent social behaviour over extended simulated periods",
     "Shared memory stream; no measurement of retrieval precision as the corpus grows",
     "Per-unit memory scoping with precision measured against corpus size"],
    ["8", "Categorizing Variants of Goodhart's Law (arXiv:1803.04585)",
     "Formal decomposition of metric overoptimisation",
     "Regressional, extremal, causal and adversarial variants",
     "Distinguishes mechanistically different ways a proxy decouples from its goal",
     "Theoretical; no architectural remedy at the level of a multi-unit organisation",
     "Architectural countermeasures and measurement of divergence"],
    ["9", "Defining and Characterizing Reward Hacking (arXiv:2209.13085, NeurIPS 2022)",
     "Formal definition of reward hacking and unhackability",
     "Proxy versus true reward ordering analysis",
     "Unhackability is a very strong condition; two rewards are unhackable only in narrow cases",
     "Reinforcement learning framing; not applied to multi-agent business operation",
     "Applying the framing to organisational proxies and anchors"],
    ["10", "Concrete Problems in AI Safety (arXiv:1606.06565)",
     "Enumerates practical accident risks in deployed ML systems",
     "Reward hacking, side effects, scalable supervision, distributional shift",
     "Names reward hacking and scalable supervision as central deployment problems",
     "Framed as a research agenda rather than an implemented architecture",
     "Concrete enforcement mechanisms and human oversight budgets"],
])

# =================================================== 14  EXPECTED OUTCOME ===
s = add(); mark(s)
title_ph(s, "Expected Outcome", 0.34, 0.49)
body_ph(s, [
    "Completeness: a plan filling 100 percent of a 26-field rubric against roughly 81 percent for a single-LLM baseline, measured on the smoke run and to be confirmed over the full 35-prompt sweep.",
    "Efficiency: a 17.3 percent token saving from dynamic routing with a 0.0 percentage-point completeness delta on prompts where a department is genuinely skipped.",
    "A reported negative result: on financial accuracy the single-LLM baseline currently wins, which we attribute to variance compounding along the agent dependency chain rather than to a defect, and which we report rather than tune away.",
    "A methodological finding: cross-agent quantitative constraints must be enforced in code, because prompt instructions containing explicit numeric bounds were ignored repeatedly by capable models.",
    "An operating layer whose invariants are enforced and tested: anchors computed from an append-only ledger and writable by no agent, hard constraints in the execution path, and a validated loop topology.",
    "A reproducible artefact running entirely on free-tier infrastructure, with 828 offline tests and no paid dependency in the code path.",
], 0.34, 1.26, 9.32, 3.74, 11)

# ====================================================== 15  REFERENCES 1 ====
s = add(); mark(s)
title_ph(s, "References 1", 0.34, 0.28)
body_ph(s, [
    "MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework (2023)",
    ("Hong, S. et al. arXiv:2308.00352. Introduces standardised operating procedures for role-specialised agents that exchange structured documents rather than free-form messages. Our department decomposition follows the same principle, with the shared state object in place of its documents.", 1),
    "ChatDev: Communicative Agents for Software Development (2023)",
    ("Qian, C. et al. arXiv:2307.07924. Organises agents into a chat chain and introduces communicative dehallucination. Where ChatDev reduces hallucination through dialogue, we make contested quantities non-negotiable by deriving them.", 1),
    "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation (2023)",
    ("Wu, Q. et al. arXiv:2308.08155. A general framework for conversable agents with optional human participation. We use LangGraph instead because it exposes the execution graph explicitly, which our routing experiment manipulates directly.", 1),
], 0.34, 0.95, 9.32, 4.05, 11)

# ====================================================== 16  REFERENCES 2 ====
s = add(); mark(s)
title_ph(s, "References 2", 0.34, 0.28)
body_ph(s, [
    "Reflexion: Language Agents with Verbal Reinforcement Learning (2023)",
    ("Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K. and Yao, S. NeurIPS 2023, arXiv:2303.11366. Establishes that an agent can improve by writing reflections on failure and retrieving them. Our reflection differs in being grounded in measured anchor deltas rather than the agent's own account.", 1),
    "Generative Agents: Interactive Simulacra of Human Behavior (2023)",
    ("Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P. and Bernstein, M. S. arXiv:2304.03442. Demonstrates memory streams with retrieval, reflection and planning over long horizons. Informs our memory design; we add per-department scoping.", 1),
    "BusiAgent: A Multi-Agent LLM Framework for Business Excellence (2025)",
    ("arXiv:2508.15447. The closest prior work in the business domain, targeting managerial decision support in established organisations rather than founding and then operating a new enterprise.", 1),
], 0.34, 0.95, 9.32, 4.05, 11)

# ====================================================== 17  REFERENCES 3 ====
s = add(); mark(s)
title_ph(s, "References 3", 0.34, 0.28)
body_ph(s, [
    "Categorizing Variants of Goodhart's Law (2018)",
    ("Manheim, D. and Garrabrant, S. arXiv:1803.04585. Decomposes metric overoptimisation into regressional, extremal, causal and adversarial variants. Motivates the anchor design and the divergence metric proposed for the operating layer.", 1),
    "Defining and Characterizing Reward Hacking (2022)",
    ("Skalse, J., Howe, N. H. R., Krasheninnikov, D. and Krueger, D. NeurIPS 2022, arXiv:2209.13085. Gives the first formal definition of reward hacking and shows that unhackability is a very strong condition.", 1),
    "Concrete Problems in AI Safety (2016)",
    ("Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J. and Mane, D. arXiv:1606.06565. Identifies reward hacking and scalable supervision among the concrete problems of deployed systems.", 1),
    "Agentic AI Frameworks: Architectures, Protocols and Design Challenges (2025)",
    ("arXiv:2508.10146. Survey comparing CrewAI, LangGraph, AutoGen, Semantic Kernel and MetaGPT on communication, memory and safety.", 1),
], 0.34, 0.95, 9.32, 4.05, 10.5)

# ==================================================== 18  CERTIFICATIONS ====
s = add(); mark(s)
title_ph(s, "Certifications", 0.34, 0.00)
pic_fit(s, MEDIA / "slide18_0.png", 0.21, 0.08, 3.65, 2.58)
pic_fit(s, MEDIA / "slide18_1.png", 6.13, 0.08, 3.65, 2.58)
pic_fit(s, MEDIA / "slide18_2.png", 0.21, 2.84, 3.65, 2.56)
pic_fit(s, MEDIA / "slide18_3.png", 6.07, 2.84, 3.77, 2.62)

# ========================================================== 19  CLOSING ====
s = add()
pic(s, MEDIA / "slide19_0.png", 3.15, 1.51, 3.69, 2.61)

prs.save(str(OUT))
print("slides:", len(prs.slides))
print("saved:", OUT)
