"""Probe every LLM provider in the chain with the SAME tasks.

Tests two things per provider:
  1. Plain reply (does it respond at all?)
  2. Tool-call JSON (can it emit the structured tool call our agents need?)

Run:  python test_all_llms.py
"""
import asyncio
import time

from app.config import Settings
from app.settings.store import decrypted_keys
from app.llm.providers import GroqProvider, GeminiProvider, OpenAICompatProvider, OllamaProvider

s = Settings()
ks = decrypted_keys("default-user")

# NVIDIA now uses Nemotron 3.5 Bolt E4B per request.
NIM_MODEL = "nvidia/nemotron-3.5-bolt-e4b"

PLAIN = [{"role": "user", "content": "Reply with exactly one word: READY"}]
TOOL = [{"role": "user", "content":
         'To use a tool, reply with ONLY this JSON and nothing else: '
         '{"tool": "calculator", "input": {"expression": "<expr>"}}. '
         'Use the calculator tool to compute 15 * 12.'}]


def providers():
    out = []
    gk = ks.get("groq_api_key") or (s.groq_api_key if s.groq_available else None)
    if gk:
        out.append(("groq", GroqProvider(gk)))
    if s.nvidia_nim_available:
        out.append(("nvidia_nim (bolt-e4b)",
                    OpenAICompatProvider("nvidia_nim", "https://integrate.api.nvidia.com/v1",
                                         s.nvidia_nim_api_key, NIM_MODEL, NIM_MODEL)))
    if s.openrouter_available:
        out.append(("openrouter",
                    OpenAICompatProvider("openrouter", "https://openrouter.ai/api/v1",
                                         s.openrouter_api_key, s.openrouter_model_fast,
                                         s.openrouter_model_reasoning,
                                         {"HTTP-Referer": "https://orion.local", "X-Title": "Orion"})))
    if s.gemini_available:
        out.append(("gemini", GeminiProvider(s.gemini_api_key)))
    out.append(("ollama:qwen2.5:7b", OllamaProvider(model="qwen2.5:7b-instruct")))
    return out


async def run_one(name, provider):
    for label, msgs, tier in [("PLAIN", PLAIN, "fast"), ("TOOL ", TOOL, "reasoning")]:
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(provider.call(msgs, tier, 0.2), timeout=60)
            dt = time.monotonic() - t0
            text = (r.text or "").replace("\n", " ")[:70]
            print(f"  [{label}] {dt:5.1f}s  {r.model[:30]:30}  -> {text!r}", flush=True)
        except asyncio.TimeoutError:
            dt = time.monotonic() - t0
            print(f"  [{label}] {dt:5.1f}s  TIMEOUT (>60s)", flush=True)
        except Exception as e:
            dt = time.monotonic() - t0
            print(f"  [{label}] {dt:5.1f}s  FAILED -> {type(e).__name__}: {str(e)[:80]}", flush=True)


async def main():
    print("=" * 80)
    print("LLM PROVIDER PROBE — same task to every provider")
    print("=" * 80)
    for name, p in providers():
        print(f"\n### {name}", flush=True)
        await run_one(name, p)
    print("\n" + "=" * 80)
    print("Done. PLAIN = responds at all. TOOL = can emit tool-call JSON (what agents need).")


if __name__ == "__main__":
    asyncio.run(main())
