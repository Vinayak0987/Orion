"""Data Processing built-in tools (18).

Operate on JSON-native structures (lists of dicts = "records") plus JSON/YAML/
XML/CSV parsing. All pure-python/stdlib except yaml (PyYAML). Every tool returns
a dict and degrades on bad input rather than raising.
"""

from __future__ import annotations

import csv as _csv
import io
import json as _json
from collections import defaultdict

from app.tools.base import ToolContext, err, need, ok, tool


def _as_records(ti: dict, key: str = "records"):
    recs = ti.get(key)
    if not isinstance(recs, list):
        return None
    return recs


# --- 41. json_tool -----------------------------------------------------------
@tool(
    "json_tool",
    description="Parse/validate/pretty-print JSON or read a dotted path from it. Input: "
    "{text?: str, data?: any, mode?: parse|stringify|get, path?: str (dotted)}.",
    category="data",
    input_schema={"text": {"type": "string"}, "data": {}, "mode": {"type": "string"}, "path": {"type": "string"}},
)
def json_tool(ti: dict, ctx: ToolContext) -> dict:
    mode = (ti.get("mode") or ("parse" if "text" in ti else "stringify")).lower()
    try:
        if mode == "parse":
            return ok(data=_json.loads(ti.get("text", "")))
        if mode == "stringify":
            return ok(text=_json.dumps(ti.get("data"), indent=2, ensure_ascii=False, default=str))
        if mode == "get":
            data = ti.get("data")
            if data is None and "text" in ti:
                data = _json.loads(ti["text"])
            cur = data
            for part in (ti.get("path") or "").split("."):
                if part == "":
                    continue
                if isinstance(cur, list):
                    cur = cur[int(part)]
                else:
                    cur = cur[part]
            return ok(value=cur)
        return err(f"unknown mode: {mode}")
    except Exception as e:  # noqa: BLE001
        return err(f"json_tool: {e}")


# --- 42. yaml_tool -----------------------------------------------------------
@tool(
    "yaml_tool",
    description="Parse YAML to data or dump data to YAML. Input: {text?: str, data?: any, mode?: parse|dump}.",
    category="data",
    input_schema={"text": {"type": "string"}, "data": {}, "mode": {"type": "string"}},
)
def yaml_tool(ti: dict, ctx: ToolContext) -> dict:
    try:
        import yaml
    except Exception as e:  # noqa: BLE001
        return err(f"yaml_tool needs PyYAML: {e}", degraded=True)
    mode = (ti.get("mode") or ("parse" if "text" in ti else "dump")).lower()
    try:
        if mode == "parse":
            return ok(data=yaml.safe_load(ti.get("text", "")))
        return ok(text=yaml.safe_dump(ti.get("data"), sort_keys=False, allow_unicode=True))
    except Exception as e:  # noqa: BLE001
        return err(f"yaml_tool: {e}")


# --- 43. xml_tool ------------------------------------------------------------
@tool(
    "xml_tool",
    description="Parse an XML string into a nested dict (tag/attrib/text/children). Input: {text: str}.",
    category="data",
    input_schema={"text": {"type": "string", "required": True}},
)
def xml_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    import xml.etree.ElementTree as ET

    def node(e):
        d = {"tag": e.tag}
        if e.attrib:
            d["attrib"] = e.attrib
        children = list(e)
        if children:
            d["children"] = [node(c) for c in children]
        text = (e.text or "").strip()
        if text:
            d["text"] = text
        return d

    try:
        root = ET.fromstring(ti["text"])
        return ok(data=node(root))
    except Exception as e:  # noqa: BLE001
        return err(f"xml_tool: {e}")


