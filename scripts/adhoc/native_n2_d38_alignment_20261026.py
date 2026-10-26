#!/usr/bin/env python3
# Purpose: N2 D38 offline R9 asset alignment check, 2026-10-26; Refs #5170, #4354.
# Inputs: committed N2 pin-only branch and reviewed f73764e06/6a0f8acfe Git blobs.
# Outputs: fresh evidence-only composed closures, projected rules and report.
# No registrations, generation, provider calls, native launch or prompt edits.
# Adapted from db0573d96:native_n1c_r9_alignment_20261024.py; support copies are exact.
"""Check a composed asset closure; this is not an installed-target acceptance."""

from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

BASE = "fbf885213db040f5cbd19f742cdb7de76fd3382c"
TARGET = "f73764e0685f436a07e802766e16030572d29a18"
ASSET_SOURCE = "6a0f8acfed6d58fac8747d891b8a05975534a5c5"
RECOVERY_SOURCE = "db0573d96bb16ee32d3537ea0a9ad0ca607e355a"
SOURCE_HELPER = "scripts/adhoc/native_n1c_r9_alignment_20261024.py"
SELF = "scripts/adhoc/native_n2_d38_alignment_20261026.py"
SUPPORT = "scripts/adhoc/native_n1b_offline_preflight_20261023.py"
ORIGIN_PROOF = "scripts/adhoc/native_n1b_receipt_policy_probe_20261023.py"
SELECTION = "src/data_sheets_schema/native_shared_selection.py"
OMISSION = "src/data_sheets_schema/omission_inventory_v1/"
GENERIC = "src/download/prompts/d4d_generic_arm_prompt_v10.md"
UNIFORM = ".claude/commands/d4d-uniform-rules-v2.md"
ROTATIONS = {
    GENERIC: (
        "95511eeea60e5112c630c28bcc342f132d14efcf0d5485bbf26f3e81a0f4cc99",
        "ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db",
    ),
    UNIFORM: (
        "cbf7e9f53e97a1d7dd953507308825e3c835daabcb8f6ee0a6a5dcd8bb9a048f",
        "22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e",
    ),
}
R9_START = b"- A slot whose declared range is an enumeration is populated only from a\n"
R9_END = b"\n- `raw_data_format`"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(tree, *arguments):
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(tree), *arguments],
        env=environment, check=True, capture_output=True, timeout=30,
    ).stdout


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--expect-head", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    tree = Path(args.tree).absolute()
    require(tree.resolve(strict=True) == tree, "tree must be physical and absolute")
    require(Path(__file__).resolve(strict=True) == tree / SELF,
            "execute the helper from its declared source tree")
    head = git(tree, "rev-parse", "HEAD").decode().strip()
    require(head == args.expect_head, "HEAD differs from the explicit expected commit")
    require(git(tree, "rev-parse", TARGET + "^{commit}").decode().strip() == TARGET,
            "reviewed target commit is unavailable")
    for commit in (BASE, ASSET_SOURCE, RECOVERY_SOURCE):
        require(git(tree, "rev-parse", commit + "^{commit}").decode().strip() == commit,
                "fixed local source commit is unavailable")

    # Compile captured, committed support bytes, never a cached helper .pyc.
    support_raw = git(tree, "show", head + ":" + SUPPORT)
    require(support_raw == git(tree, "show", RECOVERY_SOURCE + ":" + SUPPORT),
            "recovered support helper differs from its reviewed source")
    support = ModuleType("n2_d38_alignment_support")
    support.__file__ = str(tree / SUPPORT)
    exec(compile(support_raw, support.__file__, "exec"), support.__dict__)
    reader = support.Reader()
    require(reader.read(tree / SUPPORT) == support_raw,
            "support helper differs from its committed blob")
    proof_raw = reader.read(tree / ORIGIN_PROOF)
    require(proof_raw == git(tree, "show", head + ":" + ORIGIN_PROOF)
            == git(tree, "show", RECOVERY_SOURCE + ":" + ORIGIN_PROOF),
            "origin proof helper must match its exact recovered and committed bytes")
    self_raw = reader.read(tree / SELF)
    require(self_raw == git(tree, "show", head + ":" + SELF),
            "alignment helper must be committed before execution")
    require(support.frozen_head(tree) == head, "tracked tree is not frozen")

    destination = support.evidence_destination(args.evidence, args.tag, tree)
    cache_root = destination / "unused-import-cache"
    require(sys.pycache_prefix == str(cache_root) and not os.path.lexists(cache_root),
            "set PYTHONPYCACHEPREFIX to the fresh evidence unused-import-cache path")

    # Helper/test/report commits are allowed. Production has only two pin edits.
    changed = git(
        tree, "diff", "--name-only", "--no-ext-diff", "--no-textconv",
        BASE, head, "--", "src",
    ).decode().splitlines()
    require(changed == [SELECTION], "production delta is not the sole native pin file")
    expected_source = git(tree, "show", BASE + ":" + SELECTION)
    for old, new in ROTATIONS.values():
        require(expected_source.count(old.encode()) == 1,
                "baseline pin replacement is not unique")
        expected_source = expected_source.replace(old.encode(), new.encode())
    require(git(tree, "show", head + ":" + SELECTION) == expected_source,
            "native selection has changes beyond the two reviewed pin replacements")

    roster = support.record_sources(tree, reader)
    tools, isolation = support.isolated_imports(tree, reader, head)
    selection = importlib.import_module("data_sheets_schema.native_shared_selection")
    require(Path(selection.__file__).resolve(strict=True) == tree / SELECTION,
            "native selection imported from another source root")
    loaded_before = tools.loaded_source_proof(tree, head)

    names = tuple(sorted(selection.ASSET_HASHES))
    ordinary = tuple(name for name in names if not name.startswith(OMISSION))
    adjacent = tuple(name for name in names if name.startswith(OMISSION))
    require(len(names) == 13 and len(ordinary) == 10 and len(adjacent) == 3,
            "asset roster differs from the reviewed 10+3 closure")
    for name, (_, new) in ROTATIONS.items():
        require(selection.ASSET_HASHES[name] == new, "reviewed pin is not installed")

    old_bytes, selected_bytes, provenance = {}, {}, []

    def blob(commit, name):
        raw = git(tree, "show", commit + ":" + name)
        return raw, {
            "commit": commit,
            "git_blob": git(tree, "rev-parse", commit + ":" + name).decode().strip(),
            "bytes": len(raw),
            "sha256": support.digest(raw),
        }

    for name in names:
        old, baseline_pin = blob(BASE, name)
        installed, installed_pin = blob(head, name)
        require(installed == old, "trial asset changed: " + name)
        require(reader.read(tree / name) == installed,
                "installed asset differs from its committed blob: " + name)
        expected_old = ROTATIONS[name][0] if name in ROTATIONS else selection.ASSET_HASHES[name]
        require(support.digest(old) == expected_old, "baseline asset pin differs: " + name)
        chosen, chosen_pin = blob(TARGET if name in ROTATIONS else head, name)
        if name in ROTATIONS:
            authored, authored_pin = blob(ASSET_SOURCE, name)
            require(authored == chosen, "reviewed target differs from the D38 authored asset")
            chosen_pin["authored_at"] = authored_pin
        require(support.digest(chosen) == selection.ASSET_HASHES[name],
                "composed asset differs from its native pin: " + name)
        old_bytes[name], selected_bytes[name] = old, chosen
        provenance.append({
            "logical_path": name,
            "baseline": baseline_pin,
            "installed_trial": {**installed_pin, "path": str(tree / name)},
            "selected": chosen_pin,
            "read_method": "module_adjacent" if name in adjacent else "composed_cwd",
        })

    destination.mkdir(mode=0o700)
    staged = {}

    def stage(label, substitution=None):
        root = destination / label
        root.mkdir(mode=0o700)
        for name in ordinary:
            raw = old_bytes[name] if name == substitution else selected_bytes[name]
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            write_new(path, raw)
            require(reader.read(path) == raw, "staged bytes differ: " + name)
        staged[label] = root
        return root

    positive_root = stage("composed-reviewed")
    old_generic_root = stage("composed-old-generic", GENERIC)
    old_uniform_root = stage("composed-old-uniform", UNIFORM)

    def capture_at(root):
        previous = Path.cwd()
        try:
            os.chdir(root)
            return selection.capture_assets()
        finally:
            os.chdir(previous)

    authority = capture_at(positive_root)
    require(tuple(a.pin.role for a in authority) ==
            tuple("asset:" + name for name in names), "captured roster/order differs")
    actual_paths = {}
    for artifact, name in zip(authority, names):
        expected_path = (tree if name in adjacent else positive_root) / name
        require(artifact.pin.path == str(expected_path),
                "capture used an unexpected resource path: " + name)
        require(artifact.raw == selected_bytes[name],
                "capture did not retain the selected blob: " + name)
        require(artifact.pin.sha256 == support.digest(artifact.raw)
                and artifact.pin.bytes == len(artifact.raw),
                "captured artifact pin differs from its bytes")
        actual_paths[name] = artifact.pin.path

    rules = selection.rules_from_assets(authority).encode("utf-8")
    parent = selected_bytes[GENERIC]
    require(parent.count(R9_START) == 1 and parent.count(R9_END) == 1,
            "reviewed R9 delimiters are missing or ambiguous")
    first, last = parent.index(R9_START), parent.index(R9_END)
    require(first < last, "reviewed R9 delimiters are reversed")
    excerpt = parent[first:last]
    require(rules.count(excerpt) == 1,
            "complete reviewed R9 is not present verbatim once in projected rules")

    refusals = []
    for label, root, changed_asset in (
        ("stale_installed_trial", tree, UNIFORM),
        ("old_generic_only", old_generic_root, GENERIC),
        ("old_uniform_only", old_uniform_root, UNIFORM),
    ):
        expected_error = "selected native asset bytes changed: " + changed_asset
        try:
            capture_at(root)
        except ValueError as error:
            require(str(error) == expected_error,
                    "refusal occurred at an unexpected boundary: " + str(error))
            refusals.append({
                "case": label, "cwd": str(root),
                "type": type(error).__name__, "message": str(error),
            })
        else:
            raise ValueError("stale asset closure unexpectedly accepted: " + label)

    for label, root in staged.items():
        actual = sorted(path.relative_to(root).as_posix()
                        for path in root.rglob("*") if path.is_file())
        require(actual == list(ordinary), "staged inventory changed: " + label)
    support.require_source_roster(tree, roster)
    loaded_after = tools.loaded_source_proof(tree, head)
    reader.stable()
    require(support.frozen_head(tree) == head, "source HEAD changed")
    require(not os.path.lexists(cache_root), "unexpected import-cache artifact")

    report = {
        "scope": "composed_offline_asset_closure",
        "status": "positive_projection_and_three_exact_refusals_verified",
        "source_head": head, "pre_rotation_source": BASE, "reviewed_target": TARGET,
        "asset_source": ASSET_SOURCE,
        "adapted_from": {"commit": RECOVERY_SOURCE, "path": SOURCE_HELPER,
                         "sha256": support.digest(git(tree, "show", RECOVERY_SOURCE + ":" + SOURCE_HELPER))},
        "source_tree": git(tree, "rev-parse", head + ":src").decode().strip(),
        "production_changed_paths": changed,
        "source_and_observed_inventory_unchanged": True,
        "helpers": [
            {"path": SELF, "sha256": support.digest(self_raw)},
            {"path": SUPPORT, "sha256": support.digest(support_raw)},
            {"path": ORIGIN_PROOF, "sha256": support.digest(proof_raw),
             "recovered_from": RECOVERY_SOURCE},
        ],
        "isolation": isolation,
        "pycache_prefix": str(cache_root),
        "loaded_project_sources_before": loaded_before,
        "loaded_project_sources_after": loaded_after,
        "asset_provenance": provenance,
        "positive_actual_read_paths": actual_paths,
        "positive_counts": {"ordinary_staged_assets": 10, "module_adjacent_assets": 3},
        "r9": {
            "source": GENERIC, "bytes": len(excerpt),
            "sha256": support.digest(excerpt),
            "projected_rules_verbatim_occurrences": 1,
        },
        "projected_rules_sha256": support.digest(rules),
        "refusals": refusals,
        "observed_files": reader.manifest(),
        "limits": [
            "The composed resource directory is not a merged or installed target checkout.",
            "Only native asset capture and factual-rule projection were exercised.",
            "No full instruction, selection registration, execution or canary was produced.",
            "No token/context capacity or scientific-equivalence acceptance is claimed.",
            "Installed dependency bytes are not authenticated by this check.",
            "Pre-rotation full-suite results remain pre-rotation evidence.",
        ],
    }
    write_new(destination / "projected-rules.txt", rules)
    write_new(destination / "reviewed-r9.txt", excerpt)
    write_new(destination / "report.json", support.encoded(report))
    print(str(destination / "report.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
