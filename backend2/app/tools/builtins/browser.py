r"""Browser-automation action tool — SCAFFOLD (Step 4).

Last-resort action path: when no API/MCP tool exists for a target action, an
agent can drive a real headless browser (Playwright) to do it the way a human
would — open a page, click, type, submit. This is how "do anything on any site"
becomes possible without a per-site API.

STATUS: UNVERIFIED SCAFFOLD. This is intentionally gated OFF by default and is
NOT claimed to work end-to-end, because making it real requires, in the user's
own environment:
  1. Installing Playwright + a Chromium runtime:
        ..\.venv\Scripts\python.exe -m pip install playwright
        ..\.venv\Scripts\python.exe -m playwright install chromium
  2. Enabling it:  BROWSER_ACTION_ENABLED=true  in the backend .env
  3. Real account logins / stored sessions for sites that require auth (the user
     must do this; the agent cannot be handed real credentials here).

Until (1)+(2), this tool returns a clear 'disabled' result and never pretends to
act. The approval gate (Step 2) applies to it like any action tool.
"""

from __future__ import annotations

from app.config import settings
from app.tools.base import ToolContext, err, need, ok, tool


def _enabled() -> bool:
    return bool(getattr(settings, "browser_action_enabled", False))


@tool(
    "browser_action",
    display_name="Browser Action (automation)",
    description="Drive a real headless browser to perform an action on a website that has no "
    "API (navigate, click, type, submit). ACTION — requires approval. LAST-RESORT fallback. "
    "Input: {url, steps:[{action:'goto|click|type|press|wait', selector?, text?, value?}]}.",
    category="utility",
    # Registered but off: it needs the Playwright runtime + an explicit enable flag.
    degraded=True,
)
async def browser_action(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "url")):
        return err(m)

    if not _enabled():
        return err(
            "Browser automation is disabled. To enable: pip install playwright && "
            "python -m playwright install chromium, then set BROWSER_ACTION_ENABLED=true. "
            "It also needs you to log into the target site in a persistent profile.",
            degraded=True, needs_setup="browser",
        )

    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except Exception:  # noqa: BLE001
        return err("Playwright is not installed. Run: pip install playwright && "
                   "python -m playwright install chromium.", degraded=True, needs_setup="browser")

    url = ti["url"].strip()
    steps = ti.get("steps") or []
    log: list[dict] = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            # headless by default; a persistent context would carry logins (future).
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            log.append({"action": "goto", "url": url})
            for s in steps:
                act = (s.get("action") or "").lower()
                sel = s.get("selector")
                if act == "goto" and s.get("value"):
                    await page.goto(s["value"], timeout=30000)
                elif act == "click" and sel:
                    await page.click(sel, timeout=15000)
                elif act == "type" and sel:
                    await page.fill(sel, s.get("text", ""))
                elif act == "press" and sel:
                    await page.press(sel, s.get("value", "Enter"))
                elif act == "wait":
                    await page.wait_for_timeout(int(s.get("value") or 1000))
                else:
                    log.append({"skipped": s})
                    continue
                log.append({"action": act, "selector": sel})
            title = await page.title()
            await browser.close()
        return ok(performed=True, final_title=title, steps_run=len(log), log=log)
    except Exception as e:  # noqa: BLE001
        return err(f"browser_action failed: {e}", degraded=True, log=log)
