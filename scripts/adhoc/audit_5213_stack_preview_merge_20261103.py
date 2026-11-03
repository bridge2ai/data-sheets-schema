#!/usr/bin/env python3
"""Audit added and removed lines of PR #5213 preview merge 1 (2026-11-03).

Inputs: pinned local Git parents/base/merge, optional explicit candidate
dispositions, and an optional path restriction for the one-file canary.
Outputs: a fresh external directory containing JSON evidence and contextual
parent/merge diffs. This script never changes Git state or imports package code.
Line preservation is positional; semantic disposition remains a review decision.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BASE = "ddfd45c3b520d37da247cf899401437794880e0c"
PARENTS = {
    "d76": "9a76ebd5634d57ad33f6a69f67b3eb4a8fe3def8",
    "bc1_g2": "72324b4cab74156c86b6bde5cea14d2e49d16595",
}
MERGE = "66145c56d4654051d0d593765bbfc3d40d63b213"
CONFLICT_PATHS = (
    "src/data_sheets_schema/api_runner.py",
    "src/data_sheets_schema/typed_audit_runtime.py",
    "tests/test_profiles.py",
)
DISPOSITIONS = frozenset({
    "authorized_conflict_resolution", "inherited_opposite_parent_change",
    "intentional_removal", "intentional_relocation",
})


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
               GIT_TERMINAL_PROMPT="0")
    command = ["git", "--no-replace-objects", "-c", "protocol.allow=never",
               "-C", str(ROOT), *args]
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise ValueError(f"Git read failed ({result.returncode}): {args!r}: "
                         + result.stderr.decode(errors="replace"))
    return result.stdout


def producer():
    if git("status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("a clean, committed producer is required")
    return {
        "head": git("rev-parse", "HEAD").decode().strip(),
        "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "script_sha256": digest(Path(__file__).read_bytes()),
    }


def tree(ref):
    entries = {}
    for row in git("ls-tree", "-r", "-z", "--full-tree", ref).split(b"\0"):
        if not row:
            continue
        identity, path = row.split(b"\t", 1)
        mode, kind, oid = identity.decode("ascii").split()
        name = path.decode("utf-8", errors="surrogateescape")
        entries[name] = {"mode": mode, "kind": kind, "oid": oid}
    return entries


def scope_rows(raw, path, required=False):
    """Return lexical AST scope identities, never a semantic equivalence claim."""
    lines = raw.splitlines(keepends=True)
    result = ["<module>"] * len(lines)
    if not path.endswith(".py"):
        return result, "not_python"
    try:
        parsed = ast.parse(raw, filename=path)
    except (SyntaxError, ValueError, UnicodeError) as exc:
        if required:
            raise ValueError(f"required contextual file does not parse: {path}: {exc}") from exc
        return [None] * len(lines), f"unavailable: {type(exc).__name__}"
    seen = Counter()

    def visit(node, enclosing):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            label = ("class:" if isinstance(node, ast.ClassDef) else "function:") + node.name
            qualified = enclosing + (label,)
            seen[qualified] += 1
            instance = qualified + ((f"occurrence:{seen[qualified]}",) if seen[qualified] > 1 else ())
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            for number in range(start - 1, node.end_lineno):
                result[number] = "/".join(instance)
            enclosing = instance
        for child in ast.iter_child_nodes(node):
            visit(child, enclosing)

    visit(parsed, ())
    return result, "parsed"


def equal_map(before, after):
    mapping = {}
    for block in difflib.SequenceMatcher(None, before, after, autojunk=False).get_matching_blocks():
        for offset in range(block.size):
            old, new = block.a + offset, block.b + offset
            if before[old] != after[new]:
                raise ValueError("invalid equal-line mapping")
            mapping[old] = new
    return mapping


def added_indices(base, side):
    added = set()
    for action, _a, _b, start, stop in difflib.SequenceMatcher(
            None, base, side, autojunk=False).get_opcodes():
        if action in ("insert", "replace"):
            added.update(range(start, stop))
    return added


def context(lines, number, radius=3):
    return [{"line": index + 1, "text": lines[index].decode("utf-8", errors="surrogateescape")}
            for index in range(max(0, number - radius), min(len(lines), number + radius + 1))]


def candidate_id(candidate):
    # Stable across evidence destinations. Actual source coordinates and bytes
    # distinguish repeated identical lines; no wildcard disposition is accepted.
    raw = json.dumps(candidate, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":")).encode()
    return digest(raw)


def candidate_line(side, path, index, raw, scope, reason, since_base, mapped):
    identity = {"side": side, "parent": PARENTS[side], "path": path,
                "parent_line": index + 1, "line_sha256": digest(raw),
                "scope": scope, "reason": reason, "added_since_base": since_base,
                "mapped_merge_line": None if mapped is None else mapped + 1}
    return {"id": candidate_id(identity), **identity,
            "text": raw.decode("utf-8", errors="surrogateescape")}


def audit_text(side, path, base, parent, merged, detailed):
    before, after, origin = (raw.splitlines(keepends=True) for raw in (parent, merged, base))
    added = added_indices(origin, before)
    mapping = equal_map(before, after)
    old_scopes, old_parse = scope_rows(parent, path, required=detailed)
    new_scopes, new_parse = scope_rows(merged, path, required=detailed)
    source_counts, result_counts = Counter(before), Counter(after)
    source_scope_counts = Counter(zip(old_scopes, before))
    result_scope_counts = Counter(zip(new_scopes, after))
    by_text = defaultdict(list)
    for index, value in enumerate(after):
        by_text[value].append(index)
    rows, candidates = [], []
    preserved_added = 0
    checked = range(len(before)) if detailed else sorted(added)
    for index in checked:
        target = mapping.get(index)
        same_scope = target is not None and old_scopes[index] == new_scopes[target]
        # Contextual assurance is mandatory for the three conflicted Python
        # files. Elsewhere equal-block positions are retained but scope parsing
        # availability remains explicit in the evidence.
        preserved = target is not None and (same_scope or not detailed)
        if preserved:
            if index in added:
                preserved_added += 1
            if detailed and index in added:
                rows.append({"parent_line": index + 1, "merge_line": target + 1,
                             "scope": old_scopes[index], "line_sha256": digest(before[index]),
                             "text": before[index].decode("utf-8", errors="surrogateescape"),
                             "status": "preserved_at_equal_block_position_in_same_scope"})
            continue
        reason = "not_mapped_by_equal_blocks" if target is None else "mapped_to_different_ast_scope"
        row = candidate_line(side, path, index, before[index], old_scopes[index], reason,
                             index in added, target)
        matches = by_text[before[index]]
        row.update({
            "parent_context": context(before, index),
            "mapped_merge_context": [] if target is None else context(after, target),
            "same_text_merge_locations": [{"line": number + 1, "scope": new_scopes[number]}
                                           for number in matches],
            "multiplicity": {
                "parent_file": source_counts[before[index]],
                "merge_file": result_counts[before[index]],
                "parent_scope": source_scope_counts[(old_scopes[index], before[index])],
                "merge_same_scope": result_scope_counts[(old_scopes[index], before[index])],
            },
            "disposition": None,
        })
        candidates.append(row)
        if detailed and index in added:
            rows.append({"parent_line": index + 1, "scope": old_scopes[index],
                         "line_sha256": digest(before[index]), "status": "candidate",
                         "candidate_id": row["id"]})
    added_candidates = sum(row["added_since_base"] for row in candidates)
    if preserved_added + added_candidates != len(added):
        raise ValueError(f"added-line occurrence accounting differs: {side}:{path}")
    if detailed and len(rows) != len(added):
        raise ValueError(f"detailed added-line roster is incomplete: {side}:{path}")
    # A multiplicity deficit is never hidden by text appearing somewhere else.
    deficits = [{"text": value.decode("utf-8", errors="surrogateescape"),
                 "line_sha256": digest(value), "parent_count": count,
                 "merge_count": result_counts[value]}
                for value, count in source_counts.items() if count > result_counts[value]]
    return {
        "path": path, "side": side, "status": "text_compared",
        "parent_sha256": digest(parent), "merge_sha256": digest(merged),
        "base_sha256": digest(base), "parent_lines": len(before), "merge_lines": len(after),
        "parent_scope_parse": old_parse, "merge_scope_parse": new_parse,
        "detailed_all_parent_line_comparison": detailed,
        "added_since_base": len(added), "added_preserved_at_positions": preserved_added,
        "added_candidates": added_candidates, "added_line_occurrences": rows if detailed else None,
        "file_multiplicity_deficits": deficits, "candidates": candidates,
    }


def load_dispositions(path):
    if path is None:
        return {}, None
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"format", "candidates"}:
        raise ValueError("dispositions must contain format and candidates only")
    if value["format"] != "pr5213_preview_merge1_dispositions_v1" or not isinstance(value["candidates"], dict):
        raise ValueError("unsupported disposition format")
    for identity, row in value["candidates"].items():
        if (not isinstance(identity, str) or len(identity) != 64
                or any(char not in "0123456789abcdef" for char in identity)
                or not isinstance(row, dict) or set(row) != {"classification", "reason", "evidence"}
                or row["classification"] not in DISPOSITIONS
                or not isinstance(row["reason"], str) or not row["reason"].strip()
                or not isinstance(row["evidence"], list) or not row["evidence"]
                or any(not isinstance(item, str) or not item.strip() for item in row["evidence"])):
            raise ValueError(f"invalid explicit disposition: {identity!r}")
    return value["candidates"], {"path": str(path), "sha256": digest(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--path", action="append", dest="paths",
                        help="Explicit restriction for a diagnostic canary; omit for full changed-tree audit.")
    parser.add_argument("--dispositions", type=Path,
                        help="Explicit per-candidate review decisions; not machine-verified semantic proof.")
    args = parser.parse_args()
    producer_before = producer()
    git("merge-base", "--is-ancestor", MERGE, producer_before["head"])
    actual_parents = git("show", "-s", "--format=%P", MERGE).decode().strip().split()
    if actual_parents != list(PARENTS.values()):
        raise ValueError("preview merge parents differ")
    if git("merge-base", *PARENTS.values()).decode().strip() != BASE:
        raise ValueError("preview merge base differs")
    output = args.output
    if (not output.is_absolute() or ".." in output.parts or output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True) != output.parent
            or output.is_relative_to(ROOT)):
        raise ValueError("fresh physical absolute output outside the worktree required")
    decisions, decisions_identity = load_dispositions(args.dispositions)
    trees = {name: tree(ref) for name, ref in {"base": BASE, **PARENTS, "merge": MERGE}.items()}
    changed = set()
    for side in PARENTS:
        changed.update(name for name in trees["base"].keys() | trees[side].keys()
                       if trees["base"].get(name) != trees[side].get(name))
    if args.paths:
        if len(set(args.paths)) != len(args.paths) or any(path not in changed for path in args.paths):
            raise ValueError("restricted paths must be distinct changed-tree members")
        paths = sorted(args.paths)
    else:
        paths = sorted(changed)
    cache = {}

    def content(entry):
        if entry is None:
            return b""
        if entry["kind"] != "blob":
            raise ValueError("requested text for a non-blob entry")
        oid = entry["oid"]
        if oid not in cache:
            cache[oid] = git("cat-file", "blob", oid)
        return cache[oid]

    file_rows, all_candidates, diffs = [], [], {}
    for path in paths:
        entries = {name: entries.get(path) for name, entries in trees.items()}
        detailed = path in CONFLICT_PATHS
        for side in PARENTS:
            parent, merged, base = entries[side], entries["merge"], entries["base"]
            row = {"path": path, "side": side, "entries": entries, "candidates": []}
            if detailed:
                filename = digest(path.encode())[:16] + f"-{side}-versus-merge.diff"
                diffs[filename] = git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                                      "--no-color", "--unified=3", PARENTS[side], MERGE, "--", path)
            if parent == merged and not detailed:
                row["status"] = "exact_parent_entry_retained_including_mode_and_blob"
            elif parent == base and not detailed:
                row["status"] = "no_side_changes_since_base"
            elif parent is None:
                row["status"] = "parent_has_no_entry"
                if base is not None and merged is not None:
                    identity = {"side": side, "path": path, "reason": "side_deletion_not_retained",
                                "parent": PARENTS[side], "entries": entries}
                    row["candidates"] = [{"id": candidate_id(identity), **identity, "disposition": None}]
            elif any(entry is not None and (entry["kind"] != "blob" or entry["mode"] != "100644")
                     for entry in (parent, merged, base)):
                # Preserve modes, executable bits, symlinks and gitlinks as exact
                # object identities; do not disguise them as parsed source lines.
                row["status"] = "nonregular_entry_comparison"
                if parent != merged:
                    identity = {"side": side, "path": path, "reason": "changed_nonregular_parent_entry",
                                "parent": PARENTS[side], "entries": entries}
                    row["candidates"] = [{"id": candidate_id(identity), **identity, "disposition": None}]
            else:
                raw_base, raw_parent, raw_merge = (content(entry) for entry in (base, parent, merged))
                if any(b"\0" in raw for raw in (raw_base, raw_parent, raw_merge)):
                    row["status"] = "binary_blob_comparison"
                    row["sha256"] = {"base": digest(raw_base), "parent": digest(raw_parent),
                                     "merge": digest(raw_merge)}
                    if parent != merged:
                        identity = {"side": side, "path": path, "reason": "changed_binary_parent_blob",
                                    "parent": PARENTS[side], "entries": entries}
                        row["candidates"] = [{"id": candidate_id(identity), **identity, "disposition": None}]
                else:
                    row.update(audit_text(side, path, raw_base, raw_parent, raw_merge, detailed))
            file_rows.append(row)
            all_candidates.extend(row["candidates"])
    ids = [row["id"] for row in all_candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate identity")
    extras = set(decisions) - set(ids)
    if extras:
        raise ValueError("dispositions name candidates outside this audit: " + repr(sorted(extras)))
    for row in all_candidates:
        row["disposition"] = decisions.get(row["id"])
    unattributed = [row["id"] for row in all_candidates if row["disposition"] is None]
    result = {
        "format": "pr5213_preview_merge1_line_audit_v1", "base": BASE, "parents": PARENTS,
        "merge": MERGE, "merge_tree": git("rev-parse", MERGE + "^{tree}").decode().strip(),
        "producer": producer_before, "command": sys.argv, "python_executable": sys.executable,
        "python_version": sys.version, "scope": "restricted_canary" if args.paths else "full_changed_tree",
        "paths": paths, "all_changed_paths": len(changed), "files": file_rows,
        "candidate_count": len(all_candidates), "unattributed_candidate_ids": unattributed,
        "all_candidates_have_explicit_dispositions": not unattributed,
        "dispositions": decisions_identity, "structural_verification_complete": True,
        "semantic_acceptance": "not_assessed_by_this_helper",
        "limits": [
            "Equal-block mappings preserve positions and multiplicity; matching text elsewhere never auto-accepts a candidate.",
            "Every added-line occurrence is accounted for in compared text; exact parent object identity preserves all bytes without enumerating lines.",
            "The three conflict files additionally compare every parent line within lexical AST scopes and retain all removed or relocated candidates, including blank lines.",
            "Other unchanged-base parent entries have no side additions; their deletions are covered by the opposite-parent review and the separate lead silent-revert audit.",
            "Dispositions are explicit review input, not independently proved semantic equivalence. No wildcard or generic text-match disposition is synthesized.",
            "Binary, gitlink, symlink and mode outcomes remain explicit object comparisons, not successful Python line checks.",
            "This audits the specified committed resolved merge, not the automatic conflict-marker tree generated by the separate lead script.",
            "No runtime test, provider operation, protected-file edit, or Git mutation is performed.",
        ],
    }
    if producer() != producer_before:
        raise ValueError("producer changed during read-only audit")
    if args.dispositions is not None and digest(args.dispositions.read_bytes()) != decisions_identity["sha256"]:
        raise ValueError("dispositions changed during audit")
    output.mkdir()
    if diffs:
        (output / "diffs").mkdir()
        for name, raw in sorted(diffs.items()):
            path = output / "diffs" / name
            with path.open("xb") as stream:
                stream.write(raw)
            if path.read_bytes() != raw:
                raise ValueError("persisted contextual diff differs")
    result["contextual_diff_sha256"] = {name: digest(raw) for name, raw in sorted(diffs.items())}
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    with (output / "audit.json").open("xb") as stream:
        stream.write(raw)
    if (output / "audit.json").read_bytes() != raw:
        raise ValueError("persisted audit differs")
    print(json.dumps({"output": str(output / "audit.json"), "sha256": digest(raw),
                      "scope": result["scope"], "candidates": len(all_candidates),
                      "unattributed": len(unattributed)}, sort_keys=True))
    return 1 if unattributed else 0


if __name__ == "__main__":
    raise SystemExit(main())
