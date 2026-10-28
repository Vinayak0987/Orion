"""Typed artifact normalization — turns a tool's raw output into a list of
typed, renderable artifacts so the frontend can show the RIGHT widget (image,
video, html iframe, file download, data table, or plain text).

normalize_artifacts(tool_name, tool_output) -> list[dict] where each dict has:
  type:     one of text|image|video|html|file|data
  url?:     a servable URL / path for image|video|file
  content?: inline content for text|html|data
  mime?:    best-effort MIME type
  filename?:a filename when the artifact is a file/download
  title?:   a short human label

It is deliberately permissive: it never raises, and anything it can't classify
becomes a `text` artifact so nothing is silently dropped.
"""

from __future__ import annotations

import json
import re

# --- extension / mime tables -------------------------------------------------
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")
_VIDEO_EXT = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")
_FILE_EXT = (".pdf", ".csv", ".docx", ".doc", ".xlsx", ".xls", ".zip", ".pptx",
             ".txt", ".json", ".tsv", ".md", ".rtf", ".odt")

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
    ".avi": "video/x-msvideo", ".mkv": "video/x-matroska", ".m4v": "video/x-m4v",
    ".pdf": "application/pdf", ".csv": "text/csv", ".tsv": "text/tab-separated-values",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".zip": "application/zip", ".txt": "text/plain", ".json": "application/json",
    ".md": "text/markdown",
}

_URL_RE = re.compile(r"https?://[^\s\"'<>)]+", re.IGNORECASE)


def _ext_of(s: str) -> str:
    """Lowercased file extension of a url/path (ignoring any ?query)."""
    s = (s or "").split("?")[0].split("#")[0].strip().lower()
    m = re.search(r"(\.[a-z0-9]+)$", s)
    return m.group(1) if m else ""


def _mime_for(ext: str) -> str | None:
    return _MIME.get(ext)


def _filename_of(url: str) -> str | None:
    tail = (url or "").split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    return tail or None


def _classify_url(url: str, title: str | None = None) -> dict | None:
    """Type a single url/path by its extension. Returns an artifact dict or None."""
    ext = _ext_of(url)
    if ext in _IMAGE_EXT:
        return {"type": "image", "url": url, "mime": _mime_for(ext),
                "filename": _filename_of(url), "title": title}
    if ext in _VIDEO_EXT:
        return {"type": "video", "url": url, "mime": _mime_for(ext),
                "filename": _filename_of(url), "title": title}
    if ext in _FILE_EXT:
        return {"type": "file", "url": url, "mime": _mime_for(ext),
                "filename": _filename_of(url), "title": title}
    return None


def _looks_like_html(s: str) -> bool:
    low = (s or "").strip().lower()
    if not low:
        return False
    return (low.startswith("<html") or low.startswith("<!doctype")
            or "<div" in low or "<body" in low or "<section" in low
            or "<table" in low or "<svg" in low)


def _clean(d: dict) -> dict:
    """Drop None values so artifacts stay compact."""
    return {k: v for k, v in d.items() if v is not None}


def normalize_artifacts(tool_name: str, tool_output) -> list[dict]:
    """Normalize ANY tool output into a list of typed artifacts.

    Detection order (first match wins per field):
      1. matplotlib / code_interpreter charts  -> tool_output["images"] => image
      2. explicit media fields (image_url, video_url, url, audio_url ...)
      3. urls found anywhere in a string field, typed by extension
      4. HTML strings (<html|<!doctype|<div ...)                         => html
      5. file paths/urls (.pdf/.csv/.docx/.zip ...)                      => file
      6. tabular / structured JSON (dict/list)                           => data
      7. anything else                                                   => text
    Never raises; unknown shapes degrade to a single text artifact.
    """
    artifacts: list[dict] = []
    try:
        return _normalize(tool_name, tool_output, artifacts)
    except Exception:  # noqa: BLE001 — normalization must never break a task
        if not artifacts:
            artifacts.append({"type": "text", "content": _to_text(tool_output)})
        return artifacts


