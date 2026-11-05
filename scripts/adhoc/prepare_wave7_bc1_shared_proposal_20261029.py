"""Prepare BC1/A13/A14/D41 union as a diff only (Wave7 Task 5, 2026-10-29).

Inputs: immutable BC1, pre-BC1 and #5212 Git blobs plus unchanged local SG.
Outputs: notes/reviews/wave7_bc1_shared_generation_proposal_2026-10-29.{diff,json}.
Never writes protected source or pins and never imports production code.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/data_sheets_schema/shared_generation.py"
BASE = "f8c5ac73caba610d40c49aaceddb31ead3590a72"
BC1 = "b7e4d3ef76b8ceee2c1c9ee5fdabba9ff00949e6"
D41 = "20def9d63a3131ef9b56eca39b61fbf5f6aaab49"
BC1_SHA = "1c4436b5ea689fcd674c848a722dd9a86495692ad83401682f3d805f49acb6d6"
D41_SHA = "8c799066df941dd80d65ffdc23eee225f875383e046bbc1f88656f9897d01e47"


def git(*args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="file")
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=ROOT, env=env)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("proposal anchor does not occur exactly once: " + repr(before))
    return text.replace(before, after, 1)


HOOKS = (
    ('NAME = "shared_generation_v1"\n',
     'BC1_HOOK_VERSION = 1  # Explicit opt-in; dependencies and registrations must be rebuilt.\nNAME = "shared_generation_v1"\n'),
    ('def select(spec) -> dict | None:\n',
     'def select(spec) -> dict | None:\n    from .bc1_selection import validate_spec_mode\n    validate_spec_mode(spec)\n'),
    ('                   | ({"routing"} if version == 2 else set()), "shared registration")\n',
     '                   | ({"routing"} if version == 2 else set())\n                   | ({"bounded_carry"} if "bounded_carry" in value else set()), "shared registration")\n'),
    ('            raise ValueError("generation output cap leaves no input context")\n    return value\n',
     '            raise ValueError("generation output cap leaves no input context")\n    if "bounded_carry" in value:\n        from .bc1_selection import validate_registration as validate_bc1\n        validate_bc1(value, shared_version=version)\n    return value\n'),
    ('    captured = _context_capture(spec)\n',
     '    captured = _context_capture(spec)\n    from .bc1_selection import enabled as bc1_enabled\n    if bc1_enabled(spec):\n        from .bc1_context import schema_context as bc1_schema_context\n        return bc1_schema_context(captured, record)\n'),
    ('def plan(spec, settings):\n    """No client or historical-output discovery; dynamic sizes remain unknown."""\n',
     'def plan(spec, settings):\n    """No client or historical-output discovery; dynamic sizes remain unknown."""\n    from .bc1_selection import enabled as bc1_enabled\n    if bc1_enabled(spec):\n        from .bc1_registration import plan as bc1_plan\n        return bc1_plan(spec, settings)\n'),
)


def transform(text, *, remove=False):
    for index, (before, after) in enumerate(HOOKS):
        if remove:
            before, after = after, before
        if index == 4:
            # _context_capture is shared with another function. Restrict this
            # exact insertion to the schema_context AST segment alone.
            nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "schema_context"]
            if len(nodes) != 1:
                raise ValueError("schema_context function is not unique")
            node = nodes[0]
            lines = text.splitlines(keepends=True)
            segment = "".join(lines[node.lineno - 1:node.end_lineno])
            changed = once(segment, before, after)
            text = "".join(lines[:node.lineno - 1]) + changed + "".join(lines[node.end_lineno:])
        else:
            text = once(text, before, after)
    return text


def main():
    stem = ROOT / "notes/reviews/wave7_bc1_shared_generation_proposal_2026-10-29"
    output, proof = stem.with_suffix(".diff"), stem.with_suffix(".json")
    if output.exists() or proof.exists():
        raise SystemExit("Refusing to replace an existing proposal or proof")
    base = git("show", BASE + ":" + SOURCE)
    bc1 = git("show", BC1 + ":" + SOURCE)
    d41 = git("show", D41 + ":" + SOURCE)
    local = (ROOT / SOURCE).read_bytes()
    if sha(bc1) != BC1_SHA or sha(d41) != D41_SHA or local != bc1:
        raise SystemExit("Protected source or immutable source identity mismatch")
    if transform(bc1.decode(), remove=True).encode() != base:
        raise SystemExit("BC1 is not exactly the six reviewed hooks over the parent")
    candidate = transform(d41.decode()).encode()
    if transform(candidate.decode(), remove=True).encode() != d41:
        raise SystemExit("Union does not preserve the complete #5212 source")
    ast.parse(candidate)
    if candidate.count(b'"src/data_sheets_schema/latch_journal.py"') != 1:
        raise SystemExit("D41 journal routing dependency is not unique")
    if candidate.count(b"canonical(record), canonical(retain)") != 1:
        raise SystemExit("A14 retain memo dependency is not unique")
    patch = "".join(difflib.unified_diff(bc1.decode().splitlines(True), candidate.decode().splitlines(True),
        fromfile="a/" + SOURCE, tofile="b/" + SOURCE)).encode()
    if not patch or (ROOT / SOURCE).read_bytes() != local:
        raise SystemExit("Empty proposal or changed protected source")
    evidence = {"format": "wave7_bc1_protected_proposal_v1", "date": "2026-10-29",
        "packet_head_before_proposal": git("rev-parse", "HEAD").decode().strip(),
        "sources": {"pre_bc1": BASE, "bc1": BC1, "a13_a14_d41": D41},
        "protected_source": SOURCE, "branch_source_sha256": sha(local),
        "candidate_source_sha256": sha(candidate), "proposal_sha256": sha(patch),
        "candidate_bytes": len(candidate), "proposal_bytes": len(patch),
        "six_bc1_hooks_exact_parent_delta": True, "removing_hooks_yields_exact_d41_source": True,
        "a13_asset_pins_and_a14_and_d41_preserved": True,
        "branch_protected_source_unchanged": True, "applied": False,
        "repin": "Apply candidate hash only in a fresh git archive for validation; AGY applies real merge.",
        "helper_sha256": sha(Path(__file__).read_bytes())}
    output.write_bytes(patch)
    proof.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"proposal": str(output), "proof": str(proof), **evidence}, sort_keys=True))


if __name__ == "__main__":
    main()
