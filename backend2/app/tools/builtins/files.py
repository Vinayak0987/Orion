"""Files & Documents built-in tools (16).

Every path is resolved INSIDE the workspace sandbox via sandbox.safe_path — an
agent cannot touch the real filesystem outside it. PDF/DOCX reading reuse the
already-installed pypdf / python-docx.
"""

from __future__ import annotations

import difflib
import hashlib
import shutil
from pathlib import Path

from app.tools.base import ToolContext, err, need, ok, tool
from app.tools.sandbox import SandboxError, rel_to_workspace, safe_path


def _guard(fn):
    """Wrap a tool body so SandboxError becomes a clean {error} dict."""
    def inner(ti, ctx):
        try:
            return fn(ti, ctx)
        except SandboxError as e:
            return err(f"sandbox: {e}")
        except Exception as e:  # noqa: BLE001
            return err(f"{fn.__name__}: {e}", degraded=True)
    inner.__name__ = fn.__name__
    return inner


# --- 66. file_reader ---------------------------------------------------------
@tool(
    "file_reader",
    description="Read a UTF-8 text file from the workspace. Input: {path: str, max_chars?: int}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "max_chars": {"type": "integer"}},
)
@_guard
def file_reader(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"], must_exist=True)
    data = p.read_text("utf-8", errors="replace")
    mx = int(ti.get("max_chars") or 20000)
    return ok(path=rel_to_workspace(p), content=data[:mx], truncated=len(data) > mx, length=len(data))


# --- 67. file_writer ---------------------------------------------------------
@tool(
    "file_writer",
    description="Write text to a file in the workspace (creates parent dirs). Input: "
    "{path: str, content: str, append?: bool}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "content": {"type": "string", "required": True}},
)
@_guard
def file_writer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"])
    p.parent.mkdir(parents=True, exist_ok=True)
    content = ti.get("content", "")
    with p.open("a" if ti.get("append") else "w", encoding="utf-8") as f:
        f.write(content)
    return ok(path=rel_to_workspace(p), bytes_written=len(content.encode("utf-8")))


# --- 68. file_search ---------------------------------------------------------
@tool(
    "file_search",
    description="Search workspace files by glob and/or text content. Input: "
    "{glob?: str='**/*', contains?: str, max?: int=50}.",
    category="files",
    input_schema={"glob": {"type": "string"}, "contains": {"type": "string"}},
)
@_guard
def file_search(ti: dict, ctx: ToolContext) -> dict:
    root = safe_path(".")
    pattern = ti.get("glob") or "**/*"
    needle, mx = ti.get("contains"), int(ti.get("max") or 50)
    hits = []
    for p in root.glob(pattern):
        if not p.is_file():
            continue
        if needle:
            try:
                if needle.lower() not in p.read_text("utf-8", errors="ignore").lower():
                    continue
            except Exception:  # noqa: BLE001
                continue
        hits.append(rel_to_workspace(p))
        if len(hits) >= mx:
            break
    return ok(files=hits, count=len(hits))


# --- 69. directory_manager ---------------------------------------------------
@tool(
    "directory_manager",
    description="List/create/remove directories in the workspace. Input: "
    "{action: list|mkdir|rmdir, path?: str}.",
    category="files",
    input_schema={"action": {"type": "string", "required": True}, "path": {"type": "string"}},
)
@_guard
def directory_manager(ti: dict, ctx: ToolContext) -> dict:
    action = (ti.get("action") or "list").lower()
    p = safe_path(ti.get("path") or ".")
    if action == "list":
        if not p.exists():
            return err("directory not found")
        entries = [{"name": c.name, "type": "dir" if c.is_dir() else "file",
                    "size": (c.stat().st_size if c.is_file() else None)} for c in sorted(p.iterdir())]
        return ok(path=rel_to_workspace(p), entries=entries, count=len(entries))
    if action == "mkdir":
        p.mkdir(parents=True, exist_ok=True)
        return ok(path=rel_to_workspace(p), created=True)
    if action == "rmdir":
        if p.exists():
            shutil.rmtree(p)
        return ok(path=rel_to_workspace(p), removed=True)
    return err(f"unknown action: {action}")


# --- 70. file_metadata -------------------------------------------------------
@tool(
    "file_metadata",
    description="Return size, timestamps, and type for a workspace path. Input: {path: str}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}},
)
@_guard
def file_metadata(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"], must_exist=True)
    import datetime as dt

    st = p.stat()
    return ok(path=rel_to_workspace(p), is_dir=p.is_dir(), size_bytes=st.st_size,
              modified=dt.datetime.fromtimestamp(st.st_mtime, dt.UTC).isoformat(),
              suffix=p.suffix)


# --- 71. file_copy -----------------------------------------------------------
@tool(
    "file_copy",
    description="Copy a file within the workspace. Input: {src: str, dst: str}.",
    category="files",
    input_schema={"src": {"type": "string", "required": True}, "dst": {"type": "string", "required": True}},
)
@_guard
def file_copy(ti: dict, ctx: ToolContext) -> dict:
    s = safe_path(ti.get("src", ""), must_exist=True)
    d = safe_path(ti.get("dst", ""))
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    return ok(src=rel_to_workspace(s), dst=rel_to_workspace(d), copied=True)


# --- 72. file_move -----------------------------------------------------------
@tool(
    "file_move",
    description="Move/rename a file within the workspace. Input: {src: str, dst: str}.",
    category="files",
    input_schema={"src": {"type": "string", "required": True}, "dst": {"type": "string", "required": True}},
)
@_guard
def file_move(ti: dict, ctx: ToolContext) -> dict:
    s = safe_path(ti.get("src", ""), must_exist=True)
    d = safe_path(ti.get("dst", ""))
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return ok(src=rel_to_workspace(s), dst=rel_to_workspace(d), moved=True)


# --- 73. file_delete ---------------------------------------------------------
@tool(
    "file_delete",
    description="Delete a file in the workspace. Input: {path: str}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}},
)
@_guard
def file_delete(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"])
    existed = p.exists()
    if existed and p.is_file():
        p.unlink()
    return ok(path=rel_to_workspace(p), deleted=existed)


# --- 74. file_hash -----------------------------------------------------------
@tool(
    "file_hash",
    description="Compute a hash of a workspace file. Input: {path: str, algo?: md5|sha1|sha256}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "algo": {"type": "string"}},
)
@_guard
def file_hash(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"], must_exist=True)
    algo = (ti.get("algo") or "sha256").lower()
    if algo not in {"md5", "sha1", "sha256"}:
        return err(f"unsupported algo: {algo}")
    h = hashlib.new(algo)
    h.update(p.read_bytes())
    return ok(path=rel_to_workspace(p), algo=algo, hash=h.hexdigest())


# --- 75. file_diff -----------------------------------------------------------
@tool(
    "file_diff",
    description="Unified diff between two workspace files. Input: {a: str, b: str}.",
    category="files",
    input_schema={"a": {"type": "string", "required": True}, "b": {"type": "string", "required": True}},
)
@_guard
def file_diff(ti: dict, ctx: ToolContext) -> dict:
    a = safe_path(ti.get("a", ""), must_exist=True)
    b = safe_path(ti.get("b", ""), must_exist=True)
    da = a.read_text("utf-8", errors="replace").splitlines()
    db = b.read_text("utf-8", errors="replace").splitlines()
    diff = list(difflib.unified_diff(da, db, fromfile=a.name, tofile=b.name, lineterm="", n=2))
    return ok(diff="\n".join(diff), changed=da != db)


# --- 76. archive_manager -----------------------------------------------------
@tool(
    "archive_manager",
    description="Create or extract a .zip archive within the workspace. Input: "
    "{action: zip|unzip|list, path: str, source?: str, dest?: str}.",
    category="files",
    input_schema={"action": {"type": "string", "required": True}, "path": {"type": "string", "required": True}},
)
@_guard
def archive_manager(ti: dict, ctx: ToolContext) -> dict:
    import zipfile

    action = (ti.get("action") or "list").lower()
    archive = safe_path(ti.get("path", ""))
    if action == "zip":
        src = safe_path(ti.get("source", ""), must_exist=True)
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            if src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(src))
            else:
                z.write(src, src.name)
        return ok(path=rel_to_workspace(archive), created=True)
    if action == "list":
        with zipfile.ZipFile(safe_path(ti.get("path", ""), must_exist=True)) as z:
            return ok(entries=z.namelist())
    if action == "unzip":
        dest = safe_path(ti.get("dest") or ".")
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(safe_path(ti.get("path", ""), must_exist=True)) as z:
            # Guard each member against path traversal.
            for member in z.namelist():
                target = safe_path(str(Path(rel_to_workspace(dest)) / member))  # re-validate
            z.extractall(dest)
        return ok(dest=rel_to_workspace(dest), extracted=True)
    return err(f"unknown action: {action}")


# --- 77. pdf_reader ----------------------------------------------------------
@tool(
    "pdf_reader",
    description="Extract text from a PDF in the workspace. Input: {path: str, pages?: [int]}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "pages": {"type": "array"}},
)
@_guard
def pdf_reader(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    from pypdf import PdfReader

    p = safe_path(ti["path"], must_exist=True)
    reader = PdfReader(str(p))
    want = ti.get("pages")
    texts = []
    for i, page in enumerate(reader.pages):
        if want and i not in want:
            continue
        texts.append(page.extract_text() or "")
    return ok(path=rel_to_workspace(p), pages=len(reader.pages), text="\n".join(texts))


# --- 78. pdf_splitter --------------------------------------------------------
@tool(
    "pdf_splitter",
    description="Split selected pages of a PDF into a new PDF in the workspace. Input: "
    "{path: str, pages: [int], out: str}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "pages": {"type": "array", "required": True},
                  "out": {"type": "string", "required": True}},
)
@_guard
def pdf_splitter(ti: dict, ctx: ToolContext) -> dict:
    from pypdf import PdfReader, PdfWriter

    p = safe_path(ti.get("path", ""), must_exist=True)
    pages = ti.get("pages")
    if not isinstance(pages, list) or not pages:
        return err("'pages' must be a non-empty array of page indices")
    out = safe_path(ti.get("out", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    reader, writer = PdfReader(str(p)), PdfWriter()
    for i in pages:
        if 0 <= i < len(reader.pages):
            writer.add_page(reader.pages[i])
    with out.open("wb") as f:
        writer.write(f)
    return ok(out=rel_to_workspace(out), pages=len(writer.pages))


# --- 79. pdf_merger ----------------------------------------------------------
@tool(
    "pdf_merger",
    description="Merge multiple workspace PDFs into one. Input: {paths: [str], out: str}.",
    category="files",
    input_schema={"paths": {"type": "array", "required": True}, "out": {"type": "string", "required": True}},
)
@_guard
def pdf_merger(ti: dict, ctx: ToolContext) -> dict:
    from pypdf import PdfWriter

    paths = ti.get("paths")
    if not isinstance(paths, list) or not paths:
        return err("'paths' must be a non-empty array")
    out = safe_path(ti.get("out", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for rp in paths:
        writer.append(str(safe_path(rp, must_exist=True)))
    with out.open("wb") as f:
        writer.write(f)
    return ok(out=rel_to_workspace(out), merged=len(paths))


# --- 80. document_reader -----------------------------------------------------
@tool(
    "document_reader",
    description="Extract text from a workspace document (txt/md/csv/pdf/docx) — auto-detects by "
    "extension. Input: {path: str}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}},
)
@_guard
def document_reader(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "path")):
        return err(m)
    p = safe_path(ti["path"], must_exist=True)
    ext = p.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json", ".log"}:
        return ok(path=rel_to_workspace(p), type=ext, text=p.read_text("utf-8", errors="replace"))
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(p))
        return ok(path=rel_to_workspace(p), type="pdf", pages=len(reader.pages),
                  text="\n".join(pg.extract_text() or "" for pg in reader.pages))
    if ext == ".docx":
        import docx

        d = docx.Document(str(p))
        return ok(path=rel_to_workspace(p), type="docx", text="\n".join(par.text for par in d.paragraphs))
    return err(f"unsupported document type: {ext}")


# --- 81. document_chunker ----------------------------------------------------
@tool(
    "document_chunker",
    description="Read a workspace document and split it into overlapping chunks ready for embedding. "
    "Input: {path: str, size?: int=1000, overlap?: int=150}.",
    category="files",
    input_schema={"path": {"type": "string", "required": True}, "size": {"type": "integer"},
                  "overlap": {"type": "integer"}},
)
@_guard
def document_chunker(ti: dict, ctx: ToolContext) -> dict:
    res = document_reader({"path": ti.get("path")}, ctx)
    if "error" in res:
        return res
    text = res.get("text", "")
    size, overlap = int(ti.get("size") or 1000), int(ti.get("overlap") or 150)
    overlap = max(0, min(overlap, size - 1))
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return ok(path=res.get("path"), chunks=chunks, count=len(chunks))