def _normalize(tool_name: str, tool_output, artifacts: list[dict]) -> list[dict]:
    # --- str output -----------------------------------------------------------
    if isinstance(tool_output, str):
        s = tool_output.strip()
        if _looks_like_html(s):
            artifacts.append(_clean({"type": "html", "content": s, "mime": "text/html"}))
            return artifacts
        # A bare url string?
        if s and _URL_RE.fullmatch(s):
            a = _classify_url(s)
            if a:
                artifacts.append(_clean(a))
                return artifacts
        artifacts.append({"type": "text", "content": s})
        return artifacts

    # --- list output ----------------------------------------------------------
    if isinstance(tool_output, list):
        # A list of urls/paths?
        media = [x for x in tool_output if isinstance(x, str) and _classify_url(x)]
        if media and len(media) == len([x for x in tool_output if isinstance(x, str)]) and media:
            for u in media:
                artifacts.append(_clean(_classify_url(u)))
            return artifacts
        # Otherwise treat as tabular/structured data.
        artifacts.append({"type": "data", "content": tool_output})
        return artifacts

    # --- dict output ----------------------------------------------------------
    if isinstance(tool_output, dict):
        out = tool_output

        # 1) matplotlib / code_interpreter charts: {"images": [...]} => image(s).
        imgs = out.get("images")
        if isinstance(imgs, list) and imgs:
            for im in imgs:
                if isinstance(im, str):
                    ext = _ext_of(im)
                    artifacts.append(_clean({
                        "type": "image", "url": im,
                        "mime": _mime_for(ext) or "image/png",
                        "filename": _filename_of(im),
                        "title": "chart",
                    }))
                elif isinstance(im, dict):
                    u = im.get("url") or im.get("path") or im.get("src")
                    if u:
                        ext = _ext_of(u)
                        artifacts.append(_clean({
                            "type": "image", "url": u,
                            "mime": im.get("mime") or _mime_for(ext) or "image/png",
                            "filename": im.get("filename") or _filename_of(u),
                            "title": im.get("title") or "chart",
                        }))

        # 2) explicit media URL fields.
        _MEDIA_FIELDS = [
            ("video_url", "video"), ("video", "video"),
            ("image_url", "image"), ("image", "image"),
            ("audio_url", "video"),  # audio renders in a media player like video
            ("url", None), ("file_url", None), ("download_url", None),
            ("output_url", None), ("result_url", None), ("src", None),
        ]
        for field, forced in _MEDIA_FIELDS:
            val = out.get(field)
            if isinstance(val, str) and val.strip():
                ext = _ext_of(val)
                if forced == "video":
                    artifacts.append(_clean({"type": "video", "url": val,
                                             "mime": _mime_for(ext) or "video/mp4",
                                             "filename": _filename_of(val)}))
                elif forced == "image":
                    artifacts.append(_clean({"type": "image", "url": val,
                                             "mime": _mime_for(ext) or "image/png",
                                             "filename": _filename_of(val)}))
                else:
                    a = _classify_url(val)
                    if a:
                        artifacts.append(_clean(a))

        # 3) HTML content fields.
        for field in ("html", "content", "body", "output", "result", "text", "answer"):
            val = out.get(field)
            if isinstance(val, str) and _looks_like_html(val):
                artifacts.append(_clean({"type": "html", "content": val, "mime": "text/html"}))
                break

        # 4) file path fields.
        for field in ("path", "file", "filename", "filepath", "saved_to"):
            val = out.get(field)
            if isinstance(val, str) and val.strip():
                a = _classify_url(val)
                if a:
                    artifacts.append(_clean(a))

        if artifacts:
            return artifacts

        # 5) tabular/structured data: rows / data / table / records / items.
        for field in ("rows", "data", "table", "records", "items", "results"):
            val = out.get(field)
            if isinstance(val, (list, dict)) and val:
                artifacts.append({"type": "data", "content": val})
                return artifacts

        # 6) a plain textual answer in a known field.
        for field in ("text", "answer", "summary", "output", "message", "content"):
            val = out.get(field)
            if isinstance(val, str) and val.strip():
                artifacts.append({"type": "text", "content": val})
                return artifacts

        # 7) fall back: the whole dict is structured data.
        artifacts.append({"type": "data", "content": out})
        return artifacts

    # --- anything else --------------------------------------------------------
    artifacts.append({"type": "text", "content": _to_text(tool_output)})
    return artifacts


def _to_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, default=str)[:8000]
    except Exception:  # noqa: BLE001
        return str(v)[:8000]
