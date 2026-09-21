"""Protocol-v4 whole-member proofs, bound to the exact original artifact.

These signatures establish structural correspondence, not semantic identity.
Legacy relationship proofs deliberately remain in evidence_assertions.
"""
from __future__ import annotations

import hashlib
import math
import re


MODE = "anonymous_structure_v1"
RULE_KEYS = {"path", "match", "original_full_sha256"}


def _same_tree(left, right, ancestors=frozenset()):
    """Bind caller-parsed YAML to raw YAML without Python's bool/int aliasing.

    This is an exact parsed-value comparison, not a structural signature:
    narrative text and YAML-only scalars outside the affected lists still bind.
    """
    if type(left) is not type(right):
        return False
    if isinstance(left, (dict, list)):
        pair = (id(left), id(right))
        if pair in ancestors:
            raise ValueError("cyclic original artifact is ambiguous")
        ancestors = ancestors | {pair}
        if isinstance(left, list):
            return len(left) == len(right) and all(
                _same_tree(a, b, ancestors) for a, b in zip(left, right))
        if len(left) != len(right):
            return False
        # String keys are required separately in every affected member. Here
        # preserve the types of YAML keys elsewhere in the original too.
        keyed = {(type(key), key): value for key, value in right.items()}
        return all((type(key), key) in keyed and
                   _same_tree(value, keyed[(type(key), key)], ancestors)
                   for key, value in left.items())
    # SafeLoader's scalar representations distinguish signed zero and exact
    # date/time representations; unlike == they also handle NaN deterministically.
    return repr(left) == repr(right)


def _signature(value, narrative_fields, ancestors=frozenset()):
    """Return a typed, hashable structure and whether it has a usable anchor."""
    kind = type(value)
    if kind is dict or kind is list:
        if id(value) in ancestors:
            raise ValueError("cyclic anonymous relationship structure is ambiguous")
        ancestors = ancestors | {id(value)}
        if kind is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("anonymous relationship mappings require string keys")
            children = [(key, _signature(child, narrative_fields, ancestors))
                        for key, child in sorted(value.items())
                        if not (key in narrative_fields and
                                (child is None or type(child) is str))]
            return ("dict", tuple((key, sig) for key, (sig, _) in children)), any(
                anchored for _, (_, anchored) in children)
        children = [_signature(child, narrative_fields, ancestors) for child in value]
        return ("list", tuple(sig for sig, _ in children)), any(
            anchored for _, anchored in children)
    if value is None:
        return ("null",), False
    if kind is bool:
        return ("bool", value), True
    if kind is int:
        return ("int", value), True
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("anonymous relationship scalars must be finite")
        return ("float", value.hex()), True
    if kind is str:
        return ("str", value), bool(value.strip())
    raise ValueError("anonymous relationships require JSON scalar types, objects and lists")


def _contains_identity(value, identity_fields):
    # Called only after the typed signature has rejected cycles/unsupported types.
    if isinstance(value, dict):
        return bool(identity_fields.intersection(value)) or any(
            _contains_identity(child, identity_fields) for child in value.values())
    if isinstance(value, list):
        return any(_contains_identity(child, identity_fields) for child in value)
    return False


def _container(record, tokens):
    """The initial mode never follows an indexed ancestor."""
    current = record
    for token in tokens:
        if type(current) is not dict or token not in current:
            raise ValueError("anonymous whole-member paths require existing dictionary-only ancestors")
        current = current[token]
    if type(current) is not list:
        raise ValueError("anonymous whole-member container must remain an explicit list")
    return current


