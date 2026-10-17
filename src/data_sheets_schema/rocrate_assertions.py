"""Pure, root-scoped assertion rules for the static crate mapper (#2915).

The caller selects the root. These helpers never search other Dataset nodes
for a missing root property, infer approval/compliance, or mutate the graph.
Each returns ``(value_or_None, detail)``. Details describe decisions; the
caller retains complete original assertions in its raw provenance sidecar.

Additional reads are explicit: human subjects reads humanSubjectResearch,
humanSubjects, humanSubjectExemption, irb, and irbProtocolId; imputation reads
the two imputation keys below; parents reads isPartOf. Graph reads are only
explicit irb references and the identity/type/parent edges of named parents.
"""

from __future__ import annotations

import copy
import json
from typing import Any


IMPUTATION_KEYS = ("rai:dataImputationProtocol", "rai:imputationProtocol")
HUMAN_KEYS = ("humanSubjectResearch", "humanSubjects", "humanSubjectExemption",
              "irb", "irbProtocolId")
_TYPE_NAMES = {
    "Dataset": frozenset(("Dataset", "schema:Dataset", "http://schema.org/Dataset",
                          "https://schema.org/Dataset", "evi:Dataset",
                          "https://w3id.org/EVI#Dataset")),
    "Organization": frozenset(("Organization", "schema:Organization",
                               "http://schema.org/Organization",
                               "https://schema.org/Organization")),
}


