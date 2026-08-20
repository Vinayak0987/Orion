from overview_kit import *

def overview():
    c = [defs(), f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']
    c.append(txt(W/2, 44, "Orion \u2014 AI Business Operating System", 27, INK, "middle", "700"))
    c.append(txt(W/2, 66, "21 agents across 5 departments generate a company; an operating layer then runs it on cadences under human supervision",
                 11.5, MUTED, "middle"))

    # ================================ LEFT: clients ==========================
    c.append(panel(28, 92, 224, 288, "CLIENTS / CHANNELS", P_CLIENT))
    items = [("Web Application", "React 18 + Vite", "monitor"),
             ("REST API", "JSON over HTTP", "api"),
             ("Live Progress Stream", "WebSocket /ws/generate", "socket"),
             ("Evaluation Harness", "CLI, 8 arms", "terminal")]
    for i, (t, sub, ic) in enumerate(items):
        c.append(card(46, 128 + i * 60, 188, 48, t, ic, sub,
                      border=P_CLIENT[0] + "70", lc=P_CLIENT[2]))

    # ================================ TOP: API ===============================
    c.append(panel(276, 92, 1050, 92, "API LAYER  \u00b7  FastAPI", P_API))
    routes = ["POST /intent", "POST /generate", "WS /ws/generate", "GET /sessions",
              "GET /report + .pdf", "GET /health"]
    for i, r in enumerate(routes):
        c.append(chip(296 + i * 170, 132, 156, 32, r, P_API[0] + "80",
                      WHITE, P_API[2], 9.6))

    # ============================ RIGHT: evaluation ==========================
    c.append(panel(1350, 92, 262, 288, "EVALUATION & RESEARCH", P_EVAL))
    ev = [("5 quantitative metrics", "accuracy \u00b7 coverage \u00b7 completeness", "check"),
          ("8 experimental arms", "4 measured, 4 proposed", "flask"),
          ("Paired significance", "Wilcoxon + t-test, effect sizes", "chart"),
          ("869 offline tests", "socket guard, zero API quota", "shield")]
    yy = 128
    for t, sub, ic in ev:
        lines = 2 if "\n" in sub else 1
        h = 50 if lines == 1 else 60
        c.append(card(1368, yy, 226, h, t, ic, sub.replace("\n", " "),
                      border=P_EVAL[0] + "70", lc=P_EVAL[2], size=10))
        yy += h + 10

    # ========================== GENERATION LAYER =============================
    gy = 206
    c.append(panel(276, gy, 1050, 250,
                   "GENERATION LAYER  \u00b7  runs once, produces the opening state",
                   P_GEN, "LangGraph \u00b7 21 agents \u00b7 5 departments \u00b7 staged nested graphs"))
    c.append(card(296, gy + 56, 150, 52, "Intent\nClassifier", "brain",
                  border=P_GEN[0] + "80", lc=P_GEN[2], size=10))
    c.append(txt(371, gy + 118, "LLM + regex parsing", 8.4, MUTED, "middle"))
    c.append(card(466, gy + 56, 150, 52, "Orchestrator", "route",
                  "routing \u2192 DAG", border=P_GEN[0] + "80", lc=P_GEN[2], size=10))

    depts = [("Strategy", "5 agents", "search"), ("Finance", "4 agents", "scale"),
             ("Branding", "4 agents", "palette"), ("Marketing", "4 agents", "megaphone"),
             ("Operations", "4 agents", "gear")]
    for i, (d, n, ic) in enumerate(depts):
        c.append(card(640 + i * 134, gy + 52, 126, 60, d, ic, n,
                      border=P_GEN[0] + "80", lc=P_GEN[2], size=10))
    c.append(txt(1043, gy + 128, "stage 1 \u2192 stage 2 concurrent \u2192 stage 3 join barrier",
                 8.8, MUTED, "middle", italic=True))

    c.append(card(296, gy + 150, 700, 44,
                  "SharedBusinessState  \u2014  append-only contract", "doc",
                  "an agent may write only its own department section; a cross-department write is rejected",
                  border=P_GEN[0], lc=P_GEN[2], size=10.5, fill="#FBF3E4"))
    c.append(card(1014, gy + 150, 292, 44,
                  "Deterministic Reconciliation", "check",
                  "derived figures override asserted ones",
                  border=P_GEN[0], lc=P_GEN[2], size=10.5, fill="#FBF3E4"))
    c.append(txt(296, gy + 214,
                 "Finding that drives the layer above: prompt-level numeric bounds were ignored repeatedly, so cross-agent constraints are enforced in code.",
                 9, MUTED, "start", italic=True))

    # =========================== OPERATING LAYER =============================
    oy = 478
    c.append(panel(276, oy, 1050, 318,
                   "OPERATING LAYER  \u00b7  runs indefinitely, operates that state",
                   P_OPS, "the plan becomes the company's opening state, not the deliverable"))

    c.append(card(296, oy + 56, 152, 56, "Cadence\nScheduler", "clock",
                  border=P_OPS[0] + "80", lc=P_OPS[2], size=10))
    c.append(txt(372, oy + 122, "clock-injected", 8.4, MUTED, "middle"))

    c.append(card(468, oy + 56, 176, 56, "5 Department\nLoops", "people",
                  border=P_OPS[0] + "80", lc=P_OPS[2], size=10))
    c.append(txt(556, oy + 122, "plan \u2192 execute \u2192 record", 8.4, MUTED, "middle"))

    c.append(card(664, oy + 56, 190, 56, "Governance\nGate Chain", "shield",
                  border=P_OPS[0] + "80", lc=P_OPS[2], size=10))
    c.append(txt(759, oy + 122, "3 of 5 stages can halt", 8.4, MUTED, "middle"))

    # anchors block - the centrepiece
    c.append(panel(874, oy + 44, 432, 128, "ANCHORS  \u00b7  computed, never reported",
                   P_ANCH))
    c.append(card(890, oy + 78, 200, 78, "Append-only\nLedger", "db",
                  "every event, attributed", border=P_ANCH[0], lc=P_ANCH[2], size=10))
    c.append(card(1104, oy + 78, 186, 78, "19 Anchor\nMetrics", "lockdb",
                  "not stored anywhere", border=P_ANCH[0], lc=P_ANCH[2], size=10))
    c.append(arrow(1090, oy + 117, 1104, oy + 117, "read"))

    mons = [("Goodhart Detector", "claim vs ledger", "search"),
            ("Conflict Detector", "cross-department", "scale"),
            ("Drift Monitor", "metric freshness", "bell"),
            ("Objective Review", "should this goal exist?", "target")]
    for i, (t, sub, ic) in enumerate(mons):
        c.append(card(296 + i * 194, oy + 186, 182, 54, t, ic, sub,
                      border=P_OPS[0] + "80", lc=P_OPS[2], size=9.8))
    c.append(card(1074, oy + 186, 232, 54, "Reflection + Memory", "cycle",
                  "verdict from measured deltas", border=P_OPS[0] + "80",
                  lc=P_OPS[2], size=9.8))

    c.append(card(296, oy + 252, 500, 44, "Constitution  \u2014  7 hard constraints in code",
                  "shield", "spend caps \u00b7 no data deletion \u00b7 no payment without verification",
                  border="#C2544C", lc="#A63B33", size=10.5, fill="#FCF1F0"))
    c.append(card(812, oy + 252, 494, 44, "Human Supervisor", "user",
                  "approves, rejects, arbitrates \u2014 an approval never unlocks a hard constraint",
                  border=P_CLIENT[0], lc=P_CLIENT[2], size=10.5, fill="#F6F4FD"))

    # =============================== BOTTOM ROW ==============================
    by = 818
    c.append(panel(28, by, 470, 176, "PERSISTENCE", P_DATA))
    c.append(card(46, by + 44, 216, 56, "SQLite  (WAL)", "db",
                  "sessions \u00b7 ledger \u00b7 decisions",
                  border=P_DATA[0] + "70", lc=P_DATA[2], size=10))
    c.append(card(272, by + 44, 208, 56, "ChromaDB", "cloud",
                  "knowledge cache", border=P_DATA[0] + "70", lc=P_DATA[2], size=10))
    c.append(dashed_note(46, by + 110, 434,
                         ["audit trail and ledger are append-only, enforced by database triggers",
                          "5 isolated department memory stores, 4 typed each"]))

    c.append(panel(516, by, 396, 176, "GROUNDING  (external)", P_GROUND))
    c.append(card(534, by + 44, 176, 56, "OpenStreetMap", "cloud",
                  "competitors, 2 km radius",
                  border=P_GROUND[0] + "70", lc=P_GROUND[2], size=10))
    c.append(card(718, by + 44, 176, 56, "Serper", "search",
                  "market statistics",
                  border=P_GROUND[0] + "70", lc=P_GROUND[2], size=10))
    c.append(dashed_note(534, by + 110, 360,
                         ["retrieved data overrides generated data for the same field",
                          "every record keeps a source label"]))

    c.append(panel(930, by, 396, 176, "LLM LAYER  \u00b7  free tiers only", P_LLM))
    for i, (n, sub) in enumerate([("Groq", "70B / 8B"), ("Gemini", "Flash"),
                                  ("Ollama", "local fallback")]):
        c.append(card(948 + i * 126, by + 44, 116, 56, n, "brain", sub,
                      border=P_LLM[0] + "70", lc=P_LLM[2], size=10))
    c.append(dashed_note(948, by + 110, 360,
                         ["ordered fallback chain; a run completes even when hosted tiers are exhausted",
                          "no agent imports a vendor SDK"]))

    # =============================== LEGEND ==================================
    c.append(f'<rect x="1350" y="{by}" width="262" height="176" rx="10" '
             f'fill="#FAFBFD" stroke="{LINE}" stroke-width="1.4"/>')
    c.append(txt(1481, by + 24, "LEGEND", 11.5, MUTED, "middle", "700", spacing=1))
    leg = [("data", "Work / data flow"), ("eval", "Control / evaluation"),
           ("read", "Read-only (anchors)"), ("block", "Blocked by a constraint")]
    for i, (k, label) in enumerate(leg):
        y = by + 48 + i * 24
        c.append(arrow(1368, y, 1404, y, k))
        c.append(txt(1412, y + 3.5, label, 9.6, MUTED))
    c.append(dashed_note(1366, by + 146, 230,
                         ["869 tests \u00b7 \u20b90 cost \u00b7 fully offline"]))

    # =============================== ARROWS ==================================
    c.append(arrow(252, 236, 276, 236, "data"))              # clients -> API
    c.append(arrow(801, 184, 801, 206, "data"))              # API -> generation
    c.append(arrow(801, 456, 801, 478, "data", "plan becomes state"))
    c.append(arrow(446, gy + 82, 466, gy + 82, "data"))      # intent -> orchestrator
    c.append(arrow(616, gy + 82, 640, gy + 82, "data"))      # orchestrator -> depts
    c.append(arrow(1326, 236, 1350, 236, "eval"))            # API -> evaluation
    c.append(arrow(448, oy + 84, 468, oy + 84, "data"))      # scheduler -> depts
    c.append(arrow(644, oy + 84, 664, oy + 84, "data"))      # depts -> governance
    c.append(arrow(854, oy + 84, 890, oy + 100, "data", "events"))
    c.append(arrow(1104, oy + 156, 1000, oy + 200, "read", "read-only", curve=0.06))
    c.append(arrow(890, oy + 156, 700, oy + 200, "read", curve=0.05))
    c.append(arrow(500, oy + 240, 520, oy + 252, "block"))
    c.append(arrow(1000, oy + 240, 1010, oy + 252, "eval", "escalate"))
    c.append(arrow(700, oy + 296, 700, 818, "data"))         # ops -> persistence
    c.append(arrow(560, gy + 118, 560, oy + 44, "data") if False else "")
    c.append(arrow(1128, by, 1128, oy + 296, "eval"))        # llm -> operating
    c.append(arrow(712, 796, 712, 818, "data") if False else "")

    c.append(txt(28, H - 14,
                 "Anchors are computed, never reported: no department, planner, worker or reflection process can write one \u2014 there is no anchor table, so there is nowhere to write.",
                 9.6, P_ANCH[2], "start", "600"))
    c.append(txt(W - 28, H - 14, "Vinayak Maurya  \u00b7  University of Mumbai",
                 9.6, MUTED, "end"))

    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(c) + "</svg>")


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path("overview.svg")
    out.write_text(overview(), encoding="utf8")
    print("svg written", len(out.read_text(encoding="utf8")), "bytes")
