"""Text Processing built-in tools (15).

Pure-python where possible. A few (summarizer, entity_extractor, content_rewriter)
use the LLM via app.llm.client when a task genuinely needs semantic work; they
degrade to a heuristic result if the LLM is unavailable so they never crash.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter

from app.tools.base import ToolContext, err, need, ok, tool

_WORD = re.compile(r"[A-Za-z0-9']+")
_SENT = re.compile(r"(?<=[.!?])\s+")
_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with", "is", "are",
    "was", "were", "be", "been", "it", "this", "that", "these", "those", "as", "at", "by",
    "from", "has", "have", "had", "not", "no", "yes", "we", "you", "they", "he", "she", "i",
}


async def _llm_complete(prompt: str, ctx: ToolContext) -> str | None:
    try:
        from app.llm.client import LLMClient

        client = LLMClient(user_keys=ctx.user_keys)
        res = await client.call([{"role": "user", "content": prompt}], tier="fast")
        return (res.text or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


# --- 21. text_summarizer -----------------------------------------------------
@tool(
    "text_summarizer",
    description="Summarize a block of text. Uses the LLM; falls back to extractive (top sentences) "
    "if the LLM is unavailable. Input: {text: str, sentences?: int}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "sentences": {"type": "integer"}},
)
async def text_summarizer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    text = ti["text"].strip()
    n = int(ti.get("sentences") or 3)
    llm = await _llm_complete(f"Summarize the following in {n} sentences:\n\n{text[:6000]}", ctx)
    if llm:
        return ok(summary=llm, method="llm")
    # Extractive fallback: rank sentences by keyword frequency.
    sents = _SENT.split(text)
    freq = Counter(w.lower() for w in _WORD.findall(text) if w.lower() not in _STOP)
    scored = sorted(sents, key=lambda s: sum(freq[w.lower()] for w in _WORD.findall(s)), reverse=True)
    return ok(summary=" ".join(scored[:n]), method="extractive")


# --- 22. text_chunker --------------------------------------------------------
@tool(
    "text_chunker",
    description="Split text into overlapping chunks for embedding/processing. "
    "Input: {text: str, size?: int=1000, overlap?: int=150}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "size": {"type": "integer"},
                  "overlap": {"type": "integer"}},
)
def text_chunker(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    text, size, overlap = ti["text"], int(ti.get("size") or 1000), int(ti.get("overlap") or 150)
    if size <= 0:
        return err("size must be > 0")
    overlap = max(0, min(overlap, size - 1))
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return ok(chunks=chunks, count=len(chunks))


# --- 23. text_extractor ------------------------------------------------------
@tool(
    "text_extractor",
    description="Extract structured items from text: emails, urls, phone numbers, hashtags, mentions, "
    "numbers. Input: {text: str, kinds?: [str]}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "kinds": {"type": "array"}},
)
def text_extractor(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    text = ti["text"]
    patterns = {
        "emails": r"[\w.+-]+@[\w-]+\.[\w.-]+",
        "urls": r"https?://[^\s)]+",
        "phones": r"\+?\d[\d\s().-]{7,}\d",
        "hashtags": r"#\w+",
        "mentions": r"@\w+",
        "numbers": r"-?\d+(?:\.\d+)?",
    }
    kinds = ti.get("kinds") or list(patterns)
    out = {k: re.findall(patterns[k], text) for k in kinds if k in patterns}
    return ok(**out)


# --- 24. keyword_extractor ---------------------------------------------------
@tool(
    "keyword_extractor",
    description="Extract the most salient keywords from text (frequency-based, stopwords removed). "
    "Input: {text: str, top?: int=10}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "top": {"type": "integer"}},
)
def keyword_extractor(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    top = int(ti.get("top") or 10)
    freq = Counter(w.lower() for w in _WORD.findall(ti["text"]) if w.lower() not in _STOP and len(w) > 2)
    return ok(keywords=[{"term": t, "count": c} for t, c in freq.most_common(top)])


# --- 25. regex_tool ----------------------------------------------------------
@tool(
    "regex_tool",
    description="Run a regex over text: findall / match / sub. Input: "
    "{text: str, pattern: str, mode?: findall|search|sub, replacement?: str, flags?: [i,m,s]}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "pattern": {"type": "string", "required": True},
                  "mode": {"type": "string"}, "replacement": {"type": "string"}},
)
def regex_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text", "pattern")):
        return err(m)
    flag_val = 0
    for f in ti.get("flags") or []:
        flag_val |= {"i": re.I, "m": re.M, "s": re.S}.get(str(f).lower(), 0)
    try:
        pat = re.compile(ti["pattern"], flag_val)
    except re.error as e:
        return err(f"invalid regex: {e}")
    mode = (ti.get("mode") or "findall").lower()
    if mode == "findall":
        return ok(matches=pat.findall(ti["text"]))
    if mode == "search":
        m = pat.search(ti["text"])
        return ok(matched=bool(m), match=(m.group(0) if m else None), groups=(list(m.groups()) if m else []))
    if mode == "sub":
        return ok(result=pat.sub(ti.get("replacement", ""), ti["text"]))
    return err(f"unknown mode: {mode}")


# --- 26. text_diff -----------------------------------------------------------
@tool(
    "text_diff",
    description="Produce a unified diff between two texts. Input: {a: str, b: str}.",
    category="text",
    input_schema={"a": {"type": "string", "required": True}, "b": {"type": "string", "required": True}},
)
def text_diff(ti: dict, ctx: ToolContext) -> dict:
    a, b = ti.get("a"), ti.get("b")
    if a is None or b is None:
        return err("requires 'a' and 'b'")
    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=2))
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ok(diff="\n".join(diff), similarity=round(ratio, 4), changed=a != b)


# --- 27. text_deduplicator ---------------------------------------------------
@tool(
    "text_deduplicator",
    description="Remove duplicate lines or list items, preserving order. Input: "
    "{text?: str, items?: [str], case_insensitive?: bool}.",
    category="text",
    input_schema={"text": {"type": "string"}, "items": {"type": "array"}},
)
def text_deduplicator(ti: dict, ctx: ToolContext) -> dict:
    items = ti.get("items")
    if items is None:
        if not ti.get("text"):
            return err("provide 'text' or 'items'")
        items = ti["text"].split("\n")
    ci = bool(ti.get("case_insensitive"))
    seen, out = set(), []
    for it in items:
        key = it.lower() if ci and isinstance(it, str) else it
        if key not in seen:
            seen.add(key)
            out.append(it)
    return ok(result=out, removed=len(items) - len(out), count=len(out))


# --- 28. string_similarity ---------------------------------------------------
@tool(
    "string_similarity",
    description="Compute similarity between two strings (0..1). Uses rapidfuzz if available, else "
    "difflib. Input: {a: str, b: str}.",
    category="text",
    input_schema={"a": {"type": "string", "required": True}, "b": {"type": "string", "required": True}},
)
def string_similarity(ti: dict, ctx: ToolContext) -> dict:
    a, b = ti.get("a"), ti.get("b")
    if a is None or b is None:
        return err("requires 'a' and 'b'")
    try:
        from rapidfuzz import fuzz

        return ok(score=round(fuzz.ratio(a, b) / 100.0, 4), method="rapidfuzz")
    except Exception:  # noqa: BLE001
        return ok(score=round(difflib.SequenceMatcher(None, a, b).ratio(), 4), method="difflib")


# --- 29. fuzzy_matcher -------------------------------------------------------
@tool(
    "fuzzy_matcher",
    description="Find the best fuzzy matches for a query within a list of candidates. Input: "
    "{query: str, candidates: [str], top?: int=5}.",
    category="text",
    input_schema={"query": {"type": "string", "required": True}, "candidates": {"type": "array", "required": True}},
)
def fuzzy_matcher(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m)
    cands = ti.get("candidates")
    if not isinstance(cands, list) or not cands:
        return err("'candidates' must be a non-empty array")
    top = int(ti.get("top") or 5)
    try:
        from rapidfuzz import fuzz, process

        matches = process.extract(ti["query"], cands, scorer=fuzz.WRatio, limit=top)
        return ok(matches=[{"value": v, "score": round(s / 100.0, 4)} for v, s, _ in matches], method="rapidfuzz")
    except Exception:  # noqa: BLE001
        scored = sorted(cands, key=lambda c: difflib.SequenceMatcher(None, ti["query"], c).ratio(), reverse=True)
        return ok(matches=[{"value": c, "score": round(difflib.SequenceMatcher(None, ti["query"], c).ratio(), 4)}
                           for c in scored[:top]], method="difflib")


# --- 30. text_normalizer -----------------------------------------------------
@tool(
    "text_normalizer",
    description="Normalize text: collapse whitespace, optional lowercase, strip accents, remove "
    "punctuation. Input: {text: str, lowercase?: bool, strip_accents?: bool, strip_punct?: bool}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}},
)
def text_normalizer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    import unicodedata

    s = ti["text"]
    if ti.get("strip_accents"):
        s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    if ti.get("strip_punct"):
        s = re.sub(r"[^\w\s]", "", s)
    if ti.get("lowercase"):
        s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return ok(result=s)


# --- 31. language_detector ---------------------------------------------------
@tool(
    "language_detector",
    description="Heuristically detect the language of text (common languages, stopword-based). "
    "Input: {text: str}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}},
)
def language_detector(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    markers = {
        "en": {"the", "and", "is", "of", "to", "in"},
        "es": {"el", "la", "de", "que", "y", "en"},
        "fr": {"le", "la", "les", "de", "et", "un"},
        "de": {"der", "die", "das", "und", "ist", "nicht"},
        "it": {"il", "di", "che", "la", "e", "un"},
        "pt": {"o", "de", "que", "e", "do", "da"},
    }
    words = set(w.lower() for w in _WORD.findall(ti["text"]))
    scores = {lang: len(words & mk) for lang, mk in markers.items()}
    best = max(scores, key=scores.get)
    return ok(language=best if scores[best] else "unknown", scores=scores)


# --- 32. readability_analyzer ------------------------------------------------
@tool(
    "readability_analyzer",
    description="Compute readability metrics (Flesch reading ease, avg sentence/word length, counts). "
    "Input: {text: str}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}},
)
def readability_analyzer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    text = ti["text"]
    words = _WORD.findall(text)
    sents = [s for s in _SENT.split(text) if s.strip()] or [text]

    def syllables(w: str) -> int:
        w = w.lower()
        groups = re.findall(r"[aeiouy]+", w)
        return max(1, len(groups))

    nw, ns = max(1, len(words)), max(1, len(sents))
    syl = sum(syllables(w) for w in words)
    flesch = 206.835 - 1.015 * (nw / ns) - 84.6 * (syl / nw)
    return ok(words=len(words), sentences=len(sents), characters=len(text),
              avg_sentence_length=round(nw / ns, 2), avg_word_length=round(sum(len(w) for w in words) / nw, 2),
              flesch_reading_ease=round(flesch, 1))


# --- 33. citation_builder ----------------------------------------------------
@tool(
    "citation_builder",
    description="Build a formatted citation from fields. Input: "
    "{style?: apa|mla, title: str, author?: str, year?: str, url?: str, publisher?: str}.",
    category="text",
    input_schema={"title": {"type": "string", "required": True}, "style": {"type": "string"}},
)
def citation_builder(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "title")):
        return err(m)
    style = (ti.get("style") or "apa").lower()
    author, year, title = ti.get("author", ""), ti.get("year", "n.d."), ti["title"]
    pub, url = ti.get("publisher", ""), ti.get("url", "")
    if style == "mla":
        cite = f'{author}. "{title}." {pub}, {year}. {url}'.strip()
    else:  # apa
        cite = f"{author} ({year}). {title}. {pub}. {url}".strip()
    return ok(citation=re.sub(r"\s+", " ", cite).strip(" ."), style=style)


# --- 34. content_rewriter ----------------------------------------------------
@tool(
    "content_rewriter",
    description="Rewrite text in a requested tone/style (uses the LLM). Input: "
    "{text: str, style?: str (e.g. 'formal','concise','friendly')}. Falls back to returning the "
    "original if the LLM is unavailable.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}, "style": {"type": "string"}},
)
async def content_rewriter(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    style = ti.get("style") or "clear and professional"
    out = await _llm_complete(f"Rewrite the following text to be {style}. Return only the rewritten text.\n\n{ti['text'][:6000]}", ctx)
    if out:
        return ok(result=out, style=style, method="llm")
    return ok(result=ti["text"], style=style, method="passthrough", degraded=True)


# --- 35. entity_extractor ----------------------------------------------------
@tool(
    "entity_extractor",
    description="Extract named entities (people, orgs, places, dates) from text. Uses the LLM for "
    "semantic extraction; falls back to capitalized-phrase heuristics. Input: {text: str}.",
    category="text",
    input_schema={"text": {"type": "string", "required": True}},
)
async def entity_extractor(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    prompt = ('Extract named entities from the text. Return ONLY JSON like '
              '{"people":[],"organizations":[],"locations":[],"dates":[]}.\n\n' + ti["text"][:5000])
    out = await _llm_complete(prompt, ctx)
    if out:
        import json

        from app.llm.repair import extract_json

        try:
            data = extract_json(out)
            if isinstance(data, dict):
                return ok(entities=data, method="llm")
        except Exception:  # noqa: BLE001
            pass
    # Heuristic fallback: capitalized multi-word phrases.
    caps = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", ti["text"])
    return ok(entities={"candidates": sorted(set(caps))}, method="heuristic", degraded=True)
