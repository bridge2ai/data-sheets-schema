#!/usr/bin/env python3
# Purpose: verify actual installed N2/D38 assets and full API/native renders.
# Inputs: frozen restack, cached reviewed Git blobs and pinned historical inputs.
# Outputs: fresh source/asset proofs, complete instructions, deltas and refusals.
# Refs #4354, #5170; 2026-10-26. Offline only; no launch or scientific acceptance.
"""Validate the installed 13-asset closure without a synthetic positive root."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
from types import ModuleType

SELF = "scripts/adhoc/native_n2_installed_d38_20261026.py"
SUPPORT = "scripts/adhoc/native_n2_render_parity_20261025.py"
SUPPORT_SHA256 = "24c25f12b941d2384d37496098ea80d55732698d83cda10257c500b60d0ea6a6"
HISTORICAL = "fbf885213db040f5cbd19f742cdb7de76fd3382c"
TARGET = "a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5"
D38 = "f73764e0685f436a07e802766e16030572d29a18"
GENERIC = "src/download/prompts/d4d_generic_arm_prompt_v10.md"
UNIFORM = ".claude/commands/d4d-uniform-rules-v2.md"
OMISSION_PREFIX = "src/data_sheets_schema/omission_inventory_v1/"
NATIVE_ONLY = frozenset({
    "src/download/prompts/native_shared_generation_v1.md",
    "src/download/prompts/native_shared_receipt_policy_v1.md",
})
ROTATIONS = {
    GENERIC: "ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db",
    UNIFORM: "22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e",
}
EXPECTED_ASSETS = {
    ".claude/agents/d4d-provenance-guard-v2.md": "10dc4689e1855096ef3507de01b129abfd5795690fbcfbd3458407741fe30085",
    ".claude/commands/d4d-agent-v2.md": "dcb33659014a68596a248ed768c196dd0b1e396a0fe41579918dff95ac559299",
    ".claude/commands/d4d-full-core-v2.md": "2f52d3e70d7a6f3098b7acfcc80b9e9d0f318c9ca1517f711eae9fb789410124",
    UNIFORM: ROTATIONS[UNIFORM],
    OMISSION_PREFIX + "context.schema.json": "4cb51a481905d272d24726dddd22ab91ed3e3ce1e6a23f37d50d2f1cefa9c2c8",
    OMISSION_PREFIX + "policy.md": "0b197cf8bafe1f3df53f3c23922e9e38d514cca42979b90282022b8bef4c0b0d",
    OMISSION_PREFIX + "response.schema.json": "90d9e0fcb50b391c9345b0150af2a43f7c3581673b89f35069a70f57046e6d07",
    GENERIC: ROTATIONS[GENERIC],
    "src/download/prompts/evidence_protocol_v7.md": "72039b09bfaaa43d683c7a0ba7560aace0d5c19209f7a1e1c70c4290ee48ddb6",
    "src/download/prompts/native_shared_generation_v1.md": "ff679e9a6a76a760e57d7c0e6df88102fe630a6b802b513dc0b0144aa39ac18c",
    "src/download/prompts/native_shared_receipt_policy_v1.md": "de90df8ec7818b645e352fbae6bcc153387c02d7fcf71ef8f2abe409a083b75a",
    "src/download/prompts/native_source_attribution_v1.md": "e13f0bd8de8e4e28cd1c1216799defb7005f7e041698698a4478d824e8acc761",
    "src/download/prompts/shared_generation_v1.md": "34608f26b4a0407da036486a6e8ec6692df6b54594335140bdc3df4229d78450",
}
R9_SHA = "d9f7884a03f0480d1ab610118f32850e2d98008fcd67fb51a16a4b7b7ca79a4d"
PROTECTED = ("src/data_sheets_schema/shared_generation.py",
             "src/download/prompts/canonical_hashes.yaml")


def load_support(tree):
    """Reuse unchanged pure/evidence routines; never override historical pins."""
    path = Path(tree) / SUPPORT
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SUPPORT_SHA256:
        raise ValueError("historical support bytes differ before execution")
    value = ModuleType("native_n2_historical_render_support")
    value.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), value.__dict__)
    return value


def frozen_source(tree, head, reader, support):
    result = support.frozen_source(tree, head, reader)
    for name in (SELF, SUPPORT):
        raw = reader.read(tree / name)
        support.require(raw == support.git(tree, "show", head + ":" + name),
                        "installed helper differs from its committed source: " + name)
    support.require(reader.read(tree / SUPPORT) == support.git(tree, "show", HISTORICAL + ":" + SUPPORT),
                    "historical support helper changed")
    result["installed_helper_sha256"] = support.sha(reader.read(tree / SELF))
    result["historical_helper_reused_unchanged"] = SUPPORT_SHA256
    return result


def compare_rules(generic, api, native, support):
    support.require(support.sha(generic) == ROTATIONS[GENERIC], "not the reviewed D38 generic source")
    r9 = support.between(generic, support.R9_START, support.R9_END, "D38 R9")
    support.require(len(r9) == 4433 and support.sha(r9) == R9_SHA, "complete D38 R9 differs")
    counts = {"api25": api.count(r9), "native26": native.count(r9)}
    support.require(counts == {"api25": 1, "native26": 1},
                    "complete D38 R9 must occur verbatim exactly once in each instruction")
    api_rules = support.between(api, support.RULE_START, support.RULE_END, "API uniform rules", strip=True)
    native_rules = support.between(native, support.RULE_START, support.RULE_END, "native uniform rules", strip=True)
    support.require(api_rules == native_rules, "complete extracted D38 uniform sections differ")
    return {"r9": {"bytes": len(r9), "sha256": support.sha(r9), "occurrences": counts},
            "uniform": {"bytes": len(api_rules), "sha256": support.sha(api_rules), "identical": True,
                        "extraction": "Unique start/end markers; trim surrounding whitespace only."}}, r9, api_rules


def installed_assets(tree, head, reader, support):
    from data_sheets_schema import native_shared_selection as selected
    support.require(Path.cwd() == tree, "positive asset capture must use the actual selected checkout")
    support.require(dict(selected.ASSET_HASHES) == EXPECTED_ASSETS, "native descriptor asset roster/pins differ")
    assets = selected.capture_assets()  # Real capture; no reader/path substitutions.
    support.require(tuple(a.pin.role for a in assets) == tuple("asset:" + n for n in sorted(EXPECTED_ASSETS)),
                    "actual captured asset roster/order differs")
    rows = []
    for item in assets:
        name = item.pin.role[len("asset:"):]
        path = tree / name
        raw = reader.read(path)
        source = HISTORICAL if name in NATIVE_ONLY else TARGET
        support.require(item.pin.path == str(path) and item.raw == raw
                        and item.pin.bytes == len(raw) and item.pin.sha256 == EXPECTED_ASSETS[name],
                        "positive capture is not the exact installed asset: " + name)
        support.require(support.sha(raw) == EXPECTED_ASSETS[name]
                        and raw == support.git(tree, "show", head + ":" + name)
                        and raw == support.git(tree, "show", source + ":" + name),
                        "installed asset differs from committed/source authority: " + name)
        if name in ROTATIONS:
            support.require(raw == support.git(tree, "show", D38 + ":" + name), "asset differs from reviewed D38")
        rows.append({"logical_path": name, "path": str(path), "bytes": len(raw),
                     "sha256": support.sha(raw), "source_commit": source,
                     "git_blob": support.git(tree, "rev-parse", head + ":" + name).decode().strip(),
                     "read_method": "module_adjacent" if name.startswith(OMISSION_PREFIX) else "installed_checkout"})
    support.require(sum(r["read_method"] == "module_adjacent" for r in rows) == 3 and len(rows) == 13,
                    "installed closure is not 10 ordinary plus 3 module-adjacent assets")
    protected = []
    for name in PROTECTED:
        raw = reader.read(tree / name)
        support.require(raw == support.git(tree, "show", head + ":" + name)
                        == support.git(tree, "show", TARGET + ":" + name), "protected target changed: " + name)
        protected.append({"path": str(tree / name), "sha256": support.sha(raw), "target_commit": TARGET})
    return assets, {"counts": {"ordinary_installed": 10, "module_adjacent": 3, "total": 13},
                    "assets": rows, "protected_target_identity": protected,
                    "positive_asset_substitution": False}


def stale_refusals(tree, target, assets, reader, support):
    """Only negative cases use copied ordinary assets; production remains intact."""
    from data_sheets_schema import native_shared_selection as selected
    ordinary = {a.pin.role[len("asset:"):]: a.raw for a in assets
                if not a.pin.role[len("asset:"):].startswith(OMISSION_PREFIX)}
    rows = []
    for label, substitutions, failing_name in (
        ("both_pre_d38", (GENERIC, UNIFORM), UNIFORM),
        ("old_generic_only", (GENERIC,), GENERIC),
        ("old_uniform_only", (UNIFORM,), UNIFORM),
    ):
        root = target / ("negative-" + label)
        root.mkdir(mode=0o700)
        for name, original in ordinary.items():
            raw = support.git(tree, "show", HISTORICAL + ":" + name) if name in substitutions else original
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            support.write_new(path, raw)
            support.require(reader.read(path) == raw, "negative fixture bytes differ")
        expected = "selected native asset bytes changed: " + failing_name
        previous = Path.cwd()
        try:
            os.chdir(root)
            try:
                selected.capture_assets()
            except ValueError as error:
                support.require(str(error) == expected, "wrong stale-asset refusal: " + str(error))
            else:
                raise ValueError("stale installed asset was accepted: " + label)
        finally:
            os.chdir(previous)
        rows.append({"case": label, "cwd": str(root), "status": "exact_refusal",
                     "exception_type": "ValueError", "message": expected,
                     "substitutions": list(substitutions), "old_source": HISTORICAL,
                     "scope": "Negative fixture only; not the positive installed asset root."})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tree", "expect-head", "evidence", "name", "historical-report", "historical-report-sha256",
                 "historical-registration", "historical-ledger", "label", "date"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    tree = Path(args.tree)
    support = load_support(tree)
    support.require(tree.is_absolute() and tree.resolve(strict=True) == tree
                    and Path(__file__).resolve() == tree / SELF, "execute helper from its physical selected checkout")
    support.require(re.fullmatch("[0-9a-f]{40}", args.expect_head), "expected head must be a full SHA")
    support.require(re.fullmatch("[0-9a-f]{64}", args.historical_report_sha256), "historical report needs an exact SHA256")
    support.require(re.fullmatch(r"[A-Za-z0-9_-]+", args.label), "unsafe fixture label")
    support.require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date), "date must be explicit YYYY-MM-DD")
    target = support.destination(args.evidence, args.name, tree)
    os.chdir(tree)
    reader = support.Reader()
    source = frozen_source(tree, args.expect_head, reader, support)
    report = {"scope": "actual_installed_d38_assets_and_hypothetical_full_instruction_render",
              "status": "started", "acceptance_eligible": False, "launch_authorized": False,
              "scientific_acceptance": "not_assessed", "runtime_acceptance": "not_run",
              "source": source, "target": TARGET, "d38": D38, "argv": vars(args),
              "fixture_declarations_not_selected_caps": True}
    target.mkdir(mode=0o700)
    files, exit_code = {}, 2
    try:
        report["isolation"] = support.isolated_imports(tree, args.expect_head, target, reader)
        assets, report["installed_closure"] = installed_assets(tree, args.expect_head, reader, support)
        old, snapshots, historical, report["historical"] = support.historical_inputs(args, reader)
        for role, raw in snapshots.items():
            files["historical-input-" + role + ".txt"] = raw
        for name, raw in historical.items():
            files["historical-" + name] = raw
        reg, schemas, api, api_spec = support.api_fixture(tree, target, old, reader, args.label, args.date)
        native, native_spec = support.native_fixture(tree, target, reg, schemas, reader, args.label, args.date)
        files.update({"current-api25-instruction.txt": api, "current-native26-instruction.txt": native,
                      "api-render-spec.json": support.encoded(api_spec), "native-render-spec.json": support.encoded(native_spec),
                      "instructions.diff": support.diff(api, native, "installed-api25", "installed-native26"),
                      "historical-to-current-api.diff": support.diff(historical["current-target-api25-instruction.txt"], api,
                                                                   "N1b-api25", "installed-api25"),
                      "historical-to-current-native.diff": support.diff(historical["hypothetical-native26-instruction.txt"], native,
                                                                      "N1b-native26", "installed-native26")})
        report["parity"], r9, rules = compare_rules(reader.read(tree / GENERIC), api, native, support)
        files.update({"reviewed-r9.txt": r9, "api-uniform-rules.txt": rules, "native-uniform-rules.txt": rules})
        report["stale_asset_refusals"] = stale_refusals(tree, target, assets, reader, support)
        # Verify the true positive closure again after all negative-root activity.
        _, final_closure = installed_assets(tree, args.expect_head, reader, support)
        support.require(final_closure == report["installed_closure"], "installed closure changed after negative fixtures")
        report["fixture"] = {"api_registration": reg, "native_selection_written": False,
                             "native_runtime_written": False, "original_registration_changed": False,
                             "source_inputs": reg["inputs"], "schema_source": "actual restacked checkout",
                             "vocabulary_source": "actual selected profile in restacked checkout",
                             "bounds_scope": "Historical API allowances and native diagnostic placeholders; not approved launch limits."}
        report["classification"] = "Complete instruction deltas retained for independent review; equal shared rules do not establish scientific equivalence."
        report["status"], exit_code = "verified_installed_assets_and_full_offline_render", 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        report["status"] = "refused"
        report["error"] = {"type": type(error).__name__, "message": str(error)[:3000]}
    try:
        report["loaded_project_sources"] = support.module_origins(tree, args.expect_head, reader)
        support.require(frozen_source(tree, args.expect_head, reader, support) == source, "source identity changed")
        reader.stable()
        support.require(not os.path.lexists(target / "unused-import-cache"), "unexpected import cache created")
        support.require(not os.path.lexists(target / "hypothetical-unwritten"), "unexpected runtime output state created")
        report["source_and_inputs_unchanged"] = True
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        report.update(status="refused", source_and_inputs_unchanged=False,
                      final_verification_error={"type": type(error).__name__, "message": str(error)[:3000]})
        exit_code = 2
    report["inputs"] = reader.manifest()
    for name, raw in files.items():
        support.write_new(target / name, raw)
    report["outputs"] = [{"file": p.name, "bytes": p.stat().st_size, "sha256": support.sha(p.read_bytes())}
                         for p in sorted(target.iterdir()) if p.is_file()]
    support.write_new(target / "report.json", support.encoded(report))
    print(target / "report.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
