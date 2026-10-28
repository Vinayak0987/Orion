"""The Engine — orchestrates a whole mission.

plan → save tasks → run tasks in dependency order (parallel where possible) →
mark complete. Streams events throughout. Fully async; independent tasks run
concurrently via asyncio.create_task.
"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.llm.client import LLMClient
from app.missions import events, planner, store
from app.missions.executor import run_task
from app.missions.router import resolve as _resolve


async def run_mission(mission_id: str, skip_clarify: bool = False) -> None:
    emit = events.make_emitter(mission_id)
    try:
        await asyncio.wait_for(
            _run(mission_id, emit, skip_clarify=skip_clarify),
            timeout=settings.mission_timeout_seconds,
        )
    except asyncio.TimeoutError:
        store.set_mission(mission_id, status="partial", completed_at=_now())
        await emit("mission_failed",
                   error=f"Mission exceeded the time limit ({settings.mission_timeout_seconds}s) "
                   "and was stopped. Partial results may be available.")
    except Exception as e:  # noqa: BLE001 - never let the engine crash silently
        store.set_mission(mission_id, status="failed")
        await emit("mission_failed", error=str(e))
    finally:
        await events.finish(mission_id)


async def _run(mission_id: str, emit, skip_clarify: bool = False) -> None:
    mission = store.get_mission(mission_id)
    if mission is None:
        return

    user_id = mission.get("created_by", "default-user")
    conversation_id = mission.get("conversation_id")

    # Load the user's decrypted API keys and attach to the mission so the
    # Executor's LLMClient and tool dispatch use them (Settings → mission flow).
    from app.settings.store import decrypted_keys

    mission["user_keys"] = decrypted_keys(user_id)

    llm = LLMClient(user_keys=mission.get("user_keys"))

    # --- MASTER: route the goal to a department (unless one was explicitly set
    # by the Command Center, or routing says handle directly). ---
    if not mission.get("department_id"):
        try:
            from app.missions import master
            decision = await master.route_goal(
                mission["prompt"], created_by=user_id, user_keys=mission.get("user_keys"))
            if decision.get("department_id"):
                store.set_mission(mission_id, department_id=decision["department_id"])
                mission["department_id"] = decision["department_id"]
                await emit("routed_to_department",
                           department_id=decision["department_id"],
                           department_name=decision.get("department_name"),
                           reason=decision.get("reason"))
            else:
                await emit("handled_directly", reason=decision.get("reason"))
        except Exception:  # noqa: BLE001 — routing must never block the mission
            pass

    # --- Short-term memory: recent turns in THIS conversation ---
    short_term = _short_term_memory(conversation_id, mission_id)
    mission["short_term_memory"] = short_term
    # --- Long-term memory + global context: durable facts across ALL chats ---
    from app.chat.store import context_block

    long_term = context_block(user_id)

    # --- Clarifying question (one round, unless the user already answered) ---
    # Chart/visualization + creative/generation prompts are actionable — skip clarify.
    _p = (mission.get("prompt") or "").lower()
    _is_viz = any(k in _p for k in (
        "chart", "plot", "graph", "matplotlib", "visualiz", "bar chart", "line chart",
        "pie chart", "histogram", "code_interpreter",
        "banner", "advertisement", " ad ", "ad ", "ads", "image", "poster", "logo",
        "design", "generate", "create a", "create an", "video", "flyer", "creative",
        "mockup", "render",
    ))
    if not skip_clarify and not _is_viz:
        store.set_mission(mission_id, status="planning")
        await emit("planning_started")  # show feedback immediately
        from app.missions import planner as _planner

        try:
            clar = await asyncio.wait_for(
                _planner.clarify(mission["prompt"], llm, context=short_term),
                timeout=settings.planning_timeout_seconds,
            )
        except asyncio.TimeoutError:
            clar = {}  # don't block on a slow clarify — just proceed to planning
        if clar:
            store.set_mission(mission_id, status="awaiting_input")
            await emit("clarification_needed", question=clar["question"],
                       original_prompt=mission["prompt"])
            return  # mission pauses; the frontend sends a new /missions call with clarified=true

    # --- Planning ---
    store.set_mission(mission_id, status="planning")
    await emit("planning_started")

    # Title + plan are independent → run them concurrently to cut latency, with
    # a hard timeout so a slow/hung model can't leave the mission "Thinking…".
    try:
        mode = mission.get("mode", "action")
        catalog = planner.tool_catalog_text(mode, goal=mission["prompt"])
        title, tasks = await asyncio.wait_for(
            asyncio.gather(
                planner.generate_title(mission["prompt"], llm),
                planner.plan(mission["prompt"], llm, context=long_term, memory=short_term,
                             tool_catalog=catalog),
            ),
            timeout=settings.planning_timeout_seconds,
        )
    except asyncio.TimeoutError:
        # Planning was slow (common with a slow local model). Rather than failing
        # the whole mission, degrade to a SINGLE task = run the goal directly.
        await emit("planning_timeout_fallback")
        title = mission["prompt"][:60]
        tasks = [{
            "title": mission["prompt"][:120],
            "agent_type": "general",
            "tools_needed": ["web_search", "document_rag"],
            "depends_on": [],
        }]

    store.set_mission(mission_id, title=title)

    if not tasks:
        # No multi-step plan (common for simple/direct questions). Instead of
        # failing, run the goal as ONE task so it still gets answered.
        tasks = [{
            "title": mission["prompt"][:120],
            "agent_type": "general",
            "tools_needed": ["web_search", "document_rag"],
            "depends_on": [],
        }]

    saved = store.save_tasks(mission_id, tasks)
    for t in saved:
        await emit("task_created", task={
            "id": t["id"], "title": t["title"], "agent_type": t["agent_type"],
            "depends_on": t["depends_on"], "tools_needed": t["tools_needed"],
        })
    await emit("planning_complete", task_count=len(saved))

    # --- Execution (dependency graph) ---
    store.set_mission(mission_id, status="running")
    mission = store.get_mission(mission_id)  # refresh with tasks

    by_title = {t["title"]: t for t in saved}
    completed: set[str] = set()
    running: set[str] = set()
    results: dict[str, dict] = {}
    lock = asyncio.Lock()

    async def execute(task: dict) -> None:
        decision = _resolve(task, mission)
        agent_id = decision["agent_id"]
        if decision.get("is_head") and decision.get("department_id"):
            task["_delegate_head"] = True
            task["_department_id"] = decision["department_id"]
        store.set_task(task["id"], agent_id=agent_id, status="running")
        agent_name = _agent_name(agent_id)
        await emit("task_started", task_id=task["id"], agent_id=agent_id, agent_name=agent_name)
        try:
            result = await asyncio.wait_for(
                run_task(agent_id, task, dict(results), mission, emit),
                timeout=settings.task_timeout_seconds,
            )
            status = "failed" if result.get("error") else "completed"
            store.set_task(task["id"], status=status, result=result, completed_at=_now())
            results[task["title"]] = result
            # Post-task: extract + store durable facts into the agent's memory.
            if status == "completed":
                try:
                    from app.agents.store import get_agent
                    from app.knowledge.memory import extract_and_store_memory

                    agent = get_agent(agent_id)
                    if agent:
                        await extract_and_store_memory(
                            agent, mission["id"], result.get("data") or result.get("summary", "")
                        )
                except Exception:  # noqa: BLE001 — memory must never fail a task
                    pass
            await emit("task_completed", task_id=task["id"],
                       result_summary=result.get("summary", ""))
        except asyncio.TimeoutError:
            store.set_task(task["id"], status="failed",
                           result={"error": "task timed out"}, completed_at=_now())
            await emit("task_failed", task_id=task["id"], error="timed out")
        except Exception as e:  # noqa: BLE001
            store.set_task(task["id"], status="failed",
                           result={"error": str(e)}, completed_at=_now())
            await emit("task_failed", task_id=task["id"], error=str(e))
        finally:
            async with lock:
                completed.add(task["title"])
                running.discard(task["title"])

    async def schedule_ready() -> list:
        started = []
        async with lock:
            for t in saved:
                if t["title"] in completed or t["title"] in running:
                    continue
                if all(dep in completed for dep in t["depends_on"]):
                    running.add(t["title"])
                    started.append(t)
        return [asyncio.create_task(execute(t)) for t in started]

    # Keep scheduling until every task is completed.
    pending: list = []
    while len(completed) < len(saved):
        new = await schedule_ready()
        pending.extend(new)
        if not pending:
            # Deadlock guard (should not happen — depends_on is validated).
            break
        done, pending_set = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        pending = list(pending_set)

    # --- Done ---
    final_status = "completed"
    with_errors = any(
        (by_title.get(t) and results.get(t, {}).get("error")) for t in results
    )
    if with_errors and not any(not results.get(t, {}).get("error") for t in results):
        final_status = "failed"
    elif with_errors:
        final_status = "partial"

    store.set_mission(mission_id, status=final_status, completed_at=_now())

    outputs = [{"task": title, "result": r} for title, r in results.items()]

    # --- Stream the final answer as chunks (typewriter UX on the client) ---
    answer = _compose_answer(outputs)
    if answer:
        async for chunk in _chunker(answer):
            await emit("answer_chunk", text=chunk)

    await emit("mission_completed", status=final_status, outputs=outputs, answer=answer)

    # --- Automatic long-term memory: extract durable facts (best-effort) ---
    await _learn_memory(mission_id, conversation_id, user_id, llm, emit)


def _short_term_memory(conversation_id: str | None, mission_id: str) -> str:
    """Recent turns in this conversation, rendered for prompt injection."""
    if not conversation_id:
        return ""
    try:
        from app.chat.store import list_messages

        msgs = list_messages(conversation_id)
        # exclude the just-created running assistant placeholder / empty content
        turns = [m for m in msgs if m.get("content")][-8:]
        if not turns:
            return ""
        lines = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in turns)
        return f"Recent conversation (for continuity):\n{lines}"
    except Exception:
        return ""


def _compose_answer(outputs: list[dict]) -> str:
    """Join task outputs into a single readable answer for streaming."""
    parts = []
    for o in outputs:
        r = o.get("result") or {}
        body = r.get("data") or r.get("summary") or r.get("error") or ""
        if body:
            if len(outputs) > 1:
                parts.append(f"**{o['task']}**\n{body}")
            else:
                parts.append(body)
    return "\n\n".join(parts).strip()


async def _chunker(text: str, size: int = 24, delay: float = 0.03):
    """Yield text in small chunks with a tiny delay so the UI types it out."""
    for i in range(0, len(text), size):
        yield text[i:i + size]
        await asyncio.sleep(delay)


async def _learn_memory(mission_id, conversation_id, user_id, llm, emit) -> None:
    if not conversation_id:
        return
    try:
        from app.chat.store import list_messages, set_context
        from app.missions import planner as _planner

        msgs = list_messages(conversation_id)
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in msgs if m.get("content"))
        if not convo.strip():
            return
        facts = await _planner.extract_memory(convo, llm)
        for f in facts:
            set_context(user_id, f["key"], f["value"])
        if facts:
            await emit("memory_updated", facts=facts)
    except Exception:
        pass  # memory is best-effort; never affects the mission


def _agent_name(agent_id: str) -> str:
    from app.agents.store import get_agent
    a = get_agent(agent_id)
    return a["name"] if a else agent_id


def _now() -> str:
    from app.db.sqlite import _now as now
    return now()
