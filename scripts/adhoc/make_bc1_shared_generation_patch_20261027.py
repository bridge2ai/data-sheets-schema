#!/usr/bin/env python3
# Purpose: emit and syntax-check the protected BC1 hook proposal, without applying it.
# Inputs: exact local shared_generation.py bytes; outputs: unified diff + SHA manifest.
# Refs: Wave2 BC1/D44/D45; date2026-10-27. No network, provider calls or protected writes.
"""Produce the selected-mode hook diff; legacy behavior remains the default."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELATIVE = "src/data_sheets_schema/shared_generation.py"


def proposed_source(base: str) -> str:
    replacements = [
        ('NAME = "shared_generation_v1"\n',
         'BC1_HOOK_VERSION = 1  # Explicit opt-in; dependencies and registrations must be rebuilt.\n'
         'NAME = "shared_generation_v1"\n'),
        ('def select(spec) -> dict | None:\n',
         'def select(spec) -> dict | None:\n'
         '    from .bc1_selection import validate_spec_mode\n'
         '    validate_spec_mode(spec)\n'),
        ('                   | ({"routing"} if version == 2 else set()), "shared registration")\n',
         '                   | ({"routing"} if version == 2 else set())\n'
         '                   | ({"bounded_carry"} if "bounded_carry" in value else set()), "shared registration")\n'),
        ('    return value\n\n\ndef _validate_pin(value, label):\n',
         '    if "bounded_carry" in value:\n'
         '        from .bc1_selection import validate_registration as validate_bc1\n'
         '        validate_bc1(value, shared_version=version)\n'
         '    return value\n\n\ndef _validate_pin(value, label):\n'),
        ("    captured = _context_capture(spec)\n    return memo(spec, 'schema_context',",
         "    captured = _context_capture(spec)\n"
         "    from .bc1_selection import enabled as bc1_enabled\n"
         "    if bc1_enabled(spec):\n"
         "        from .bc1_context import schema_context as bc1_schema_context\n"
         "        return bc1_schema_context(captured, record)\n"
         "    return memo(spec, 'schema_context',"),
        ('def plan(spec, settings):\n    """No client or historical-output discovery; dynamic sizes remain unknown."""\n',
         'def plan(spec, settings):\n    """No client or historical-output discovery; dynamic sizes remain unknown."""\n'
         '    from .bc1_selection import enabled as bc1_enabled\n'
         '    if bc1_enabled(spec):\n'
         '        from .bc1_registration import plan as bc1_plan\n'
         '        return bc1_plan(spec, settings)\n'),
    ]
    result = base
    for before, after in replacements:
        if result.count(before) != 1:
            raise ValueError("protected source differs at reviewed hook: " + before.splitlines()[0])
        result = result.replace(before, after, 1)
    ast.parse(result, filename=RELATIVE + " [unapplied BC1 proposal]")
    return result


def proposal_bytes(base: bytes) -> bytes:
    original = base.decode("utf-8")
    proposed = proposed_source(original)
    return "".join(difflib.unified_diff(original.splitlines(keepends=True), proposed.splitlines(keepends=True),
        fromfile="a/" + RELATIVE, tofile="b/" + RELATIVE)).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    protected = ROOT / RELATIVE
    if args.output.resolve() == args.manifest.resolve():
        raise ValueError("proposal and manifest require distinct fresh paths")
    for path in (args.output, args.manifest):
        if not path.resolve().is_relative_to(ROOT) or path.resolve() == protected.resolve():
            raise ValueError("proposal artifacts must be fresh files inside this repository, outside protected source")
        if path.exists():
            raise ValueError("refusing to replace an existing proposal artifact: " + str(path))
    base = protected.read_bytes()
    patch = proposal_bytes(base)
    proposed = proposed_source(base.decode()).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(patch)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "format": "bc1_protected_hook_proposal_v1",
        "base_path": RELATIVE, "base_sha256": hashlib.sha256(base).hexdigest(),
        "proposal_sha256": hashlib.sha256(patch).hexdigest(),
        "proposed_source_sha256": hashlib.sha256(proposed).hexdigest(),
        "applied": False, "syntax_checked": True,
        "scope": "BC1-only opt-in/parser/schema/plan hooks; no A14/D41 merge or canonical asset rotation",
        "identity_note": "Applying this changes the shared source hash; build fresh BC1 registrations afterward.",
    }
    with args.manifest.open('x') as stream:
        stream.write(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    if protected.read_bytes() != base:
        raise RuntimeError("protected source changed during proposal generation")
    print(json.dumps({"proposal": str(args.output), "sha256": hashlib.sha256(patch).hexdigest(), "applied": False}))


if __name__ == "__main__":
    main()
