"""Split C capture orchestration and stage CLI without changing pure stage code.

Inputs: exact U3-C round-four capture/stage Git preimages below (2026-11-07).
Outputs: consumer capture, explicit orchestration, stage package and CLI.
Purpose: native U3-C round 4 approved consumer/orchestrator separation.
Use --check first; --apply refuses changed preimages or existing destinations.
No tests, imports of repository modules, Git mutation, network or native calls.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

PREIMAGES = {
    "native_shared_capture.py": "a7a64e4bd1a944d0072012699a9d3cf835d26a9f",
    "native_shared_stage.py": "0c51b71e87ee627d060f5982de02ea2a2ac35207",
}
MOVED = frozenset((
    "_create", "_append", "activate", "_base", "initialize", "_load", "_load_live",
    "_persist_observation", "capture_stage", "publish_stage", "seal_originals",
    "observe_request_read", "observe_response_intent", "observe_response_written",
    "observe_advance_settled", "selected_receipt_paths", "live_receipt_block",
    "live_provenance_block", "_recorded_run", "recorded_receipt_block",
    "recorded_receipt_claims",
))


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def segment(lines, node):
    return "".join(lines[node.lineno - 1:node.end_lineno])


def replacements(text, before, after, count):
    if text.count(before) != count:
        raise ValueError("unexpected replacement cardinality: " + before)
    return text.replace(before, after)


def prepare(root):
    execution_root = root.parent
    if root.name != "codex-native-u3c-r4" or execution_root.name != "d4d-executions":
        raise ValueError("only the assigned new C worktree may be split")
    if (execution_root / "plans/native_quiet_window.lock").exists():
        raise ValueError("quiet-window lock exists")
    package = root / "src/data_sheets_schema"
    originals = {}
    for name, expected in PREIMAGES.items():
        path = package / name
        if path.is_symlink():
            raise ValueError("source must be regular: " + name)
        raw = path.read_bytes()
        if blob(raw) != expected:
            raise ValueError("source differs from exact reviewed preimage: " + name)
        originals[name] = raw
    capture = originals["native_shared_capture.py"].decode()
    lines = capture.splitlines(keepends=True)
    tree = ast.parse(capture)
    functions = {node.name: node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    if not MOVED <= set(functions):
        raise ValueError("capture function roster changed")
    pure_names = set(functions) - MOVED
    pure_names.add("current_artifact")
    moved = "\n\n\n".join(segment(lines, node).rstrip()
        for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in MOVED)
    needed = sorted({node.id for node in ast.walk(ast.parse(moved))
                     if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)} & pure_names)
    moved = replacements(moved,
        "from .native_shared_controller import reconstruct_composition",
        "from .native_shared_controller_orchestration import reconstruct_composition", 2)
    moved = replacements(moved,
        "from .native_shared_publication import ",
        "from .native_shared_publication_orchestration import ", 2)
    moved = replacements(moved,
        "    value = registration.verified(execution_raw)",
        "    with controls_orchestration.loaded_controls() as controls:\n"
        "        value = registration.verified(execution_raw, classifier_projection=controls)", 1)
    moved = replacements(moved,
        "    value = registration.verified(e.raw)",
        "    with controls_orchestration.loaded_controls() as controls:\n"
        "        value = registration.verified(e.raw, classifier_projection=controls)", 1)
    header = '''"""Live C capture verification and durable publication orchestration.

Moved from native_shared_capture by the reviewed round-four split. Pure replay
classes/helpers remain defined once in that consumer module. Every live base
freshly verifies outer E with an explicit active classifier projection; no
successful replay verdict is cached as authority.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path, PurePosixPath
import shlex