def check(audit, original, final, *, original_raw):
    """Return handled finding indexes and v4 findings; never change inputs.

    The raw original is mandatory authority. A claimed digest plus dictionaries
    alone is not an exact-artifact proof. The caller's parsed original must
    agree with these bytes, which are parsed with the ordinary duplicate guard.
    """
    from data_sheets_schema import evidence_assertions as evidence

    rows = audit.get("findings", [])
    handled = {i for i, row in enumerate(rows)
               if isinstance(row, dict) and isinstance(row.get("remove_relationship"), dict)
               and ({"match", "original_full_sha256"} & set(row["remove_relationship"]))}
    if not handled:
        return handled, []
    problems = []

    def problem(detail, index):
        problems.append(evidence._problem("evidence_contract", detail, finding=index))

    try:
        if type(original_raw) not in (str, bytes):
            raise ValueError("anonymous whole-member removal requires exact original_full raw bytes or text")
        raw = original_raw.encode("utf-8") if isinstance(original_raw, str) else original_raw
        bound_original = evidence.load_record(raw.decode("utf-8"))
        if not _same_tree(original, bound_original):
            raise ValueError("parsed original differs from exact original_full raw artifact")
        digest = hashlib.sha256(raw).hexdigest()
    except (ValueError, TypeError, UnicodeError, evidence.yaml.YAMLError) as error:
        for index in sorted(handled):
            problem(str(error), index)
        return handled, problems

    actions, groups = [], {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("remove_relationship"), dict):
            continue
        rule = row["remove_relationship"]
        try:
            tokens = tuple(evidence._tokens(rule.get("path")))
            actions.append((index, tokens))
            if index not in handled:
                continue
            if set(rule) != RULE_KEYS or rule.get("match") != MODE:
                raise ValueError("anonymous removal needs exactly path, match=anonymous_structure_v1 and original_full_sha256")
            claimed = rule["original_full_sha256"]
            if (type(claimed) is not str or not re.fullmatch(r"[0-9a-f]{64}", claimed)
                    or claimed != digest):
                raise ValueError("anonymous removal digest differs from exact original_full bytes")
            if len(tokens) < 2 or not re.fullmatch(r"0|[1-9][0-9]*", tokens[-1]):
                raise ValueError("anonymous removal must select an original list member")
            container = tokens[:-1]
            members = _container(bound_original, container)
            selected = int(tokens[-1])
            if selected >= len(members):
                raise ValueError("anonymous removal target is absent from the original")
            groups.setdefault(container, []).append((index, selected))
        except (ValueError, TypeError, KeyError) as error:
            if index in handled:
                problem(str(error), index)
            # Legacy declarations retain the legacy parser and its diagnostics.

    for container, selections in groups.items():
        first = selections[0][0]
        try:
            selected = {position for _, position in selections}
            if len(selected) != len(selections):
                raise ValueError("duplicate anonymous whole-member removal path")
            group_indexes = {index for index, _ in selections}
            for index, path in actions:
                if index in group_indexes:
                    continue
                if path[:len(container)] == container or container[:len(path)] == path:
                    raise ValueError("anonymous whole-member removals cannot overlap other actions in their container")
            members = _container(bound_original, container)
            if any(type(member) is not dict for member in members):
                raise ValueError("anonymous relationship list members must be objects")
            structured = [_signature(member, evidence.NARRATIVE_FIELDS) for member in members]
            if not all(anchor for _, anchor in structured):
                raise ValueError("every original relationship member needs a nonempty structural anchor")
            signatures = [signature for signature, _ in structured]
            if len(set(signatures)) != len(signatures):
                raise ValueError("original relationship member structures are duplicated or ambiguous")
            for _, position in selections:
                if _contains_identity(members[position], evidence.IDENTITY_FIELDS):
                    raise ValueError("anonymous removal target must have no own or nested identity fields")
            final_members = _container(final, container)
            positions = {signature: i for i, signature in enumerate(signatures)}
            matched = set()
            for member in final_members:
                if type(member) is not dict:
                    raise ValueError("final anonymous relationship list members must be objects")
                signature, _ = _signature(member, evidence.NARRATIVE_FIELDS)
                if signature not in positions or positions[signature] in matched:
                    raise ValueError("relationship survivor is new, changed, duplicated or reintroduced")
                matched.add(positions[signature])
            if set(range(len(members))) - selected - matched:
                raise ValueError("an unselected original relationship member disappeared")
            # Admission checks original against itself first. Valid retained
            # targets are explicit retained findings, then projected away and
            # checked again. Actual final validation requires zero findings.
            for index, position in selections:
                if position in matched:
                    problems.append(evidence._problem("unsupported_relationship_retained",
                        "the audit rejected this relationship, but the final record still asserts it; a disclaimer does not remove it",
                        finding=index, path=rows[index]["remove_relationship"]["path"]))
        except (ValueError, TypeError, KeyError) as error:
            problem(str(error), first)
    return handled, problems
