#!/usr/bin/env python3
"""K1 v2/#5155/#5157, 2026-10-26: disjoint request-byte decomposition.

Input: an in-memory offline canonical request. Output: component byte counts,
pins and common-prefix metadata; no provider calls or production mutations.
Counts are serialized byte allocations, never tokenizer measurements. Nested
JSON strings are decoded only when canonical round-trip identity is exact.
"""
import copy
import hashlib
import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


CATEGORIES = ("bundle", "records", "schema_context", "manifest_context",
              "receipt_evidence", "worker_outputs", "audit_carry",
              "rejected_report", "worker_inventory", "source_review_inventory", "instructions", "transcript")
KEY_CATEGORY = {
    "bundle": "bundle", "original_full": "records", "original_core": "records",
    "record": "records", "record_yaml": "records", "full_record": "records", "core_record": "records",
    "schema": "schema_context", "classes": "schema_context", "owners": "schema_context",
    "manifest": "manifest_context", "context": "manifest_context",
    "registered_provenance": "manifest_context", "receipt": "receipt_evidence", "receipt_yaml": "receipt_evidence",
    "receipt_carry": "receipt_evidence", "unsupported_audit_candidates": "receipt_evidence",
    "workers": "worker_outputs", "proposal_index": "worker_outputs", "index": "worker_outputs",
    "omission_response": "audit_carry", "omission_check": "audit_carry",
    "inventory": "worker_inventory", "assignment": "worker_inventory",
    "protocol": "instructions", "output_contract": "instructions", "policy": "instructions",
    "transcript": "transcript",
}
NESTED_JSON_KEYS = {"shared_context", "stage"}
TYPED_HEADER = "# Exact typed stage request\n\n"


def text_category(text):
    head = text.split("\n", 1)[0].lower()
    if head.startswith("# declared input bundle"):
        return "bundle"
    if head.startswith("# target class") or "captured schema owners" in head:
        return "schema_context"
    if head in {"# original full record", "# original core record", "# completed full record",
                "# completed core record", "# reconciled full record"}:
        return "records"
    if head.startswith("# audit findings"):
        return "audit_carry"
    if head.startswith("# reconciliation report as written"):
        return "rejected_report"
    if head.startswith("# receipt completion candidates"):
        return "receipt_evidence"
    if head.startswith("# required source-review inventory"):
        return "source_review_inventory"
    if "captured generation scope" in head or any(word in head for word in
            ("source ranking", "source naming", "source scope", "source manifest")):
        return "manifest_context"
    return "instructions"


def empty(value):
    if isinstance(value, str):
        return ""
    if isinstance(value, dict):
        return {}
    if isinstance(value, list):
        return []
    return value


def strip_json(value, category):
    """Clear one disjoint category, preserving parent/sibling identity fields."""
    if isinstance(value, list):
        return [strip_json(item, category) for item in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        assigned = KEY_CATEGORY.get(key)
        if assigned:
            out[key] = empty(item) if assigned == category else item
        elif key in NESTED_JSON_KEYS and isinstance(item, str) and item.startswith("{"):
            nested = json.loads(item)
            suffix = "\n" if item.endswith("\n") else ""
            if canonical(nested).decode() + suffix != item:
                raise ValueError("nested JSON is not canonical; no byte allocation claimed")
            out[key] = canonical(strip_json(nested, category)).decode() + suffix
        else:
            out[key] = strip_json(item, category)
    return out


def strip_text(text, category):
    if text.startswith(TYPED_HEADER):
        prefix, raw = TYPED_HEADER, text[len(TYPED_HEADER):]
    elif text.startswith("{"):
        prefix, raw = "", text
    else:
        return "" if text_category(text) == category else text
    try:
        value = json.loads(raw)
    except ValueError:
        return "" if text_category(text) == category else text
    if canonical(value).decode() != raw:
        # A formatted JSON block is retained in residual rather than silently
        # reformatting its original byte count.
        return text
    return prefix + canonical(strip_json(value, category)).decode()


def summarize_payload(payload):
    raw = canonical(payload)
    current = copy.deepcopy(payload)
    counts = {}
    for category in CATEGORIES:
        before = len(canonical(current))
        if category == "instructions" and isinstance(current.get("system"), str):
            current["system"] = ""
        for message in current.get("messages", []):
            content = message.get("content")
            if message.get("role") == "assistant":
                if category == "transcript":
                    message["content"] = "" if isinstance(content, str) else []
                continue
            if isinstance(content, str):
                message["content"] = strip_text(content, category)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        part["text"] = strip_text(part["text"], category)
        delta = before - len(canonical(current))
        if delta < 0:
            raise ValueError("component stripping expanded a payload")
        counts[category] = delta
    counts["residual_structure"] = len(canonical(current))
    assert sum(counts.values()) == len(raw)
    return {"payload_bytes": len(raw), "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "component_bytes": counts,
            "basis": "Disjoint sequential byte removal including nested JSON escaping; residual retained."}


def common_worker_prefix(payloads):
    """Exact current-wire common content blocks, stopping at first variation.

    This measures existing complete message blocks, not a hypothetical new
    prefix. Output caps, identities and JSON framing are not cache savings.
    """
    if not payloads:
        return {"status": "unknown", "reason": "no worker requests"}
    for p in payloads:
        if (len(p.get("messages", [])) != 1 or p["messages"][0].get("role") != "user"
                or not isinstance(p["messages"][0].get("content"), list) or "tools" in p):
            raise ValueError("current-prefix measurement requires one plain user worker message")
    if any(p.get("model") != payloads[0].get("model") for p in payloads):
        raise ValueError("current-prefix measurement requires one selected model")
    if any(p.get("system") != payloads[0].get("system") for p in payloads):
        return {"status": "measured", "common_blocks": 0, "serialized_prefix_proxy_bytes": 0}
    rows = [p["messages"][0]["content"] for p in payloads]
    common = []
    for items in zip(*rows):
        if any(item != items[0] for item in items[1:]):
            break
        common.append(items[0])
    material = {"system": payloads[0].get("system"), "content": common}
    raw = canonical(material)
    return {"status": "measured", "worker_count": len(payloads),
            "common_blocks": len(common), "serialized_prefix_proxy_bytes": len(raw),
            "text_only_utf8_bytes": len((payloads[0].get("system") or "").encode()) +
                sum(len(block.get("text", "").encode()) for block in common),
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "single_worker_no_cross_worker_evidence": len(payloads) == 1,
            "basis": "Exact leading full content blocks, serialized in a proxy wrapper; not tokenized or exact billable prefix size. Cache eligibility still depends on route and TTL."}
