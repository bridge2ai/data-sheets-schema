#!/usr/bin/env python3
"""D68/#5212 review item 1, LR12: capture actual f8 split outputs, 2026-10-31.

Inputs: an unchanged local f8c5ac73c checkout and a new scratch directory.
Outputs: one completed generic-v6 before-tree, original invocation, manifests,
and generation evidence. Uses f8's real runner with its offline FakeClient;
does not rewrite provenance, output paths, timestamps or accounting afterwards.
Run under the packet's offline sandbox with Python -S -P -B; plan first.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d41_legacy_controls_20261029 import (
    PRE, bootstrap, capture, git, origins, save, saved_spec,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tree", type=Path, required=True)
parser.add_argument("--scratch", type=Path, required=True)
parser.add_argument("--mode", choices=("plan", "generate"), required=True)
args = parser.parse_args()
args.tree, args.scratch = args.tree.resolve(), args.scratch.resolve()
packet = Path(__file__).resolve().parents[2]
assert args.scratch.is_relative_to(packet / ".d68-validation")
assert git(args.tree, "rev-parse", "HEAD") == PRE
assert not git(args.tree, "diff", "HEAD", "--", "src", "tests")
if args.mode == "plan":
    print(json.dumps({"source_head": PRE, "source_tree": str(args.tree),
                      "scratch": str(args.scratch), "fake_calls_expected": 4,
                      "out_dir": None, "captures": 1}, indent=2))
    raise SystemExit(0)
assert not args.scratch.exists(), "preserve prior capture"
args.scratch.mkdir(parents=True)
environment = bootstrap(args.tree, args.scratch)
from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external
from tests.test_download.test_api_runner import FakeClient
import yaml

run = args.scratch / "run"
run.mkdir()
selected = replace(external.__wrapped__(run), out_dir=None)
assert selected.full_path.parent != selected.core_path.parent
assert all(path.is_relative_to(run) for path in (
    selected.full_path, selected.core_path, selected.provenance_path))
client = FakeClient()
result = api.execute(selected, client=client)
assert len(client.messages.calls) == 4 and not result.get("validation_problems")
record = yaml.safe_load(selected.provenance_path.read_text())
assert record["repo"]["commit"] == PRE
assert "runtime_integrity" not in record["model"]
assert selected.provenance_path.stat().st_size
assert not list(run.rglob("*_api_progress.json"))
destination = args.scratch / "captures/split/call-2"
destination.mkdir(parents=True)
manifest = capture(run, destination / "before")
save(destination / "before-manifest.json", manifest)
save(destination / "invocation.json", {"call": 2, "root": str(run),
    "resume": True, "spec": saved_spec(selected)})
save(args.scratch / "generation.json", {"source_head": PRE,
    "environment": environment, "origins": origins(args.tree),
    "fake_dispatches": len(client.messages.calls), "provider_calls": 0,
    "provenance": str(selected.provenance_path), "files": len(manifest),
    "full_parent": str(selected.full_path.parent),
    "core_parent": str(selected.core_path.parent),
    "capture": str(destination), "provenance_bytes_rewritten": False})
print(json.dumps({"capture": str(destination), "files": len(manifest),
                  "source_head": PRE, "fake_dispatches": 4}))
