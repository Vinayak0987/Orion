"""Run a mission and DEBUG every step: event timeline with per-step timing,
which LLM provider/model handled each call, which tools were called, and where
it failed. Run:  python debug_mission.py "<prompt>"
"""
import asyncio
import json
import sys
import time

import httpx
import websockets

BASE = "http://127.0.0.1:8081"
WS = "ws://127.0.0.1:8081"


async def run(prompt: str, mode: str = "action"):
    t_start = time.monotonic()

    def ts() -> str:
        return f"[{time.monotonic() - t_start:7.1f}s]"

    r = httpx.post(f"{BASE}/missions", json={"prompt": prompt, "mode": mode}, timeout=20).json()
    mid = r.get("mission_id") or r.get("id")
    print(f"{ts()} MISSION CREATED: {mid}")
    print(f"{ts()} prompt: {prompt}\n")

    last_event = time.monotonic()
    interesting = {
        "planning_started", "routed_to_department", "handled_directly",
        "head_planning", "specialist_created", "specialist_started", "specialist_done",
        "subagent_created", "subagent_started", "subagent_done", "head_done",
        "task_created", "task_started", "task_completed", "task_failed",
        "tool_call", "tool_result", "approval_required",
        "mission_completed", "mission_failed", "clarification_needed",
    }
    try:
        async with websockets.connect(f"{WS}/ws/missions/{mid}", open_timeout=15) as ws:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=400)
                except asyncio.TimeoutError:
                    print(f"{ts()} [WS TIMEOUT — no events for 400s, giving up]")
                    break
                ev = json.loads(raw)
                k = ev.get("event") or ev.get("type")
                if k not in interesting:
                    continue
                gap = time.monotonic() - last_event
                last_event = time.monotonic()
                # Build a compact detail string.
                det = {kk: ev[kk] for kk in (
                    "department_name", "name", "capability", "tool", "success",
                    "task", "task_id", "title", "images", "reason", "subtask", "error",
                ) if kk in ev and ev[kk] not in (None, "", [])}
                if "task" in det and isinstance(det["task"], dict):
                    det["task"] = det["task"].get("title", det["task"])
                print(f"{ts()} (+{gap:5.1f}s) {k:22} {json.dumps(det, default=str)[:140]}")
                if k in ("mission_completed", "mission_failed", "clarification_needed"):
                    break
    except Exception as e:
        print(f"{ts()} [WS ERROR: {type(e).__name__}: {e}]")

    # Post-run: full trace with per-step timing + providers/tools.
    print(f"\n{ts()} ===== POST-RUN TRACE =====")
    s = httpx.get(f"{BASE}/missions/{mid}", timeout=10).json()
    print(f"final status: {s.get('status')} | department: {s.get('department_id')}")
    from app.traces.store import list_traces
    traces = list_traces(mid)
    for tr in traces:
        if tr["trace_type"] == "llm":
            print(f"  LLM   {tr.get('provider'):14} {str(tr.get('model'))[:34]:34} "
                  f"{tr.get('latency_ms', 0):6}ms  success={tr.get('success')}")
        elif tr["trace_type"] == "tool":
            print(f"  TOOL  {str(tr.get('tool_name')):30} {tr.get('latency_ms', 0):6}ms  "
                  f"success={tr.get('success')}  err={str(tr.get('error') or '')[:50]}")
    print("\n  --- tasks ---")
    for t in s.get("tasks", []):
        o = t.get("result") or {}
        out = (o.get("data") or o.get("summary") or o.get("error") or "") if isinstance(o, dict) else str(o)
        print(f"  [{t.get('status'):9}] {t.get('title')[:45]:45} needs={t.get('tools_needed')} "
              f"-> {out[:60]!r}")
    # Charts produced?
    imgs = [i for t in s.get("tasks", []) if isinstance(t.get("result"), dict)
            for i in (t["result"].get("images") or [])]
    print(f"\n  charts/images produced: {imgs}")
    print(f"{ts()} TOTAL WALL TIME")


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "Generate an image banner advertisement for our product: a milk packet, "
        "brand name Accesco, offer Buy One Get One Free, only at 99 rupees."
    )
    asyncio.run(run(prompt))