# --- 44. csv_tool ------------------------------------------------------------
@tool(
    "csv_tool",
    description="Parse CSV text to records (list of dicts) or serialize records to CSV. Input: "
    "{text?: str, records?: [object], mode?: parse|write, delimiter?: str}.",
    category="data",
    input_schema={"text": {"type": "string"}, "records": {"type": "array"}, "mode": {"type": "string"}},
)
def csv_tool(ti: dict, ctx: ToolContext) -> dict:
    mode = (ti.get("mode") or ("parse" if "text" in ti else "write")).lower()
    delim = ti.get("delimiter") or ","
    try:
        if mode == "parse":
            reader = _csv.DictReader(io.StringIO(ti.get("text", "")), delimiter=delim)
            rows = list(reader)
            return ok(records=rows, count=len(rows), columns=reader.fieldnames or [])
        recs = _as_records(ti)
        if not recs:
            return err("'records' must be a non-empty array for write mode")
        cols = list(recs[0].keys())
        buf = io.StringIO()
        w = _csv.DictWriter(buf, fieldnames=cols, delimiter=delim)
        w.writeheader()
        w.writerows(recs)
        return ok(text=buf.getvalue())
    except Exception as e:  # noqa: BLE001
        return err(f"csv_tool: {e}")


# --- 45. data_cleaner --------------------------------------------------------
@tool(
    "data_cleaner",
    description="Clean records: trim strings, drop empty/null fields, optionally drop rows missing "
    "required keys. Input: {records: [object], required?: [str]}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "required": {"type": "array"}},
)
def data_cleaner(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None:
        return err("'records' must be an array")
    req = ti.get("required") or []
    out = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()
                   if v not in (None, "", [])}
        if all(cleaned.get(k) not in (None, "") for k in req):
            out.append(cleaned)
    return ok(records=out, count=len(out), dropped=len(recs) - len(out))


