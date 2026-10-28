"""Department Architect — NL description → structured department proposal
(reuses the shared LLMClient). Returns a proposal only; persisted on confirm."""

from __future__ import annotations

from app.llm.client import LLMClient

_VALID = {"marketing", "sales", "finance", "research", "engineering", "product",
          "operations", "customer_success", "hr", "legal", "custom"}

_SYSTEM = ("You are Orion's Department Architect. Design a business department "
           "(purpose, responsibilities, and suggested specialist roles). STRICT JSON only.")


def _prompt(desc: str) -> str:
    return f"""Design a department from this description:
\"\"\"{desc.strip()}\"\"\"
Return STRICT JSON:
{{"name":"...","dept_type":"marketing|sales|finance|research|engineering|product|operations|customer_success|hr|legal|custom",
"description":"one sentence","purpose":"one sentence","responsibilities":["..."],
"instructions":"2-3 sentence operating instruction for the head",
"suggested_roles":[{{"name":"role name","purpose":"what they do"}}]}}
Rules: 3-6 responsibilities; 2-5 suggested_roles. Return ONLY the JSON object."""


def _normalize(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    dt = str(raw.get("dept_type") or "custom").strip().lower()
    if dt not in _VALID:
        dt = "custom"
    roles = [{"name": str(r.get("name", "")).strip()[:120], "purpose": (r.get("purpose") or "").strip()}
             for r in (raw.get("suggested_roles") or []) if isinstance(r, dict) and r.get("name")]
    resp = [str(x).strip() for x in (raw.get("responsibilities") or []) if str(x).strip()]
    return {
        "name": (raw.get("name") or "New Department").strip()[:120],
        "dept_type": dt,
        "description": (raw.get("description") or "").strip(),
        "purpose": (raw.get("purpose") or "").strip(),
        "responsibilities": resp[:8],
        "instructions": (raw.get("instructions") or "").strip(),
        "suggested_roles": roles[:6],
    }


async def design_department(description: str, *, user_keys: dict | None = None) -> dict:
    llm = LLMClient(user_keys=user_keys)
    raw = await llm.call_structured(_prompt(description), system=_SYSTEM, tier="reasoning")
    return _normalize(raw)
