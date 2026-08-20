"""Departmental memory — one isolated store per department, four typed.

Why isolated rather than shared
-------------------------------
A single shared context fails three ways at once. Retrieval becomes noisy as
unrelated departments' histories compete for relevance; volume eventually exceeds
what any context can hold; and because everything is attributed to everyone, no
department's learning can be measured separately.

The isolation is an **enforced invariant**, not a convention: `retrieve` filters
by `(company_id, department)` in the query itself, and a test asserts that no
call can surface another department's entries. `retrieve_shared` exists only as
the control arm for the comparison the research proposal sets out — it is not used
by the operating layer.

Four types, because they answer different questions
--------------------------------------------------
    episodic     what happened, and when
    semantic     what we know to be true
    procedural   how we do this
    reflective   what we should do differently

Keeping them separate is what allows a planner to ask for method without being
handed anecdotes, and what lets consolidation promote repeated episodes into a
single durable conclusion.

Retrieval
---------
Lexical and deterministic: token overlap, weighted by recency and by how often an
entry has proved useful. No embedding model.

That is a deliberate constraint rather than a shortcut. ChromaDB's default
embedding function downloads a model on first use, which would break the offline
test guarantee and make retrieval results vary with whatever model version was
fetched. A deterministic scorer keeps the ablation reproducible. Semantic
retrieval can be layered on later behind the same interface; the invariant that
matters — scoping — is independent of how relevance is scored.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Iterable
from uuid import uuid4

from app.db.sqlite import connection

# --------------------------------------------------------------------- schema --

MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id                TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL,
    department        TEXT NOT NULL,
    memory_type       TEXT NOT NULL,
    content           TEXT NOT NULL,
    tokens            TEXT NOT NULL DEFAULT '',
    confidence        REAL NOT NULL DEFAULT 0.5,
    occurrences       INTEGER NOT NULL DEFAULT 1,
    retrieval_count   INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    last_retrieved_at TEXT,
    superseded_by     TEXT,
    meta_json         TEXT
);

CREATE INDEX IF NOT EXISTS idx_memories_scope
    ON memories(company_id, department, memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_live
    ON memories(company_id, department, superseded_by);
"""


def init_memory() -> None:
    """Idempotent."""
    with connection() as conn:
        conn.executescript(MEMORY_SCHEMA)


# ---------------------------------------------------------------------- types --


