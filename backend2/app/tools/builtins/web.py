"""Web & Research built-in tools (18).

All network calls are wrapped so a failure degrades to {error, degraded} rather
than raising. web_search prefers Serper (if a key is set) and falls back to the
keyless DuckDuckGo (ddgs). HTML parsing prefers BeautifulSoup+lxml.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx

from app.config import settings
from app.tools.base import ToolContext, err, need, ok, tool
from app.tools.sandbox import fetch, valid_url

SERPER_URL = "https://google.serper.dev/search"
SERPER_NEWS_URL = "https://google.serper.dev/news"


def _soup(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "lxml")


def _clean_text(html: str) -> str:
    soup = _soup(html)
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


# --- 1. web_search -----------------------------------------------------------
@tool(
    "web_search",
    description="Search the web for current information. Prefers Serper (needs SERPER_API_KEY) and "
    "falls back to keyless DuckDuckGo. Input: {query: str, num?: int}. Returns ranked results.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "num": {"type": "integer"}},
    requires_key="serper",
)
async def web_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m)
    query = ti["query"].strip()
    num = int(ti.get("num") or 10)
    key = (ctx.user_keys or {}).get("serper_api_key") or settings.serper_api_key
    if key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post(SERPER_URL, headers={"X-API-KEY": key}, json={"q": query, "num": num})
            if r.status_code < 400:
                organic = r.json().get("organic", [])[:num]
                return ok(results=[{"title": o.get("title"), "link": o.get("link"),
                                    "snippet": o.get("snippet")} for o in organic],
                          count=len(organic), source="serper")
        except httpx.HTTPError:
            pass  # fall through to DDG
    # Keyless fallback (DuckDuckGo). Runs in a thread with a hard timeout so an
    # unconfigured / rate-limited search FAILS FAST instead of hanging until the
    # whole task times out.
    try:
        import asyncio

        def _ddg():
            from ddgs import DDGS
            with DDGS() as ddg:
                return list(ddg.text(query, max_results=num))

        hits = await asyncio.wait_for(asyncio.to_thread(_ddg), timeout=8.0)
        results = [{"title": h.get("title"), "link": h.get("href"), "snippet": h.get("body")} for h in hits]
        if not results:
            return err("web_search returned no results (search is unconfigured or rate-limited). "
                       "Proceed with your own knowledge or another tool.", degraded=True, results=[])
        return ok(results=results, count=len(results), source="duckduckgo")
    except asyncio.TimeoutError:
        return err("web_search timed out (no SERPER_API_KEY and the keyless fallback is slow/blocked). "
                   "Proceed with your own knowledge or another tool.", degraded=True, results=[])
    except Exception as e:  # noqa: BLE001
        return err(f"web_search unavailable: {e}", degraded=True, results=[])


# --- 2. web_search_news ------------------------------------------------------
@tool(
    "web_search_news",
    description="Search recent news articles. Prefers Serper news, falls back to keyless DuckDuckGo "
    "news. Input: {query: str, num?: int}.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "num": {"type": "integer"}},
    requires_key="serper",
)
async def web_search_news(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m)
    query, num = ti["query"].strip(), int(ti.get("num") or 10)
    key = (ctx.user_keys or {}).get("serper_api_key") or settings.serper_api_key
    if key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post(SERPER_NEWS_URL, headers={"X-API-KEY": key}, json={"q": query, "num": num})
            if r.status_code < 400:
                news = r.json().get("news", [])[:num]
                return ok(results=[{"title": n.get("title"), "link": n.get("link"),
                                    "snippet": n.get("snippet"), "date": n.get("date"),
                                    "source": n.get("source")} for n in news],
                          count=len(news), provider="serper")
        except httpx.HTTPError:
            pass
    try:
        from ddgs import DDGS

        with DDGS() as ddg:
            hits = list(ddg.news(query, max_results=num))
        results = [{"title": h.get("title"), "link": h.get("url"), "snippet": h.get("body"),
                    "date": h.get("date"), "source": h.get("source")} for h in hits]
        return ok(results=results, count=len(results), provider="duckduckgo")
    except Exception as e:  # noqa: BLE001
        return err(f"web_search_news unavailable: {e}", degraded=True, results=[])


# --- 3. web_scraper ----------------------------------------------------------
@tool(
    "web_scraper",
    description="Fetch a web page and return its clean main text (scripts/nav/ads stripped). "
    "Input: {url: str, max_chars?: int}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "max_chars": {"type": "integer"}},
)
async def web_scraper(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("web_scraper requires a valid http(s) 'url'")
    try:
        r = await fetch(url)
        if r.status_code >= 400:
            return err(f"HTTP {r.status_code} fetching {url}", degraded=True)
        text = _clean_text(r.text)
        max_chars = int(ti.get("max_chars") or 8000)
        return ok(url=str(r.url), status=r.status_code, text=text[:max_chars],
                  truncated=len(text) > max_chars, length=len(text))
    except Exception as e:  # noqa: BLE001
        return err(f"web_scraper failed: {e}", degraded=True)


# --- 4. web_crawler ----------------------------------------------------------
@tool(
    "web_crawler",
    description="Crawl same-domain links starting from a seed URL, up to a page limit, returning each "
    "page's URL + text. Input: {url: str, max_pages?: int (<=10)}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "max_pages": {"type": "integer"}},
)
async def web_crawler(ti: dict, ctx: ToolContext) -> dict:
    seed = (ti.get("url") or "").strip()
    if not valid_url(seed):
        return err("web_crawler requires a valid http(s) 'url'")
    max_pages = min(int(ti.get("max_pages") or 5), 10)
    host = urlparse(seed).netloc
    seen, queue, pages = set(), [seed], []
    while queue and len(pages) < max_pages:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            r = await fetch(u, timeout=10.0)
            if r.status_code >= 400:
                continue
            pages.append({"url": str(r.url), "text": _clean_text(r.text)[:2000]})
            soup = _soup(r.text)
            for a in soup.find_all("a", href=True):
                nxt = urljoin(u, a["href"]).split("#")[0]
                if urlparse(nxt).netloc == host and nxt not in seen:
                    queue.append(nxt)
        except Exception:  # noqa: BLE001 — skip bad pages, keep crawling
            continue
    return ok(pages=pages, count=len(pages), crawled=len(seen))


# --- 5. http_request ---------------------------------------------------------
@tool(
    "http_request",
    description="Make an HTTP request to any API and return the response. Input: "
    "{url: str, method?: GET|POST|PUT|DELETE|PATCH, headers?: object, body?: object, timeout?: number}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "method": {"type": "string"},
                  "headers": {"type": "object"}, "body": {"type": "object"}},
)
async def http_request(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("http_request requires a valid http(s) 'url'")
    method = (ti.get("method") or "GET").upper()
    if method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
        return err(f"unsupported method: {method}")
    timeout = float(ti.get("timeout") or 30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.request(method, url, headers=ti.get("headers") or {}, json=ti.get("body"))
        body: object
        ctype = r.headers.get("content-type", "")
        body = r.json() if "application/json" in ctype else r.text[:8000]
        return ok(status_code=r.status_code, headers=dict(r.headers), body=body)
    except Exception as e:  # noqa: BLE001
        return err(f"http_request failed: {e}", degraded=True)


# --- 6. read_webpage_metadata ------------------------------------------------
@tool(
    "read_webpage_metadata",
    description="Extract a page's title, description, and OpenGraph/meta tags. Input: {url: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def read_webpage_metadata(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        r = await fetch(url)
        soup = _soup(r.text)
        meta = {}
        for m in soup.find_all("meta"):
            k = m.get("property") or m.get("name")
            if k and m.get("content"):
                meta[k] = m["content"]
        title = (soup.title.string.strip() if soup.title and soup.title.string else None)
        return ok(url=str(r.url), title=title, description=meta.get("description") or meta.get("og:description"),
                  meta=meta)
    except Exception as e:  # noqa: BLE001
        return err(f"read_webpage_metadata failed: {e}", degraded=True)


# --- 7. web_link_extractor ---------------------------------------------------
@tool(
    "web_link_extractor",
    description="Extract all hyperlinks (absolute) from a page. Input: {url: str, same_domain?: bool}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "same_domain": {"type": "boolean"}},
)
async def web_link_extractor(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        r = await fetch(url)
        host = urlparse(str(r.url)).netloc
        soup = _soup(r.text)
        links = []
        for a in soup.find_all("a", href=True):
            absu = urljoin(str(r.url), a["href"]).split("#")[0]
            if ti.get("same_domain") and urlparse(absu).netloc != host:
                continue
            links.append({"url": absu, "text": a.get_text(strip=True)[:120]})
        # dedupe by url preserving order
        seen, uniq = set(), []
        for lk in links:
            if lk["url"] not in seen:
                seen.add(lk["url"])
                uniq.append(lk)
        return ok(links=uniq, count=len(uniq))
    except Exception as e:  # noqa: BLE001
        return err(f"web_link_extractor failed: {e}", degraded=True)


# --- 8. web_content_extractor ------------------------------------------------
@tool(
    "web_content_extractor",
    description="Fetch a page and return structured content: title, headings, and paragraphs. "
    "Input: {url: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def web_content_extractor(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        r = await fetch(url)
        soup = _soup(r.text)
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        headings = [h.get_text(strip=True) for h in soup.find_all(re.compile("^h[1-3]$"))][:40]
        paras = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)][:60]
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        return ok(url=str(r.url), title=title, headings=headings, paragraphs=paras)
    except Exception as e:  # noqa: BLE001
        return err(f"web_content_extractor failed: {e}", degraded=True)


# --- 9. url_checker ----------------------------------------------------------
@tool(
    "url_checker",
    description="Check whether a URL is reachable and return its status code + content type. "
    "Input: {url: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def url_checker(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            r = await c.head(url)
            if r.status_code >= 400:  # some servers reject HEAD
                r = await c.get(url)
        return ok(url=str(r.url), ok=r.status_code < 400, status_code=r.status_code,
                  content_type=r.headers.get("content-type"))
    except Exception as e:  # noqa: BLE001
        return err(f"url unreachable: {e}", degraded=True, ok=False)


# --- 10. url_resolver --------------------------------------------------------
@tool(
    "url_resolver",
    description="Follow redirects and return the final destination URL + the redirect chain. "
    "Input: {url: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def url_resolver(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            r = await c.get(url)
        chain = [str(h.url) for h in r.history] + [str(r.url)]
        return ok(final_url=str(r.url), chain=chain, hops=len(r.history))
    except Exception as e:  # noqa: BLE001
        return err(f"url_resolver failed: {e}", degraded=True)


# --- 11. robots_txt_checker --------------------------------------------------
@tool(
    "robots_txt_checker",
    description="Fetch and parse a site's robots.txt, reporting whether a path is allowed for a "
    "user-agent. Input: {url: str, path?: str, user_agent?: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "path": {"type": "string"}},
)
async def robots_txt_checker(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    import urllib.robotparser as rp

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        r = await fetch(robots_url, timeout=10.0)
        parser = rp.RobotFileParser()
        parser.parse(r.text.splitlines())
        ua = ti.get("user_agent") or "*"
        path = ti.get("path") or parsed.path or "/"
        return ok(robots_url=robots_url, allowed=parser.can_fetch(ua, path),
                  path=path, user_agent=ua, exists=r.status_code < 400)
    except Exception as e:  # noqa: BLE001
        return err(f"robots_txt_checker failed: {e}", degraded=True, allowed=True)


# --- 12. sitemap_reader ------------------------------------------------------
@tool(
    "sitemap_reader",
    description="Fetch and parse a sitemap.xml, returning the list of URLs. Input: {url: str} "
    "(the site root or a direct sitemap.xml URL).",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def sitemap_reader(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    if not url.endswith(".xml"):
        p = urlparse(url)
        url = f"{p.scheme}://{p.netloc}/sitemap.xml"
    try:
        r = await fetch(url, timeout=12.0)
        if r.status_code >= 400:
            return err(f"no sitemap at {url}", degraded=True, urls=[])
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", r.text, re.I)
        return ok(sitemap_url=url, urls=locs[:500], count=len(locs))
    except Exception as e:  # noqa: BLE001
        return err(f"sitemap_reader failed: {e}", degraded=True, urls=[])


# --- 13. rss_reader ----------------------------------------------------------
@tool(
    "rss_reader",
    description="Fetch and parse an RSS/Atom feed, returning its items (title, link, date, summary). "
    "Input: {url: str, limit?: int}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "limit": {"type": "integer"}},
)
async def rss_reader(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    limit = int(ti.get("limit") or 20)
    try:
        r = await fetch(url, timeout=12.0)
        soup = _soup(r.text)  # lxml handles xml too
        items = soup.find_all(["item", "entry"])[:limit]
        out = []
        for it in items:
            link = it.find("link")
            link_val = (link.get("href") if link and link.get("href") else (link.get_text(strip=True) if link else None))
            out.append({
                "title": (it.find("title").get_text(strip=True) if it.find("title") else None),
                "link": link_val,
                "date": (it.find(["pubdate", "updated", "published"]).get_text(strip=True)
                         if it.find(["pubdate", "updated", "published"]) else None),
                "summary": (it.find(["description", "summary"]).get_text(strip=True)[:400]
                            if it.find(["description", "summary"]) else None),
            })
        return ok(items=out, count=len(out))
    except Exception as e:  # noqa: BLE001
        return err(f"rss_reader failed: {e}", degraded=True, items=[])


# --- 14. wikipedia_search ----------------------------------------------------
@tool(
    "wikipedia_search",
    description="Search Wikipedia and return a summary of the best-matching article (keyless). "
    "Input: {query: str, lang?: str}.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "lang": {"type": "string"}},
)
async def wikipedia_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m)
    lang = (ti.get("lang") or "en").strip()
    q = ti["query"].strip()
    try:
        async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "OrionAgent/1.0"}) as c:
            s = await c.get(f"https://{lang}.wikipedia.org/w/api.php",
                            params={"action": "query", "list": "search", "srsearch": q,
                                    "format": "json", "srlimit": 1})
            hits = s.json().get("query", {}).get("search", [])
            if not hits:
                return ok(found=False, note="No matching article.")
            title = hits[0]["title"]
            summ = await c.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}")
            d = summ.json()
        return ok(found=True, title=d.get("title"), summary=d.get("extract"),
                  url=d.get("content_urls", {}).get("desktop", {}).get("page"))
    except Exception as e:  # noqa: BLE001
        return err(f"wikipedia_search failed: {e}", degraded=True)


# --- 15. redirect_inspector --------------------------------------------------
@tool(
    "redirect_inspector",
    description="Inspect the full redirect chain of a URL with each hop's status code and location. "
    "Input: {url: str}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}},
)
async def redirect_inspector(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            r = await c.get(url)
        hops = [{"url": str(h.url), "status": h.status_code,
                 "location": h.headers.get("location")} for h in r.history]
        hops.append({"url": str(r.url), "status": r.status_code, "location": None})
        return ok(hops=hops, redirect_count=len(r.history), final_url=str(r.url))
    except Exception as e:  # noqa: BLE001
        return err(f"redirect_inspector failed: {e}", degraded=True)


# --- 16. web_archive_reader --------------------------------------------------
@tool(
    "web_archive_reader",
    description="Look up the most recent Wayback Machine (archive.org) snapshot of a URL (keyless). "
    "Input: {url: str, timestamp?: str (YYYYMMDD)}.",
    category="web",
    input_schema={"url": {"type": "string", "required": True}, "timestamp": {"type": "string"}},
)
async def web_archive_reader(ti: dict, ctx: ToolContext) -> dict:
    url = (ti.get("url") or "").strip()
    if not valid_url(url):
        return err("requires a valid http(s) 'url'")
    try:
        params = {"url": url}
        if ti.get("timestamp"):
            params["timestamp"] = ti["timestamp"]
        async with httpx.AsyncClient(timeout=12.0) as c:
            r = await c.get("https://archive.org/wayback/available", params=params)
        snap = r.json().get("archived_snapshots", {}).get("closest")
        if not snap:
            return ok(found=False, note="No archived snapshot found.")
        return ok(found=True, archived_url=snap.get("url"), timestamp=snap.get("timestamp"),
                  status=snap.get("status"))
    except Exception as e:  # noqa: BLE001
        return err(f"web_archive_reader failed: {e}", degraded=True)


# --- 17. html_to_markdown ----------------------------------------------------
@tool(
    "html_to_markdown",
    description="Convert an HTML string (or fetched URL) to clean Markdown. Input: {html?: str, url?: str}.",
    category="web",
    input_schema={"html": {"type": "string"}, "url": {"type": "string"}},
)
async def html_to_markdown(ti: dict, ctx: ToolContext) -> dict:
    html = ti.get("html")
    if not html and valid_url((ti.get("url") or "").strip()):
        try:
            r = await fetch(ti["url"].strip())
            html = r.text
        except Exception as e:  # noqa: BLE001
            return err(f"could not fetch url: {e}", degraded=True)
    if not html:
        return err("provide 'html' or a valid 'url'")
    try:
        from markdownify import markdownify as md

        return ok(markdown=md(html, strip=["script", "style"]).strip())
    except Exception as e:  # noqa: BLE001
        return err(f"html_to_markdown failed: {e}", degraded=True)


# --- 18. markdown_renderer ---------------------------------------------------
@tool(
    "markdown_renderer",
    description="Render Markdown to safe HTML. Input: {markdown: str}.",
    category="web",
    input_schema={"markdown": {"type": "string", "required": True}},
)
def markdown_renderer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "markdown")):
        return err(m)
    text = ti["markdown"]
    # Minimal, dependency-free markdown→HTML (headings, bold/italic, code, links, lists).
    import html as _html

    out_lines, in_list = [], False
    for line in text.split("\n"):
        esc = _html.escape(line)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
        esc = re.sub(r"\*(.+?)\*", r"<em>\1</em>", esc)
        esc = re.sub(r"`(.+?)`", r"<code>\1</code>", esc)
        esc = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', esc)
        h = re.match(r"^(#{1,6})\s+(.*)$", esc)
        if h:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            lvl = len(h.group(1))
            out_lines.append(f"<h{lvl}>{h.group(2)}</h{lvl}>")
        elif re.match(r"^\s*[-*]\s+", esc):
            if not in_list:
                out_lines.append("<ul>")
                in_list = True
            out_lines.append(f"<li>{re.sub(r'^\s*[-*]\s+', '', esc)}</li>")
        elif esc.strip():
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<p>{esc}</p>")
    if in_list:
        out_lines.append("</ul>")
    return ok(html="\n".join(out_lines))



# --- 19. arxiv_search --------------------------------------------------------
@tool(
    "arxiv_search",
    description="Search arXiv for academic papers (keyless). Returns titles, authors, summaries, and "
    "links. Input: {query: str, max_results?: int=5}.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "max_results": {"type": "integer"}},
)
async def arxiv_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, results=[])
    n = min(int(ti.get("max_results") or 5), 20)
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "OrionAgent/1.0"}) as c:
            r = await c.get("http://export.arxiv.org/api/query",
                            params={"search_query": f"all:{ti['query']}", "start": 0, "max_results": n})
        soup = _soup(r.text)
        entries = soup.find_all("entry")
        out = []
        for e in entries[:n]:
            authors = [a.get_text(strip=True) for a in e.find_all("name")]
            link = e.find("id")
            out.append({
                "title": (e.find("title").get_text(strip=True) if e.find("title") else None),
                "authors": authors,
                "summary": (e.find("summary").get_text(strip=True)[:500] if e.find("summary") else None),
                "published": (e.find("published").get_text(strip=True) if e.find("published") else None),
                "link": (link.get_text(strip=True) if link else None),
            })
        return ok(results=out, count=len(out))
    except Exception as e:  # noqa: BLE001
        return err(f"arxiv_search failed: {e}", degraded=True, results=[])


# --- 20. pubmed_search -------------------------------------------------------
@tool(
    "pubmed_search",
    description="Search PubMed for biomedical literature (keyless, NCBI E-utilities). Returns article "
    "titles + PubMed IDs. Input: {query: str, max_results?: int=5}.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "max_results": {"type": "integer"}},
)
async def pubmed_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, results=[])
    n = min(int(ti.get("max_results") or 5), 20)
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "OrionAgent/1.0"}) as c:
            s = await c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                            params={"db": "pubmed", "term": ti["query"], "retmax": n, "retmode": "json"})
            ids = s.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return ok(results=[], count=0)
            summ = await c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                               params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
            data = summ.json().get("result", {})
        out = [{"pmid": pid, "title": data.get(pid, {}).get("title"),
                "source": data.get(pid, {}).get("source"),
                "pubdate": data.get(pid, {}).get("pubdate"),
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"} for pid in ids]
        return ok(results=out, count=len(out))
    except Exception as e:  # noqa: BLE001
        return err(f"pubmed_search failed: {e}", degraded=True, results=[])