from . import native_shared_contract as c
from . import native_shared_evidence as evidence
from . import native_shared_streams as live_streams
from . import native_shared_observations as observed
from . import native_shared_stage as stage
from . import native_shared_controls_orchestration as controls_orchestration
'''
    imports = "from .native_shared_capture import (\n" + "".join(
        "    " + name + ",\n" for name in needed) + ")\n"
    orchestration = header + imports + "\n\n" + moved + "\n"
    removed = set()
    for name in MOVED:
        node = functions[name]
        removed.update(range(node.lineno - 1, node.end_lineno))
    consumer = "".join(line for number, line in enumerate(lines) if number not in removed)
    consumer = replacements(consumer,
        '"""Fixed native stage capture and publication boundary.',
        '"""Input-only native stage capture and saved replay.', 1)
    consumer = consumer.replace("\n\n\n\n", "\n\n\n")

    stage_raw = originals["native_shared_stage.py"]
    stage_text = stage_raw.decode()
    stage_tree = ast.parse(stage_text)
    main = [node for node in stage_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    guards = [node for node in stage_tree.body if isinstance(node, ast.If)
              and "__name__" in ast.unparse(node.test)]
    if len(main) != 1 or len(guards) != 1 or guards[0] is not stage_tree.body[-1]:
        raise ValueError("stage CLI shape changed")
    stage_lines = stage_text.splitlines(keepends=True)
    pure_stage = "".join(stage_lines[:main[0].lineno - 1]).rstrip() + "\n"
    pure_stage = replacements(pure_stage, "import argparse\n", "", 1)
    pure_stage = replacements(pure_stage, "from . import ", "from .. import ", 4)
    pure_stage = replacements(pure_stage,
        "delegates all observation and durable publication to native_shared_capture.",
        "lives in __main__ and delegates to native_shared_capture_orchestration.", 1)
    cli_main = segment(stage_lines, main[0])
    cli_main = replacements(cli_main,
        "    from .native_shared_capture import capture_stage, publish_stage\n", "", 1)
    cli = '''"""Unchanged native_shared_stage advance CLI; orchestration is explicit.

Package __init__ contains the pure stage implementation and never imports this
module. The registered -m data_sheets_schema.native_shared_stage spelling stays
unchanged.
"""
from __future__ import annotations

import argparse
from . import _Replay, _check_response, _prepare_next, c, nr
from ..native_shared_capture_orchestration import capture_stage, publish_stage


''' + cli_main + "\n\n\nif __name__ == '__main__':\n    main()\n"
    # Every existing pure stage function/class is byte-identical. Only top-level
    # relative imports, the package docstring and CLI extraction differ.
    old_stage_nodes = {node.name: segment(stage_lines, node)
        for node in stage_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and node.name != "main"}
    new_lines = pure_stage.splitlines(keepends=True)
    new_stage_nodes = {node.name: segment(new_lines, node)
        for node in ast.parse(pure_stage).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    if old_stage_nodes != new_stage_nodes:
        raise ValueError("pure stage implementation changed during package conversion")
    # Unmoved capture functions/classes must likewise retain exact source.
    new_capture_lines = consumer.splitlines(keepends=True)
    new_capture_nodes = {node.name: segment(new_capture_lines, node)
        for node in ast.parse(consumer).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    old_capture_nodes = {name: segment(lines, node) for name, node in functions.items() if name not in MOVED}
    if old_capture_nodes != new_capture_nodes:
        raise ValueError("pure capture implementation changed during extraction")
    outputs = {
        "native_shared_capture.py": consumer.encode(),
        "native_shared_capture_orchestration.py": orchestration.encode(),
        "native_shared_stage/__init__.py": pure_stage.encode(),
        "native_shared_stage/__main__.py": cli.encode(),
    }
    for relative, raw in outputs.items():
        compile(raw, str(package / relative), "exec", dont_inherit=True)
        if relative != "native_shared_capture.py" and (package / relative).exists():
            raise ValueError("new destination already exists: " + relative)
    witness = {
        "preimage_git_blobs": PREIMAGES,
        "moved_functions": sorted(MOVED),
        "imported_pure_helpers": needed,
        "pure_capture_functions_identical": sorted(old_capture_nodes),
        "pure_stage_functions_identical": sorted(old_stage_nodes),
        "outputs_sha256": {path: hashlib.sha256(raw).hexdigest()
                           for path, raw in sorted(outputs.items())},
        "removed": ["native_shared_stage.py"],
        "registered_module_command_unchanged": "data_sheets_schema.native_shared_stage",
    }
    return package, originals, outputs, witness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    package, originals, outputs, witness = prepare(args.root.resolve(strict=True))
    if args.apply:
        for relative, raw in outputs.items():
            path = package / relative
            path.parent.mkdir(exist_ok=True)
            if relative == "native_shared_capture.py":
                if path.read_bytes() != originals[relative]:
                    raise ValueError("capture changed after preflight")
                path.write_bytes(raw)
            else:
                with path.open("xb") as out:
                    out.write(raw)
            if path.read_bytes() != raw:
                raise ValueError("written output differs: " + relative)
        old = package / "native_shared_stage.py"
        if old.read_bytes() != originals[old.name]:
            raise ValueError("stage preimage changed; refusing unlink")
        old.unlink()
    print(json.dumps({"applied": args.apply, **witness}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