def _present(value: Any) -> bool:
    # False is a present assertion. Never use truthiness for source values.
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _literal(value: Any) -> str:
    """Preserve strings verbatim and other JSON values with their types."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _identity(value: Any) -> str | None:
    identifier = value.get("@id") if isinstance(value, dict) else value
    return identifier if isinstance(identifier, str) and identifier.strip() else None


def _index(graph: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for node in graph:
        if isinstance(node, dict) and (identifier := _identity(node)) is not None:
            index.setdefault(identifier, []).append(node)
    return index


def _typed(node: dict, kind: str) -> bool:
    types = node.get("@type", [])
    if not isinstance(types, list):
        types = [types]
    return any(isinstance(t, str) and t in _TYPE_NAMES[kind] for t in types)


def _explicit_boolean(value: Any) -> bool | None:
    """Only native booleans or a whole Yes/No token; no numeric truthiness."""
    if type(value) is bool:
        return value
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in ("yes", "no"):
            return token == "yes"
    return None


def _boolean_assertion(value: Any) -> bool | None:
    items = value if isinstance(value, list) else [value]
    normalized = [_explicit_boolean(item) for item in items]
    if normalized and all(item is not None for item in normalized):
        first = normalized[0]
        if all(item is first for item in normalized):
            return first
    return None


def _irb_organization(value: Any, index: dict[str, list[dict]]) -> tuple[dict | None, str]:
    """Read an inline Organization or a unique, explicitly typed reference."""
    if not isinstance(value, (str, dict)):
        return None, "irb has no supported Organization shape"
    identifier = _identity(value)
    if identifier is not None and len(index.get(identifier, [])) > 1:
        return None, "irb reference has duplicate graph identities"
    if isinstance(value, dict) and "@type" in value:
        if not _typed(value, "Organization"):
            return None, "irb inline value is not explicitly an Organization"
        matches = index.get(identifier, []) if identifier is not None else []
        if matches and "@type" in matches[0] and not _typed(matches[0], "Organization"):
            return None, "inline and graph irb types disagree"
        if (matches and _present(value.get("name")) and _present(matches[0].get("name"))
                and value["name"] != matches[0]["name"]):
            return None, "inline and graph irb names disagree; neither name selected"
        return value, "inline Organization"
    matches = index.get(identifier, []) if identifier is not None else []
    if len(matches) != 1 or not _typed(matches[0], "Organization"):
        return None, "irb reference has no unique explicit Organization"
    return matches[0], "referenced Organization"


def human_subject_record(root: dict | None, graph: list[dict]) -> tuple[dict | None, str]:
    """Keep the root's assertions in one HumanSubjectResearch object.

    The complete original values are source-labeled in description. A single
    unambiguous research Yes/No (including a list of agreeing explicit tokens)
    may additionally fill involves_human_subjects. Opposing explicit tokens
    under humanSubjects suppress that normalization; they remain separate
    assertions. A uniquely resolved Organization may supply ethics_review_board.
    No protocol identifier or review narrative is treated as approval.
    """
    if not isinstance(root, dict):
        return None, "no selected crate root"
    assertions = [(key, root[key]) for key in HUMAN_KEYS
                  if key in root and _present(root[key])]
    if not assertions:
        return None, "selected root has no human-subject assertions"
    record: dict[str, Any] = {
        "description": "\n".join(f"Source {key}: {_literal(value)}"
                                 for key, value in assertions),
    }
    notes = ["preserved root assertions: " + ", ".join(key for key, _ in assertions)]
    research = _boolean_assertion(root.get("humanSubjectResearch"))
    subject_values = root.get("humanSubjects")
    subject_values = subject_values if isinstance(subject_values, list) else [subject_values]
    opposition = research is not None and any(
        (explicit := _explicit_boolean(value)) is not None and explicit is not research
        for value in subject_values)
    if opposition:
        notes.append("opposing explicit humanSubjectResearch and humanSubjects "
                     "assertions retained; involves_human_subjects left unset")
    elif research is not None:
        record["involves_human_subjects"] = research
        notes.append("humanSubjectResearch explicit Yes/No or boolean normalized")
    elif _present(root.get("humanSubjectResearch")):
        notes.append("humanSubjectResearch is not an unambiguous Yes/No or boolean; "
                     "involves_human_subjects left unset")
    if _present(root.get("irb")):
        index = _index(graph)
        values = root["irb"] if isinstance(root["irb"], list) else [root["irb"]]
        names = []
        for value in values:
            identifier = _identity(value)
            matches = index.get(identifier, []) if identifier is not None else []
            if len(matches) == 1 and matches[0] != value:
                # Preserve conflicting referenced assertions without choosing
                # them as the board's name or silently hiding their content.
                record["description"] += "\nSource irb referenced entity: " + _literal(matches[0])
            organization, note = _irb_organization(value, index)
            notes.append(note)
            if organization is not None:
                name = organization.get("name")
                if isinstance(name, str) and name.strip() and name not in names:
                    names.append(name)
        if len(names) == 1:
            record["ethics_review_board"] = names[0]
        elif len(names) > 1:
            notes.append("multiple board names retained in description; singular "
                         "ethics_review_board left unset")
    notes.append("review and protocol assertions do not establish approval")
    return record, "; ".join(notes)


def imputation_values(root: dict | None) -> tuple[Any, str]:
    """Return canonical then legacy values, preserving distinct assertions.

    Each source list contributes its elements in order. Nested values remain
    intact for the caller's schema handling and raw evidence retention. Only
    exact JSON-value duplicates are removed; boolean and numeric types differ.
    """
    if not isinstance(root, dict):
        return None, "no selected crate root"
    values = []
    seen: set[str] = set()
    used = []
    for key in IMPUTATION_KEYS:
        if key not in root or not _present(root[key]):
            continue
        used.append(key)
        items = root[key] if isinstance(root[key], list) else [root[key]]
        for item in items:
            signature = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if signature not in seen:
                seen.add(signature)
                values.append(copy.deepcopy(item))
    if not used:
        return None, "selected root has neither imputation source key"
    note = "imputation assertions from " + ", ".join(used)
    if len(used) > 1:
        note += "; canonical and legacy assertions combined without overwriting; exact duplicates removed"
    return values, note + "; source statements do not imply an applied method"


def _with_parent_edges(inline: dict, graph_node: dict) -> dict:
    """An inline assertion cannot hide a graph assertion that creates a cycle."""
    merged = {**graph_node, **inline}
    if "isPartOf" in inline and "isPartOf" in graph_node:
        graph_edges = graph_node["isPartOf"]
        inline_edges = inline["isPartOf"]
        merged["isPartOf"] = (
            (graph_edges if isinstance(graph_edges, list) else [graph_edges])
            + (inline_edges if isinstance(inline_edges, list) else [inline_edges]))
    return merged


def _parent_node(value: Any, index: dict[str, list[dict]]) -> tuple[dict | None, str]:
    identifier = _identity(value)
    if identifier is None:
        return None, "parent has no explicit identifier"
    matches = index.get(identifier, [])
    if len(matches) > 1:
        return None, "parent identity is duplicated in graph"
    if isinstance(value, dict) and "@type" in value:
        if not _typed(value, "Dataset"):
            return None, "parent is not explicitly typed Dataset"
        if matches and "@type" in matches[0] and not _typed(matches[0], "Dataset"):
            return None, "inline and graph parent types disagree"
        # Graph edges remain relevant even when the inline assertion gives its type.
        return _with_parent_edges(value, matches[0] if matches else {}), "explicit inline Dataset"
    if len(matches) == 1 and _typed(matches[0], "Dataset"):
        return (_with_parent_edges(value, matches[0]) if isinstance(value, dict)
                else matches[0]), "explicit graph Dataset"
    return None, "parent has no unique explicitly typed Dataset"


def _parent_graph_problem(node: dict, root_id: str,
                          index: dict[str, list[dict]]) -> str | None:
    """Reject cycles or ambiguous ancestor identities in the supplied graph.

    Iterative traversal avoids recursion limits; unresolved external ancestors
    are leaves, not guessed types. Inline isPartOf objects also supply edges.
    Refuse after 10,000 visits rather than silently accept an unverified path.
    """
    visiting: set[str] = set()
    stack = [(node, False)]
    visits = 0
    while stack:
        current, leaving = stack.pop()
        identifier = _identity(current)
        if identifier is None:
            continue
        if leaving:
            visiting.discard(identifier)
            continue
        if identifier == root_id or identifier in visiting:
            return "parent path contains a cycle or reaches the selected root"
        visits += 1
        if visits > 10_000:
            return "parent ancestry exceeds the 10000-visit verification limit"
        visiting.add(identifier)
        stack.append((current, True))
        edges = current.get("isPartOf", [])
        edges = edges if isinstance(edges, list) else [edges]
        for edge in reversed(edges):
            target = _identity(edge)
            if target is None:
                continue
            if target == root_id:
                return "parent path contains a cycle or reaches the selected root"
            matches = index.get(target, [])
            if len(matches) > 1:
                return "parent ancestry has duplicate graph identities"
            if isinstance(edge, dict):
                child = _with_parent_edges(edge, matches[0] if matches else {})
            elif matches:
                child = matches[0]
            else:
                continue
            stack.append((child, False))
    return None


def typed_parent_values(root: dict | None, graph: list[dict]) -> tuple[Any, str]:
    """Return unique parent references supported by explicit Dataset types.

    Only the selected root's isPartOf is read. Organization/Project types are
    not promoted to Dataset; URI spelling is never evidence of a type.
    Self-links, cycles and ambiguous identities are refused with reasons.
    """
    if not isinstance(root, dict) or not _present(root.get("isPartOf")):
        return None, "selected root has no isPartOf assertion"
    root_id = _identity(root)
    if root_id is None:
        return None, "selected root has no identifier; parent identity cannot be checked"
    index = _index(graph)
    values = root["isPartOf"] if isinstance(root["isPartOf"], list) else [root["isPartOf"]]
    accepted = []
    seen: set[str] = set()
    notes = []
    for position, value in enumerate(values):
        node, reason = _parent_node(value, index)
        if node is None:
            notes.append(f"isPartOf[{position}] refused: {reason}")
            continue
        problem = _parent_graph_problem(node, root_id, index)
        if problem is not None:
            notes.append(f"isPartOf[{position}] refused: {problem}")
            continue
        identifier = _identity(node)
        if identifier not in seen:
            seen.add(identifier)
            accepted.append({"@id": identifier})
            notes.append(f"isPartOf[{position}] accepted: {reason}")
        else:
            notes.append(f"isPartOf[{position}] duplicate reference subsumed")
    return accepted or None, "; ".join(notes)