# --- 46. data_validator ------------------------------------------------------
@tool(
    "data_validator",
    description="Validate records against required keys and simple type rules. Input: "
    "{records: [object], required?: [str], types?: {field: 'string|number|boolean|array|object'}}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}},
)
def data_validator(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None:
        return err("'records' must be an array")
    req, types = ti.get("required") or [], ti.get("types") or {}
    pytypes = {"string": str, "number": (int, float), "boolean": bool, "array": list, "object": dict}
    errors = []
    for i, r in enumerate(recs):
        for k in req:
            if k not in r:
                errors.append({"row": i, "field": k, "issue": "missing"})
        for k, t in types.items():
            if k in r and t in pytypes and not isinstance(r[k], pytypes[t]):
                errors.append({"row": i, "field": k, "issue": f"expected {t}"})
    return ok(valid=not errors, errors=errors, checked=len(recs))


# --- 47. schema_validator ----------------------------------------------------
@tool(
    "schema_validator",
    description="Validate a single object against a lightweight JSON-schema-like spec "
    "({field: {type, required}}). Input: {data: object, schema: object}.",
    category="data",
    input_schema={"data": {"type": "object", "required": True}, "schema": {"type": "object", "required": True}},
)
def schema_validator(ti: dict, ctx: ToolContext) -> dict:
    data, schema = ti.get("data"), ti.get("schema")
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return err("'data' and 'schema' must be objects")
    pytypes = {"string": str, "number": (int, float), "integer": int, "boolean": bool,
               "array": list, "object": dict}
    errors = []
    for field, spec in schema.items():
        spec = spec if isinstance(spec, dict) else {"type": spec}
        if spec.get("required") and field not in data:
            errors.append({"field": field, "issue": "required"})
            continue
        if field in data and spec.get("type") in pytypes and not isinstance(data[field], pytypes[spec["type"]]):
            errors.append({"field": field, "issue": f"expected {spec['type']}"})
    return ok(valid=not errors, errors=errors)


# --- 48. data_transformer ----------------------------------------------------
@tool(
    "data_transformer",
    description="Map/rename/select fields across records. Input: {records: [object], "
    "rename?: {old: new}, select?: [str], drop?: [str]}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}},
)
def data_transformer(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None:
        return err("'records' must be an array")
    rename, select, drop = ti.get("rename") or {}, ti.get("select"), set(ti.get("drop") or [])
    out = []
    for r in recs:
        row = {rename.get(k, k): v for k, v in r.items() if k not in drop}
        if select:
            row = {k: row.get(k) for k in select}
        out.append(row)
    return ok(records=out, count=len(out))


# --- 49. data_aggregator -----------------------------------------------------
@tool(
    "data_aggregator",
    description="Aggregate a numeric field across records. Input: {records: [object], field: str, "
    "op?: sum|avg|min|max|count}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "field": {"type": "string", "required": True}},
)
def data_aggregator(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None or (m := need(ti, "field")):
        return err("'records' array and 'field' required")
    f, op = ti["field"], (ti.get("op") or "sum").lower()
    vals = [r[f] for r in recs if isinstance(r.get(f), (int, float))]
    if op == "count":
        return ok(result=len([r for r in recs if f in r]), op=op)
    if not vals:
        return ok(result=None, op=op, note="no numeric values")
    res = {"sum": sum(vals), "avg": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}.get(op)
    if res is None:
        return err(f"unknown op: {op}")
    return ok(result=res, op=op, n=len(vals))


# --- 50. data_joiner ---------------------------------------------------------
@tool(
    "data_joiner",
    description="Inner/left join two record sets on a key. Input: {left: [object], right: [object], "
    "key: str, how?: inner|left}.",
    category="data",
    input_schema={"left": {"type": "array", "required": True}, "right": {"type": "array", "required": True},
                  "key": {"type": "string", "required": True}},
)
def data_joiner(ti: dict, ctx: ToolContext) -> dict:
    left, right, key = ti.get("left"), ti.get("right"), ti.get("key")
    if not isinstance(left, list) or not isinstance(right, list) or not key:
        return err("requires 'left', 'right' arrays and a 'key'")
    how = (ti.get("how") or "inner").lower()
    index = defaultdict(list)
    for r in right:
        index[r.get(key)].append(r)
    out = []
    for l in left:
        matches = index.get(l.get(key), [])
        if matches:
            for r in matches:
                out.append({**r, **l})
        elif how == "left":
            out.append(dict(l))
    return ok(records=out, count=len(out))


# --- 51. data_deduplicator ---------------------------------------------------
@tool(
    "data_deduplicator",
    description="Remove duplicate records, optionally by a subset of keys. Input: {records: [object], by?: [str]}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "by": {"type": "array"}},
)
def data_deduplicator(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None:
        return err("'records' must be an array")
    by = ti.get("by")
    seen, out = set(), []
    for r in recs:
        key = tuple(r.get(k) for k in by) if by else _json.dumps(r, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return ok(records=out, count=len(out), removed=len(recs) - len(out))


# --- 52. data_filter ---------------------------------------------------------
@tool(
    "data_filter",
    description="Filter records by field conditions. Input: {records: [object], where: {field: value} "
    "or {field: {op: eq|ne|gt|lt|gte|lte|contains, value: any}}}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "where": {"type": "object", "required": True}},
)
def data_filter(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    where = ti.get("where")
    if recs is None or not isinstance(where, dict):
        return err("requires 'records' array and 'where' object")

    def match(r):
        for f, cond in where.items():
            v = r.get(f)
            if isinstance(cond, dict) and "op" in cond:
                op, target = cond["op"], cond.get("value")
                try:
                    if op == "eq" and v != target: return False
                    if op == "ne" and v == target: return False
                    if op == "gt" and not (v > target): return False
                    if op == "lt" and not (v < target): return False
                    if op == "gte" and not (v >= target): return False
                    if op == "lte" and not (v <= target): return False
                    if op == "contains" and target not in (v or ""): return False
                except TypeError:
                    return False
            elif v != cond:
                return False
        return True

    out = [r for r in recs if match(r)]
    return ok(records=out, count=len(out))


# --- 53. data_sorter ---------------------------------------------------------
@tool(
    "data_sorter",
    description="Sort records by a field. Input: {records: [object], by: str, desc?: bool}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "by": {"type": "string", "required": True}},
)
def data_sorter(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None or (m := need(ti, "by")):
        return err("requires 'records' array and 'by'")
    by = ti["by"]
    try:
        out = sorted(recs, key=lambda r: (r.get(by) is None, r.get(by)), reverse=bool(ti.get("desc")))
    except TypeError:
        out = sorted(recs, key=lambda r: str(r.get(by)), reverse=bool(ti.get("desc")))
    return ok(records=out, count=len(out))


# --- 54. data_grouping -------------------------------------------------------
@tool(
    "data_grouping",
    description="Group records by a field; returns groups with counts. Input: {records: [object], by: str}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}, "by": {"type": "string", "required": True}},
)
def data_grouping(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None or (m := need(ti, "by")):
        return err("requires 'records' array and 'by'")
    by = ti["by"]
    groups = defaultdict(list)
    for r in recs:
        groups[str(r.get(by))].append(r)
    return ok(groups={k: v for k, v in groups.items()},
              counts={k: len(v) for k, v in groups.items()}, group_count=len(groups))


# --- 55. data_merger ---------------------------------------------------------
@tool(
    "data_merger",
    description="Concatenate multiple record arrays into one. Input: {sources: [[object], ...]}.",
    category="data",
    input_schema={"sources": {"type": "array", "required": True}},
)
def data_merger(ti: dict, ctx: ToolContext) -> dict:
    sources = ti.get("sources")
    if not isinstance(sources, list):
        return err("'sources' must be an array of arrays")
    out = []
    for s in sources:
        if isinstance(s, list):
            out.extend(s)
    return ok(records=out, count=len(out))


# --- 56. jsonl_reader --------------------------------------------------------
@tool(
    "jsonl_reader",
    description="Parse JSONL (one JSON object per line) into records. Input: {text: str}.",
    category="data",
    input_schema={"text": {"type": "string", "required": True}},
)
def jsonl_reader(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    records, errors = [], []
    for i, line in enumerate(ti["text"].splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(_json.loads(line))
        except Exception as e:  # noqa: BLE001
            errors.append({"line": i, "error": str(e)})
    return ok(records=records, count=len(records), errors=errors)


# --- 57. jsonl_writer --------------------------------------------------------
@tool(
    "jsonl_writer",
    description="Serialize records to JSONL text (one object per line). Input: {records: [object]}.",
    category="data",
    input_schema={"records": {"type": "array", "required": True}},
)
def jsonl_writer(ti: dict, ctx: ToolContext) -> dict:
    recs = _as_records(ti)
    if recs is None:
        return err("'records' must be an array")
    text = "\n".join(_json.dumps(r, ensure_ascii=False, default=str) for r in recs)
    return ok(text=text, count=len(recs))


# --- 58. table_extractor -----------------------------------------------------
@tool(
    "table_extractor",
    description="Extract HTML <table> elements from an HTML string into records. Input: {html: str, index?: int}.",
    category="data",
    input_schema={"html": {"type": "string", "required": True}, "index": {"type": "integer"}},
)
def table_extractor(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "html")):
        return err(m)
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(ti["html"], "lxml")
        tables = soup.find_all("table")
        if not tables:
            return ok(tables=[], count=0, note="no tables found")
        idx = ti.get("index")
        chosen = [tables[idx]] if idx is not None else tables
        parsed = []
        for t in chosen:
            rows = t.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
            recs = []
            for tr in rows[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                recs.append(dict(zip(headers, cells)))
            parsed.append({"headers": headers, "records": recs})
        return ok(tables=parsed, count=len(parsed))
    except Exception as e:  # noqa: BLE001
        return err(f"table_extractor: {e}", degraded=True)
