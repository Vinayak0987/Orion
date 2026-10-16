"""The Executor — runs one task through an agent using a ReAct loop.

The agent is prompted to either (a) emit a JSON tool call, or (b) give a final
prose answer. The executor parses each LLM reply: if it is a tool call, it
dispatches the tool and feeds the result back; otherwise the task is done.

Every LLM call and tool call is logged to execution_traces. The loop is capped
at settings.max_task_steps to prevent runaway tool-calling.
"""

from __future__ import annotations

import json

from app.agents.store import get_agent
from app.config import settings
from app.llm.client import LLMClient
from app.llm.repair import extract_json
from app.tools import registry
from app.traces import store as traces


def _tier_for(agent: dict) -> str:
    model = agent.get("model", "")
    # 70b / reasoning-class models → reasoning tier; else fast.
    return "reasoning" if "70b" in model or "reasoning" in model else "fast"


def _parse_tool_call(text: str) -> dict | None:
    """If the reply is (or contains) a tool-call JSON object, return it. Else None."""
    stripped = text.strip()
    if "{" not in stripped:
        return None
    try:
        obj = extract_json(stripped)
    except Exception:
        return None
    if isinstance(obj, dict) and "tool" in obj:
        return {"tool": obj["tool"], "input": obj.get("input", {})}
    return None


def _build_messages(agent: dict, task: dict, context: dict, memory: str = "") -> list[dict]:
    tools = agent.get("tools", [])
    tool_lines = "\n".join(
        f"- {t['name']}: {t['description']}"
        for t in registry.list_tools() if t["name"] in tools
    ) or "(no tools available — rely on your own knowledge)"

    context_block = ""
    if context:
        context_block = "\n\nResults from previous tasks:\n" + json.dumps(context, indent=2)[:4000]

    memory_block = f"\n\n{memory}" if memory else ""

    user = (
        f"Available tools:\n{tool_lines}{memory_block}\n{context_block}\n\n"
        f"Your task: {task['title']}\n\n"
        "Work step by step. Call tools as needed, then give your final answer."
    )
    return [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": user},
    ]


async def run_task(agent_id: str, task: dict, context: dict, mission: dict, emit) -> dict:
    agent = get_agent(agent_id)
    if agent is None:
        return {"summary": "Agent not found", "error": f"no agent {agent_id}"}

    allowed_tools = set(agent.get("tools", []))
    llm = LLMClient(user_keys=mission.get("user_keys"))
    tier = _tier_for(agent)
    messages = _build_messages(agent, task, context, memory=mission.get("short_term_memory", ""))

    for _ in range(settings.max_task_steps):
        # --- LLM step ---
        try:
            result = await llm.call(messages, tier=tier, temperature=agent.get("temperature", 0.7))
        except Exception as e:  # AllProvidersFailedError or any provider issue
            traces.record_llm(
                mission["id"], task["id"], agent_id, provider="none", model="none",
                input_tokens=0, output_tokens=0, cost_usd=0.0, latency_ms=0,
                success=False, error=str(e),
            )
            return {"summary": "LLM unavailable", "error": str(e)}

        traces.record_llm(
            mission["id"], task["id"], agent_id, provider=result.provider, model=result.model,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            cost_usd=result.cost_usd, latency_ms=result.latency_ms, success=True,
        )

        tool_call = _parse_tool_call(result.text)
        if tool_call is None:
            # Final answer. If the model returned nothing usable, retry once
            # with an explicit instruction before giving up (prevents blank "—").
            answer = result.text.strip()
            if not answer:
                messages.append({"role": "assistant", "content": result.text})
                messages.append({
                    "role": "user",
                    "content": "Your reply was empty. Provide the complete answer to the task "
                    "now, in clear prose/markdown. Do not call a tool.",
                })
                try:
                    retry = await llm.call(messages, tier=tier, temperature=agent.get("temperature", 0.7))
                    traces.record_llm(
                        mission["id"], task["id"], agent_id, provider=retry.provider, model=retry.model,
                        input_tokens=retry.input_tokens, output_tokens=retry.output_tokens,
                        cost_usd=retry.cost_usd, latency_ms=retry.latency_ms, success=True,
                    )
                    answer = retry.text.strip()
                except Exception:
                    pass
            if not answer:
                return {"summary": "No output produced",
                        "error": "The agent returned an empty response for this task."}
            return {"summary": answer[:500], "data": answer}

        tool_name = tool_call["tool"]
        tool_input = tool_call["input"]

        # Enforce the agent's allowed-tools list.
        if tool_name not in allowed_tools:
            messages.append({"role": "assistant", "content": result.text})
            messages.append({
                "role": "user",
                "content": f"You are not allowed to use '{tool_name}'. "
                f"Use only: {sorted(allowed_tools) or 'no tools'}. Continue.",
            })
            continue

        # --- Tool step ---
        await emit("tool_call", task_id=task["id"], tool=tool_name, input=tool_input)
        import time
        t0 = time.monotonic()
        tool_result = await registry.dispatch(tool_name, tool_input, mission.get("user_keys"))
        latency = int((time.monotonic() - t0) * 1000)
        ok = "error" not in tool_result
        traces.record_tool(
            mission["id"], task["id"], agent_id, tool_name=tool_name, tool_input=tool_input,
            tool_output=tool_result, latency_ms=latency, success=ok,
            error=tool_result.get("error") if not ok else None,
        )
        await emit("tool_result", task_id=task["id"], tool=tool_name, success=ok)

        # Feed the tool result back to the agent.
        messages.append({"role": "assistant", "content": result.text})
        messages.append({
            "role": "user",
            "content": f"Tool '{tool_name}' returned:\n{json.dumps(tool_result)[:3000]}\n\n"
            "Continue, or give your final answer.",
        })

    # Hit the step cap — force a final answer.
    messages.append({
        "role": "user",
        "content": "You have reached the tool-call limit. Give your final answer now, as prose.",
    })
    try:
        final = await llm.call(messages, tier=tier)
        traces.record_llm(
            mission["id"], task["id"], agent_id, provider=final.provider, model=final.model,
            input_tokens=final.input_tokens, output_tokens=final.output_tokens,
            cost_usd=final.cost_usd, latency_ms=final.latency_ms, success=True,
        )
        answer = final.text.strip()
        if not answer:
            return {"summary": "No output produced",
                    "error": "The agent reached the tool-call limit without producing an answer."}
        return {"summary": answer[:500], "data": answer}
    except Exception as e:
        return {"summary": "Could not complete", "error": str(e)}
