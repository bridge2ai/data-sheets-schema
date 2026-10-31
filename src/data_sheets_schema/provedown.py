"""Inline verifiable watermarks in markdown prose reports (provedown pattern).

Inspired by `ai4curation/provedown` and Slides 8 & 14 of *"Show me the
receipts: patterns for truth verification in agentic knowledge generation"*.

`report_claims.py` deliberately restricts free-prose parsing to table cells and
backticked `**Action:**` lines so regex heuristics do not produce false
positives on narrative prose. When an author or agent wants free-prose numeric,
structural, chunk-quote, or schema claims in `{PROJECT}_reconciliation.md` (or
any narrative markdown report) to be deterministically checked, they can embed
inline provedown watermarks:

1. Backtick attribute form:
   `` `165,051`{pd: full:/total_files} ``
   `` `64/75`{pd: ratio(receipt:/slots/with_receipt, receipt:/slots/receiptable)} ``
   `` `distributions`{pd: schema:CoreDataset.distributions} ``
   `` `phyla`{pd: schema:!Dataset.phyla} ``

2. Bracketed HTML-comment form (renders invisibly in standard Markdown viewers):
   ``[165,051]<!-- pd: full:/total_files -->``
   ``[OT2OD032701]<!-- pd: chunk:c001 -->``

Supported expression grammars:
- `<source>:/<json_pointer_or_slot_path>` where `<source>` is one of
  `full`, `core`, `snapshot`, `receipt`, `manifest`. Both RFC 6901 JSON
  Pointers (`/file_collections/0/total_bytes`) and D4D slot paths
  (`file_collections[0].total_bytes`) are accepted.
- `count(<source>:/<path>)` — count of items in a list/mapping at `<path>`
  (0 when absent/empty).
- `sum(<source>:/<path>)` — numeric sum over values resolved at `<path>`
  (supports wildcard `*` or `[*]`, e.g. `sum(full:/file_collections/*/total_bytes)`).
- `ratio(<expr_a>, <expr_b>)` — verifies `A/B` (or percentage `X%` / `X.Y%`)
  against two integer/numeric sub-expressions.
- `chunk:<cid>` — verifies that the display text is a verified snippet of
  `chunk_texts[cid]` under `receipts.snippet_in`.
- `schema:<Class>.<slot>` and `schema:!<Class>.<slot>` — verifies that `<slot>`
  is (or is not) a declared slot of `<Class>` in `declared`.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

from data_sheets_schema.receipts import normalise, snippet_in

PROVEDOWN_INSTRUMENT = (
    "v1 (provedown): deterministic verification of inline markdown watermarks "
    "(`value`{pd: expr} and [value]<!-- pd: expr -->) against full/core/snapshot "
    "records, receipt/manifest blocks, chunk texts, and schema slot declarations"
)

_FENCED_BLOCK_RE = re.compile(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", re.M | re.S)

_ATTR_WATERMARK_RE = re.compile(
    r"`(?P<display>[^`\n]+)`\{\s*pd\s*:\s*(?P<expr>[^}\n]+?)\s*\}"
)
_COMMENT_WATERMARK_RE = re.compile(
    r"\[(?P<display>[^\]\n]+)\]<!--\s*pd\s*:\s*(?P<expr>[^>]+?)\s*-->"
)
_WATERMARK_START_RE = re.compile(r"(?P<attr>\{\s*pd\s*:)|(?P<comment><!--\s*pd\s*:)")

_SOURCE_PATH_RE = re.compile(
    r"^(?P<source>full|core|snapshot|receipt|manifest):(?P<path>.+)$"
)
_FUNC_ONE_RE = re.compile(
    r"^(?P<func>count|sum)\(\s*(?P<arg>[^)]+?)\s*\)$"
)
_RATIO_RE = re.compile(
    r"^(?P<func>ratio|pct)\(\s*(?P<num>[^,]+?)\s*,\s*(?P<den>[^)]+?)\s*\)$"
)
_CHUNK_RE = re.compile(r"^chunk:(?P<cid>[A-Za-z0-9_.-]+)$")
_SCHEMA_RE = re.compile(
    r"^schema:(?P<neg>!)?(?P<cls>[A-Za-z_][A-Za-z0-9_]*)\.(?P<slot>[A-Za-z_][A-Za-z0-9_]*)$"
)

_UNIT_MULTIPLIERS: dict[str, float] = {
    "b": 1.0,
    "byte": 1.0,
    "bytes": 1.0,
    "kb": 1e3,
    "kilobyte": 1e3,
    "kilobytes": 1e3,
    "kib": 1024.0,
    "mb": 1e6,
    "megabyte": 1e6,
    "megabytes": 1e6,
    "mib": 1024.0 ** 2,
    "gb": 1e9,
    "gigabyte": 1e9,
    "gigabytes": 1e9,
    "gib": 1024.0 ** 3,
    "tb": 1e12,
    "terabyte": 1e12,
    "terabytes": 1e12,
    "tib": 1024.0 ** 4,
}

_NUMBER_WITH_UNIT_RE = re.compile(
    r"^\s*(?P<num>[+-]?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>[A-Za-z]+)?\s*$"
)


def _strip_fenced_code_blocks(markdown_text: str) -> str:
    """Replace fenced code blocks with newline-preserving spaces so line
    numbers and offsets outside fences remain aligned."""
    def _blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _FENCED_BLOCK_RE.sub(_blank, markdown_text)


def extract_watermarks(markdown_text: str) -> list[dict[str, Any]]:
    """Extract watermarks, including malformed explicit markers, outside fences.

    An author requesting verification with ``{pd:`` or ``<!-- pd:`` must
    receive a finding when the surrounding syntax is incomplete. Silently
    ignoring that request would make a broken watermark look like no claim.
    """
    cleaned = _strip_fenced_code_blocks(markdown_text)
    found: list[tuple[int, dict[str, Any]]] = []
    matched_spans: list[tuple[int, int]] = []
    for style, pattern in (("attr", _ATTR_WATERMARK_RE), ("comment", _COMMENT_WATERMARK_RE)):
        for m in pattern.finditer(cleaned):
            matched_spans.append(m.span())
            line_no = cleaned.count("\n", 0, m.start()) + 1
            display = m.group("display").strip()
            expr = m.group("expr").strip()
            found.append((
                m.start(),
                {
                    "style": style,
                    "display": display,
                    "expr": expr,
                    "raw": m.group(0),
                    "line": line_no,
                    **({"parse_error": "empty watermark display or expression"}
                       if not display or not expr else {}),
                },
            ))
    for start in _WATERMARK_START_RE.finditer(cleaned):
        if any(left <= start.start() < right for left, right in matched_spans):
            continue
        end = cleaned.find("\n", start.end())
        if end == -1:
            end = len(cleaned)
        found.append((start.start(), {
            "style": "attr" if start.group("attr") else "comment",
            "display": "",
            "expr": cleaned[start.end():end].strip(),
            "raw": cleaned[start.start():end],
            "line": cleaned.count("\n", 0, start.start()) + 1,
            "parse_error": "malformed or unclosed provedown watermark",
        }))
    found.sort(key=lambda item: item[0])
    return [item[1] for item in found]


def render_watermark(
    display_or_expr: str,
    expr: str | None = None,
    *,
    style: str = "attr",
    full: Mapping[str, Any] | None = None,
    core: Mapping[str, Any] | None = None,
    snapshot: Mapping[str, Any] | None = None,
    receipt: Mapping[str, Any] | None = None,
    receipt_block: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> str:
    """Format a display string and provedown expression as an inline watermark.

    Can be called either as `render_watermark(display, expr, style=...)` or as
    `render_watermark(expr, full=..., core=..., receipt_block=..., style=...)`
    to auto-compute the display string from the expression.
    """
    if expr is None:
        expr = display_or_expr.strip()
        ctx: dict[str, Any] = {
            "full": full,
            "core": core,
            "snapshot": snapshot,
            "receipt": receipt if receipt is not None else receipt_block,
            "manifest": manifest,
        }
        m_ratio = _RATIO_RE.match(expr)
        if m_ratio:
            ok_n, num_val, err_n = _eval_scalar_expr(m_ratio.group("num"), ctx)
            ok_d, den_val, err_d = _eval_scalar_expr(m_ratio.group("den"), ctx)
            if not ok_n or not ok_d:
                raise ValueError(f"cannot render watermark {expr!r}: {err_n or err_d}")
            if m_ratio.group("func") == "pct":
                display = f"{100.0 * float(num_val) / float(den_val):.1f}%"
            else:
                display = f"{num_val}/{den_val}"
        else:
            ok, val, err = _eval_scalar_expr(expr, ctx)
            if not ok:
                raise ValueError(f"cannot render watermark {expr!r}: {err}")
            display = str(val)
    else:
        display = display_or_expr
    if style == "attr":
        return f"`{display}`{{pd: {expr}}}"
    if style == "comment":
        return f"[{display}]<!-- pd: {expr} -->"
    raise ValueError(f"unsupported watermark style: {style!r}")


def _parse_path_tokens(path: str) -> list[str]:
    """Convert either a JSON Pointer (`/a/0/b` or `/a/*/b`) or a D4D slot path
    (`a[0].b` or `a[*].b`) into a list of navigation tokens."""
    p = path.strip()
    if p.startswith("/"):
        # RFC 6901: remove exactly the pointer's leading slash. Empty keys
        # are meaningful, including a leading, interior or trailing key.
        raw_parts = [seg.replace("~1", "/").replace("~0", "~") for seg in p[1:].split("/")]
        return raw_parts
    tokens: list[str] = []
    for part in re.findall(r"[\w]+|\[\d+\]|\[\*\]|\*", p):
        if part == "[*]" or part == "*":
            tokens.append("*")
        elif part.startswith("[") and part.endswith("]"):
            tokens.append(part[1:-1])
        else:
            tokens.append(part)
    return tokens


def _resolve_tokens(node: Any, tokens: list[str]) -> tuple[bool, Any, bool]:
    """Resolve `tokens` against `node`. Returns `(found, value, wildcard_used)`."""
    if not tokens:
        return True, node, False

    has_wildcard = "*" in tokens

    def _walk(cur: Any, idx: int) -> list[Any]:
        if idx == len(tokens):
            return [cur]
        tok = tokens[idx]
        if tok == "*":
            if isinstance(cur, list):
                out: list[Any] = []
                for item in cur:
                    out.extend(_walk(item, idx + 1))
                return out
            if isinstance(cur, dict):
                out = []
                for item in cur.values():
                    out.extend(_walk(item, idx + 1))
                return out
            return []
        if isinstance(cur, list):
            if tok.isdigit():
                i = int(tok)
                if 0 <= i < len(cur):
                    return _walk(cur[i], idx + 1)
                return []
            # Implicit list traversal for dotted paths over lists
            out = []
            for item in cur:
                out.extend(_walk(item, idx))
            return out
        if isinstance(cur, dict) and tok in cur:
            return _walk(cur[tok], idx + 1)
        return []

    results = _walk(node, 0)
    if not results:
        return False, None, has_wildcard
    if has_wildcard:
        return True, results, True
    return True, results[0], False


def _eval_scalar_expr(expr: str, context: Mapping[str, Any]) -> tuple[bool, Any, str | None]:
    """Evaluate a value-producing expression (`<source>:<path>`, `count(...)`,
    `sum(...)`) against `context`. Returns `(ok, value, error_reason)`."""
    expr = expr.strip()
    m_func = _FUNC_ONE_RE.match(expr)
    if m_func:
        func = m_func.group("func")
        arg = m_func.group("arg").strip()
        ok, val, err = _eval_scalar_expr(arg, context)
        if not ok:
            if func == "count" and err and err.startswith("path_not_found:"):
                return True, 0, None
            return False, None, err
        if func == "count":
            if val is None:
                return True, 0, None
            if isinstance(val, (list, dict, tuple, set)):
                return True, len(val), None
            return True, 1, None
        if func == "sum":
            items = val if isinstance(val, list) else [val]
            nums: list[float | int] = []
            for item in items:
                if isinstance(item, bool) or not isinstance(item, (int, float)):
                    return False, None, f"non_numeric_in_sum:{item!r}"
                nums.append(item)
            return True, sum(nums), None

    m_src = _SOURCE_PATH_RE.match(expr)
    if m_src:
        source_name = m_src.group("source")
        raw_path = m_src.group("path")
        source_obj = context.get(source_name)
        if source_obj is None:
            return False, None, f"source_unavailable:{source_name}"
        tokens = _parse_path_tokens(raw_path)
        found, value, _wild = _resolve_tokens(source_obj, tokens)
        if not found:
            return False, None, f"path_not_found:{source_name}:{raw_path}"
        return True, value, None

    return False, None, f"unrecognized_expression:{expr}"


def _numbers_match(display: str, expected: int | float) -> bool:
    """Check whether `display` matches numeric `expected` (exact, comma-grouped,
    or unit-scaled for byte counts)."""
    m = _NUMBER_WITH_UNIT_RE.match(display.strip())
    if not m:
        return False
    try:
        disp_val = float(m.group("num").replace(",", ""))
    except ValueError:
        return False
    unit = (m.group("unit") or "").lower()
    if not unit:
        if isinstance(expected, int) and "." not in m.group("num"):
            return int(m.group("num").replace(",", "")) == expected
        tol = max(1e-9, abs(float(expected)) * 1e-6)
        return math.isclose(disp_val, float(expected), abs_tol=tol, rel_tol=1e-6)
    if unit in _UNIT_MULTIPLIERS:
        # Compare under both decimal (TB=1e12) and binary (TiB=1024^4) conventions
        # because prose often writes "3.82 TB" for either 3.82e12 or 3.82 * 1024^4.
        mult_dec = _UNIT_MULTIPLIERS[unit]
        binary_key = {"kb": "kib", "mb": "mib", "gb": "gib", "tb": "tib"}.get(unit, unit)
        mult_bin = _UNIT_MULTIPLIERS[binary_key]
        # Allow half-ulp rounding at the written decimal precision
        num_str = m.group("num").replace(",", "")
        decimals = len(num_str.split(".")[1]) if "." in num_str else 0
        half_step = 0.5 * (10 ** (-decimals))
        for mult in (mult_dec, mult_bin):
            scaled = float(expected) / mult
            if abs(disp_val - scaled) <= half_step + 1e-9:
                return True
    return False


def _values_match(display: str, expected: Any) -> bool:
    """Compare a display string from prose with an expected Python value."""
    disp = display.strip()
    if expected is None:
        return disp.lower() in ("null", "none", "n/a", "absent")
    if isinstance(expected, bool):
        return disp.lower() == ("true" if expected else "false")
    if isinstance(expected, (int, float)):
        return _numbers_match(disp, expected)
    if isinstance(expected, str):
        if disp == expected.strip():
            return True
        return normalise(disp) == normalise(expected)
    if isinstance(expected, (list, dict)):
        # Allow scalar count display if someone points directly at a list and writes its length?
        # No, `count(...)` is for lengths; direct list match compares normalized string representation.
        return normalise(disp) == normalise(str(expected))
    return disp == str(expected)


def evaluate_watermark(expr: str, display: str, context: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a single watermark claim against `context`."""
    expr = expr.strip()
    display = display.strip()

    # 1. Schema declaration claim: schema:Class.slot or schema:!Class.slot
    m_schema = _SCHEMA_RE.match(expr)
    if m_schema:
        negated = bool(m_schema.group("neg"))
        cls_name = m_schema.group("cls")
        slot_name = m_schema.group("slot")
        declared = context.get("declared")
        if not isinstance(declared, Mapping):
            return {
                "verified": False,
                "kind": "watermark_source_unavailable",
                "expr": expr,
                "display": display,
                "detail": "schema declarations unavailable",
            }
        cls_slots = declared.get(cls_name)
        if cls_slots is None:
            return {
                "verified": False,
                "kind": "watermark_schema_mismatch",
                "expr": expr,
                "display": display,
                "detail": f"class {cls_name!r} is not in declared schema classes",
            }
        is_declared = slot_name in cls_slots
        # Also verify display names either the slot or class.slot
        if display not in (slot_name, f"{cls_name}.{slot_name}"):
            return {
                "verified": False,
                "kind": "watermark_display_mismatch",
                "expr": expr,
                "display": display,
                "expected": slot_name,
                "detail": f"display {display!r} does not name slot {slot_name!r}",
            }
        passed = (not is_declared) if negated else is_declared
        return {
            "verified": passed,
            "kind": "ok" if passed else "watermark_schema_mismatch",
            "expr": expr,
            "display": display,
            "expected": f"{'not ' if negated else ''}declared on {cls_name}",
            "actual": "declared" if is_declared else "not declared",
            "detail": (
                f"{cls_name}.{slot_name} is {'declared' if is_declared else 'not declared'}"
            ),
        }

    # 2. Chunk quote watermark: chunk:cNNN
    m_chunk = _CHUNK_RE.match(expr)
    if m_chunk:
        cid = m_chunk.group("cid")
        chunk_texts = context.get("chunk_texts")
        if not isinstance(chunk_texts, Mapping):
            return {
                "verified": False,
                "kind": "watermark_source_unavailable",
                "expr": expr,
                "display": display,
                "detail": "chunk_texts unavailable",
            }
        if cid not in chunk_texts:
            return {
                "verified": False,
                "kind": "watermark_chunk_mismatch",
                "expr": expr,
                "display": display,
                "detail": f"chunk {cid!r} not found in chunk_texts",
            }
        ok, why = snippet_in(display, chunk_texts[cid])
        return {
            "verified": ok,
            "kind": "ok" if ok else "watermark_chunk_mismatch",
            "expr": expr,
            "display": display,
            "detail": why,
        }

    # 3. Ratio watermark: ratio(num_expr, den_expr)
    m_ratio = _RATIO_RE.match(expr)
    if m_ratio:
        ok_n, num_val, err_n = _eval_scalar_expr(m_ratio.group("num"), context)
        ok_d, den_val, err_d = _eval_scalar_expr(m_ratio.group("den"), context)
        if not ok_n or not ok_d:
            return {
                "verified": False,
                "kind": "watermark_path_unresolved",
                "expr": expr,
                "display": display,
                "detail": err_n or err_d or "ratio operand unresolved",
            }
        if not isinstance(num_val, (int, float)) or not isinstance(den_val, (int, float)):
            return {
                "verified": False,
                "kind": "watermark_value_mismatch",
                "expr": expr,
                "display": display,
                "detail": f"ratio operands must be numeric, got {num_val!r} and {den_val!r}",
            }
        expected_forms = {
            f"{num_val}/{den_val}",
            f"{num_val:,}/{den_val:,}" if isinstance(num_val, int) and isinstance(den_val, int) else f"{num_val}/{den_val}",
        }
        disp_clean = display.replace(" ", "")
        matched = disp_clean in expected_forms
        if not matched and den_val != 0 and disp_clean.endswith("%"):
            try:
                pct = float(disp_clean[:-1].replace(",", ""))
                actual_pct = 100.0 * float(num_val) / float(den_val)
                num_str = disp_clean[:-1].replace(",", "")
                decimals = len(num_str.split(".")[1]) if "." in num_str else 0
                half_step = 0.5 * (10 ** (-decimals))
                matched = abs(pct - actual_pct) <= half_step + 1e-9
            except ValueError:
                matched = False
        return {
            "verified": matched,
            "kind": "ok" if matched else "watermark_value_mismatch",
            "expr": expr,
            "display": display,
            "expected": f"{num_val}/{den_val}",
            "actual": display,
            "detail": (
                f"expected {num_val}/{den_val}"
                + (f" ({100.0 * float(num_val) / float(den_val):.1f}%)" if den_val else "")
                + f", prose has {display!r}"
            ),
        }

    # 4. Scalar / count / sum expression
    ok, expected_val, err = _eval_scalar_expr(expr, context)
    if not ok:
        kind = (
            "watermark_source_unavailable"
            if (err or "").startswith("source_unavailable:")
            else "watermark_path_unresolved"
        )
        return {
            "verified": False,
            "kind": kind,
            "expr": expr,
            "display": display,
            "detail": err or "expression could not be resolved",
        }
    matched = _values_match(display, expected_val)
    return {
        "verified": matched,
        "kind": "ok" if matched else "watermark_value_mismatch",
        "expr": expr,
        "display": display,
        "expected": expected_val,
        "actual": display,
        "detail": f"expected {expected_val!r} from {expr}, prose has {display!r}",
    }


def verify_watermarks(
    markdown_text: str,
    *,
    full: Mapping[str, Any] | None = None,
    core: Mapping[str, Any] | None = None,
    snapshot: Mapping[str, Any] | None = None,
    receipt: Mapping[str, Any] | None = None,
    receipt_block: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    chunk_texts: Mapping[str, str] | None = None,
    declared: Mapping[str, set[str]] | None = None,
) -> dict[str, Any]:
    """Extract and deterministically verify all provedown watermarks in `markdown_text`."""
    watermarks = extract_watermarks(markdown_text)
    if declared is None and any(wm["expr"].startswith("schema:") for wm in watermarks):
        from data_sheets_schema.report_claims import declared_slots
        declared = declared_slots()
    effective_receipt = receipt if receipt is not None else receipt_block
    context: dict[str, Any] = {
        "full": full,
        "core": core,
        "snapshot": snapshot,
        "receipt": effective_receipt,
        "manifest": manifest,
        "chunk_texts": chunk_texts,
        "declared": declared,
    }
    results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    verified_count = 0
    for wm in watermarks:
        if "parse_error" in wm:
            res = {
                "verified": False,
                "kind": "watermark_malformed",
                "detail": wm["parse_error"],
            }
        else:
            res = evaluate_watermark(wm["expr"], wm["display"], context)
        entry = {**wm, **res}
        results.append(entry)
        if res["verified"]:
            verified_count += 1
        else:
            findings.append({
                "kind": res["kind"],
                "section": "provedown_watermarks",
                "slot": wm["expr"],
                "record": wm["expr"].split(":", 1)[0] if ":" in wm["expr"] else "report",
                "detail": res["detail"],
                "claim": wm["raw"],
                "line": wm["line"],
            })
    return {
        "checked": True,
        "instrument": PROVEDOWN_INSTRUMENT,
        "total": len(watermarks),
        "verified": verified_count,
        "mismatched": len(watermarks) - verified_count,
        "watermarks": results,
        "findings": findings,
    }
