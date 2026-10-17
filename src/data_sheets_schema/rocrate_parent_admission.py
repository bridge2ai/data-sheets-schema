"""Converter-only, explicit Dataset parent admission (#4047, #4946).

This policy does not change the static mapper. Evidence preserves parsed JSON
assertions, not source formatting or the truth of a claimed relationship.
"""
from __future__ import annotations

import json
import math

from data_sheets_schema.rocrate_assertions import (
    _TYPE_NAMES, _parent_graph_problem, _with_parent_edges,
)


_COMPATIBLE = frozenset(("ROCrate", "evi:ROCrate", "https://w3id.org/EVI#ROCrate",
                         "prov:Entity", "http://www.w3.org/ns/prov#Entity"))


def snapshot(value):
    """Detach exactly JSON-shaped evidence; never stringify unsupported input.

    Inspect only evidence this adapter actually consults. In particular this is
    not a new serialization/validation pass over unrelated crate properties.
    """
    active = set()
    pending = [(value, False)]
    while pending:
        item, leaving = pending.pop()
        kind = type(item)
        if leaving:
            active.remove(id(item))
        elif item is None or kind in (str, bool, int):
            continue
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("parent evidence contains a nonfinite number")
        elif kind is list or kind is dict:
            if id(item) in active:
                raise ValueError("parent evidence contains a cyclic value")
            active.add(id(item))
            pending.append((item, True))
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError("parent evidence contains a non-text JSON key")
                pending.extend((child, False) for child in item.values())
            else:
                pending.extend((child, False) for child in item)
        else:
            raise ValueError("parent evidence contains a non-JSON value")
    try:
        return json.loads(json.dumps(value, ensure_ascii=True, allow_nan=False))
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("parent evidence cannot be preserved as parsed JSON") from exc


def refusal_text(decision):
    return ("not placed in `parent_datasets`: " + decision["reason"]
            + "; parent_evidence="
            + json.dumps(decision, ensure_ascii=True, allow_nan=False, separators=(",", ":")))


def _type_state(node):
    if "@type" not in node:
        return "absent"
    raw = node["@type"]
    values = raw if type(raw) is list else [raw]
    if (not values or any(type(value) is not str for value in values)
            or any(value not in _TYPE_NAMES["Dataset"] | _COMPATIBLE for value in values)):
        return "unsupported"
    return "dataset" if any(value in _TYPE_NAMES["Dataset"] for value in values) else "unsupported"


class ParentAdmission:
    """One selected root, its exact graph identities, and detached decisions."""

    def __init__(self, root, graph, resolve):
        self.root_id = root.get("@id")
        self.root_index = next((i for i, node in enumerate(graph) if node is root), None)
        self.resolve = resolve
        self.index = {}
        self.positions = {}
        for i, node in enumerate(graph):
            if isinstance(node, dict) and type(node.get("@id")) is str and node["@id"].strip():
                self.index.setdefault(node["@id"], []).append(node)
                self.positions.setdefault(node["@id"], []).append(i)
        self.decisions = []

    def matches(self, identifier):
        return [{"pointer": "/@graph/" + str(i), "value": snapshot(node)}
                for i, node in zip(self.positions.get(identifier, []), self.index.get(identifier, []))]

    def prepare(self, value):
        if value is None or (type(value) is list and not value):
            return [], []
        is_list = type(value) is list
        items = value if is_list else [value]
        admitted = []
        for position, item in enumerate(items):
            pointer = "/@graph/" + str(self.root_index) + "/isPartOf"
            if is_list:
                pointer += "/" + str(position)
            decision = {"root_id": snapshot(self.root_id), "root_graph_index": self.root_index,
                "source_pointer": pointer, "occurrence": position, "raw": snapshot(item),
                "matches": [], "supplied_types": [], "ancestry": [],
                "decision": "refused", "reason": "", "reference_id": None, "output_id": None}
            self.decisions.append(decision)
            reason = self._admit(item, decision)
            if reason is None:
                decision.update(decision="admitted", reason="explicit Dataset under the converter policy")
                admitted.append(snapshot(item))
            else:
                decision["reason"] = reason
                admitted.append(None)
        return admitted, self.decisions

    def _admit(self, item, decision):
        if type(item) is not dict:
            return "literal or malformed entry, not an explicit @id reference"
        identifier = item.get("@id")
        if type(identifier) is not str or not identifier.strip():
            return "reference has no nonempty textual @id"
        decision["reference_id"] = identifier
        decision["matches"] = self.matches(identifier)
        matches = self.index.get(identifier, [])
        sources = [(decision["source_pointer"], item)] + [
            (row["pointer"], node) for row, node in zip(decision["matches"], matches)]
        decision["supplied_types"] = [{"pointer": pointer, "present": "@type" in node,
            "value": snapshot(node.get("@type"))} for pointer, node in sources]
        if identifier != identifier.strip():
            return "surrounding whitespace in parent @id is unsupported by the converter policy"
        if len(matches) > 1:
            return "parent identity has multiple exact graph matches"
        states = [_type_state(node) for _, node in sources]
        if "unsupported" in states:
            return "explicit type or co-type is unsupported by the finite converter policy"
        if "dataset" not in states:
            return "parent has no explicit Dataset type in inline or unique graph evidence"
        if "id" in item and (type(item["id"]) is not str
                or item["id"] not in (identifier, self.resolve(identifier))):
            return "inline id conflicts with the examined @id reference"
        if type(self.root_id) is not str or not self.root_id.strip() or self.root_index is None:
            return "selected root has no exact graph identity for parent ancestry verification"

        # Preserve the existing traversal and its fixed 10000-visit bound. The
        # recording adapter only snapshots graph nodes actually consulted by it.
        admission = self
        class EvidenceIndex(dict):
            def get(self, key, default=None):
                nodes = admission.index.get(key, default)
                decision["ancestry"].append({"reference_id": key, "matches": admission.matches(key)})
                return nodes

        node = _with_parent_edges(item, matches[0] if matches else {})
        return _parent_graph_problem(node, self.root_id, EvidenceIndex())