class MemoryType(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    REFLECTIVE = "reflective"


ALL_TYPES: tuple[MemoryType, ...] = tuple(MemoryType)

#: Repeated episodes are promoted into a semantic conclusion at this count. A
#: department that ran the same campaign eleven times should carry one conclusion,
#: not eleven anecdotes competing for retrieval.
CONSOLIDATION_THRESHOLD = 3

#: Entries never retrieved within this window are eligible for decay.
DECAY_AFTER_DAYS = 180

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    to was were will with we our this these those they their""".split()
)


def tokenise(text: str) -> list[str]:
    """Lowercase content words. Deterministic, no external resources.

    Numeric tokens are kept regardless of length. A business memory that
    discarded "15", "2026" or "q3" would lose the part of a sentence that
    distinguishes one budget, quarter or campaign from another — and would then
    consolidate genuinely different episodes into one.
    """
    out: list[str] = []
    for token in _TOKEN.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        if token.isdigit() or any(ch.isdigit() for ch in token):
            out.append(token)
        elif len(token) > 2:
            out.append(token)
    return out


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class Memory:
    """One entry. Immutable; a correction is a new entry that supersedes it."""

    company_id: str
    department: str
    memory_type: MemoryType
    content: str
    confidence: float = 0.5
    meta: dict[str, Any] | None = None
    id: str = ""
    occurrences: int = 1
    retrieval_count: int = 0
    created_at: str = ""
    last_retrieved_at: str | None = None
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("a memory must have content")
        if not self.department.strip() or not self.company_id.strip():
            raise ValueError("a memory must be scoped to a company and department")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class MemoryScopeViolation(RuntimeError):
    """An attempt to read across the department boundary."""


# ----------------------------------------------------------------------- write --


def write(memory: Memory) -> str:
    """Store one entry, consolidating a near-duplicate rather than duplicating it.

    Consolidation is what keeps retrieval precision from decaying as the corpus
    grows: the eleventh recording of the same episode increments an existing
    entry instead of adding an eleventh competitor for the same query.
    """
    tokens = tokenise(memory.content)
    existing = _find_duplicate(memory, tokens)

    if existing is not None:
        with connection() as conn:
            conn.execute(
                "UPDATE memories SET occurrences = occurrences + 1, "
                "confidence = MIN(1.0, confidence + 0.1) WHERE id = ?",
                (existing["id"],),
            )
        _maybe_consolidate(memory, existing["id"])
        return str(existing["id"])

    memory_id = memory.id or str(uuid4())
    with connection() as conn:
        conn.execute(
            "INSERT INTO memories (id, company_id, department, memory_type, "
            "content, tokens, confidence, occurrences, retrieval_count, "
            "created_at, meta_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                memory_id, memory.company_id, memory.department,
                str(memory.memory_type), memory.content, " ".join(tokens),
                memory.confidence, memory.occurrences, memory.retrieval_count,
                memory.created_at or _now(),
                json.dumps(memory.meta, default=str) if memory.meta else None,
            ),
        )
    return memory_id


def _find_duplicate(memory: Memory, tokens: list[str]) -> dict | None:
    """An entry of the same type in the same store saying substantially the same thing."""
    if not tokens:
        return None
    candidates = _rows(memory.company_id, [memory.department],
                       [memory.memory_type])
    wanted = set(tokens)
    for row in candidates:
        other = set((row["tokens"] or "").split())
        if not other:
            continue
        overlap = len(wanted & other) / max(len(wanted | other), 1)
        if overlap >= 0.8:
            return row
    return None


def _maybe_consolidate(memory: Memory, episodic_id: str) -> None:
    """Promote a repeated episode into a semantic conclusion."""
    if memory.memory_type is not MemoryType.EPISODIC:
        return
    with connection() as conn:
        row = conn.execute(
            "SELECT occurrences, content FROM memories WHERE id = ?",
            (episodic_id,),
        ).fetchone()
    if row is None or row["occurrences"] < CONSOLIDATION_THRESHOLD:
        return

    conclusion = (
        f"Observed {row['occurrences']} times: {row['content']}"
    )
    already = _find_duplicate(
        Memory(company_id=memory.company_id, department=memory.department,
               memory_type=MemoryType.SEMANTIC, content=conclusion),
        tokenise(conclusion),
    )
    if already is not None:
        return
    with connection() as conn:
        conn.execute(
            "INSERT INTO memories (id, company_id, department, memory_type, "
            "content, tokens, confidence, occurrences, created_at, meta_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()), memory.company_id, memory.department,
                str(MemoryType.SEMANTIC), conclusion,
                " ".join(tokenise(conclusion)), 0.8, row["occurrences"], _now(),
                json.dumps({"consolidated_from": episodic_id}),
            ),
        )


# ------------------------------------------------------------------- retrieval --


def _rows(company_id: str, departments: Iterable[str],
          types: Iterable[MemoryType] | None = None) -> list[dict]:
    depts = list(departments)
    sql = [
        "SELECT * FROM memories WHERE company_id = ? AND superseded_by IS NULL"
    ]
    params: list[Any] = [company_id]
    if depts:
        sql.append(f"AND department IN ({','.join('?' * len(depts))})")
        params.extend(depts)
    type_list = [str(t) for t in (types or [])]
    if type_list:
        sql.append(f"AND memory_type IN ({','.join('?' * len(type_list))})")
        params.extend(type_list)
    with connection() as conn:
        rows = conn.execute(" ".join(sql), params).fetchall()
    return [dict(r) for r in rows]


def _score(row: dict, query_tokens: set[str], now: datetime) -> float:
    """Relevance: token overlap, weighted by recency and proven usefulness."""
    tokens = set((row["tokens"] or "").split())
    if not tokens or not query_tokens:
        return 0.0
    overlap = len(query_tokens & tokens) / len(query_tokens)
    if overlap == 0:
        return 0.0

    created = datetime.fromisoformat(row["created_at"])
    age_days = max((now - created).total_seconds() / 86_400, 0.0)
    recency = 1.0 / (1.0 + math.log1p(age_days))
    usefulness = 1.0 + math.log1p(row.get("retrieval_count", 0))
    confidence = row.get("confidence", 0.5)

    return overlap * (0.6 + 0.4 * recency) * usefulness * (0.5 + confidence)


def retrieve(
    company_id: str,
    department: str,
    query: str,
    *,
    types: Iterable[MemoryType] | None = None,
    limit: int = 5,
    now: datetime | None = None,
    record_retrieval: bool = True,
) -> list[dict]:
    """The department's own memory, and only its own.

    Scoping is applied in the SQL, so there is no code path by which another
    department's entries can be returned.
    """
    if not department or not department.strip():
        raise MemoryScopeViolation(
            "retrieve requires a department; use retrieve_shared explicitly if "
            "an unscoped read is genuinely intended"
        )
    moment = now or datetime.now(UTC)
    query_tokens = set(tokenise(query))
    scored = [
        (_score(row, query_tokens, moment), row)
        for row in _rows(company_id, [department], types)
    ]
    hits = [row for score, row in sorted(scored, key=lambda p: -p[0]) if score > 0]
    hits = hits[:limit]

    if record_retrieval and hits:
        with connection() as conn:
            for row in hits:
                conn.execute(
                    "UPDATE memories SET retrieval_count = retrieval_count + 1, "
                    "last_retrieved_at = ? WHERE id = ?",
                    (moment.isoformat(), row["id"]),
                )
    return hits


def retrieve_shared(
    company_id: str,
    query: str,
    *,
    types: Iterable[MemoryType] | None = None,
    limit: int = 5,
    now: datetime | None = None,
) -> list[dict]:
    """Unscoped retrieval across every department.

    This is the **control arm** for the scoped-versus-shared comparison. The
    operating layer does not call it; it exists so the difference can be
    measured rather than asserted.
    """
    moment = now or datetime.now(UTC)
    query_tokens = set(tokenise(query))
    scored = [
        (_score(row, query_tokens, moment), row)
        for row in _rows(company_id, [], types)
    ]
    return [row for score, row in sorted(scored, key=lambda p: -p[0])
            if score > 0][:limit]


# ------------------------------------------------------------- housekeeping ----


def supersede(memory_id: str, replacement_id: str) -> None:
    """Retire an entry without deleting it. History stays inspectable."""
    with connection() as conn:
        conn.execute(
            "UPDATE memories SET superseded_by = ? WHERE id = ?",
            (replacement_id, memory_id),
        )


def decay(company_id: str, department: str, *,
          older_than_days: int = DECAY_AFTER_DAYS,
          now: datetime | None = None) -> int:
    """Retire entries that have never been retrieved and have aged out.

    Retirement, not deletion: a decayed entry is marked and excluded from
    retrieval, so the corpus stops competing for attention without the record
    being destroyed.
    """
    moment = now or datetime.now(UTC)
    cutoff = (moment - timedelta(days=older_than_days)).isoformat()
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE memories SET superseded_by = 'decayed' "
            "WHERE company_id = ? AND department = ? AND superseded_by IS NULL "
            "AND retrieval_count = 0 AND created_at < ? "
            "AND memory_type = ?",
            (company_id, department, cutoff, str(MemoryType.EPISODIC)),
        )
    return cursor.rowcount


def stats(company_id: str) -> dict[str, dict[str, int]]:
    """Per-department counts by type, for the interface and for RQ instrumentation."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT department, memory_type, COUNT(*) AS n FROM memories "
            "WHERE company_id = ? AND superseded_by IS NULL "
            "GROUP BY department, memory_type",
            (company_id,),
        ).fetchall()
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        out.setdefault(row["department"], {})[row["memory_type"]] = int(row["n"])
    return out


def count(company_id: str, department: str | None = None) -> int:
    departments = [department] if department else []
    return len(_rows(company_id, departments))
