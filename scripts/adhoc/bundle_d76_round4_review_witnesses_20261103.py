#!/usr/bin/env python3
"""Copy the two PR #5213 round-3 reviewers' witnesses without changing bytes.

Inputs: retained scratch-5213r3check reviewer sources and the two review reports.
Outputs: a fresh repository bundle, SHA-256 provenance manifest, explicit pytest
target lists and interpretation notes. No imports or execution of witness code.
Issue #5213, round-4 task 9; 2026-11-03. Historical originals remain untouched.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


DATE = "2026-11-03"
BUNDLE = "scripts/adhoc/d76_round4_review_witnesses_20261103"
REVIEWED_HEAD = "d13c1711e19dcdcc7f624b66e15b735ebc0aab8f"
FILES = {
    "codex": {
        "test_new_guard.py": "round3_witness_assertions_and_hostile_python_observations",
        "test_new_recorder.py": "round3_witness_assertions",
        "test_new_public_registration.py": "round3_witness_assertions",
        "test_identity_reuse.py": "round3_followup_assertions_with_allocator_observation",
        "test_prior_adversarial.py": "retained_round2_assertions",
        "test_recheck_edges.py": "retained_round2_assertions_with_old_diagnostics",
        "test_postconstruction_binding.py": "retained_round2_low_level_observations",
        "test_postconstruction_admission.py": "retained_round2_defect_assertion_expected_to_invert",
        "test_round2_adversarial.py": "retained_round2_assertions_with_interpreter_sensitive_exception",
        "test_replace_portable.py": "separate_portable_replacement_assertions",
        "round2_binding_source.py": "imported_frozen_round2_fixture_not_a_replay_target",
        "round2_recorder_source.py": "imported_frozen_round2_fixture_not_a_replay_target",
    },
    "claude": {
        "test_r3_anchor_probes.py": "round3_assertions_and_printed_hostile_python_observations",
        "test_r3_classification_proof.py": "round3_roster_assertions",
        "test_r3_cross_corpus_recorder.py": "round3_printed_record_observations",
        "test_r3_verified_basis.py": "round3_printed_byte_evidence_observations",
        "test_probe_recorder_residuals.py": "retained_round2_printed_recorder_observations",
        "test_r2_boundary_probes.py": "retained_round2_assertions_and_printed_observations",
        "test_codex_r2_round2_adversarial_copy.py": "two_report_selected_functions_from_copied_codex_round2_witness",
        "round2_binding_source.py": "imported_frozen_round2_fixture_not_a_replay_target",
        "round2_recorder_source.py": "imported_frozen_round2_fixture_not_a_replay_target",
        "sg2_child_preconditions.py": "standalone_historical_review_attestation_observation_not_pytest",
    },
}
QUEUES = {
    "codex": ["required_serial.py", "additional_serial.py", "complete_serial.py"],
    "claude": ["queue1.sh", "queue2.sh", "queue3.sh"],
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular non-symlink file: " + str(path))
    return path.read_bytes()


def source_metadata(path: Path, raw: bytes) -> dict:
    return {"path": str(path), "sha256": sha(raw), "bytes": len(raw)}


def functions(raw: bytes, filename: str) -> list[str]:
    tree = ast.parse(raw, filename=filename)
    return [node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")]


def imports(raw: bytes, filename: str) -> list[str]:
    tree = ast.parse(raw, filename=filename)
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            result.add(node.module)
    return sorted(result)


def groups(test_functions: dict[str, list[str]]) -> list[dict]:
    prefix = BUNDLE + "/tests/"

    def file(reviewer, name):
        return prefix + reviewer + "/" + name

    guard = "tests/codex/test_new_guard.py"
    residual = "test_registry_forgery_is_the_documented_hostile_python_residual"
    if residual not in test_functions[guard]:
        raise ValueError("the reviewed hostile-Python observation function is missing")
    selected_codex = [file("codex", "test_new_guard.py") + "::" + name
                      for name in test_functions[guard] if name != residual]
    return [
        {"name": "codex-round3-assertions", "reviewer": "codex", "targets": [
            *selected_codex, file("codex", "test_new_recorder.py"),
            file("codex", "test_new_public_registration.py"),
            file("codex", "test_identity_reuse.py")],
         "interpretation": "Refusal/assertion evidence; allocator reuse must additionally be observed, not inferred from a pass."},
        {"name": "codex-hostile-python-observations", "reviewer": "codex", "targets": [
            file("codex", "test_new_guard.py") + "::" + residual],
         "interpretation": "Tests intentionally rewrite the private registry and expect authority access. A pass confirms the documented residual, not isolation against arbitrary Python."},
        {"name": "codex-retained-round2", "reviewer": "codex", "targets": [
            file("codex", name) for name in (
                "test_prior_adversarial.py", "test_recheck_edges.py",
                "test_round2_adversarial.py", "test_replace_portable.py")],
         "interpretation": "Literal historical assertions retained. Three locator-message failures and one Python-version-specific init=False exception failure occurred at d13; classify actual final outcomes without rewriting them."},
        {"name": "codex-retained-low-level-observations", "reviewer": "codex", "targets": [
            file("codex", "test_postconstruction_binding.py")],
         "interpretation": "Calls lower-level shared-generation helpers directly. A pass does not test the repaired public entry invariant."},
        {"name": "codex-retained-defect-observation", "reviewer": "codex", "targets": [
            file("codex", "test_postconstruction_admission.py")],
         "interpretation": "The original assertion expects a fake generation call. Early refusal intentionally inverts it; subsequent assertions receive no credit after failure."},
        {"name": "claude-round3-anchor-and-roster", "reviewer": "claude", "targets": [
            file("claude", "test_r3_anchor_probes.py"),
            file("claude", "test_r3_classification_proof.py")],
         "interpretation": "Mixed assertions and printed observations; hostile registry rewriting and inconclusive allocator loops are not clean-refusal evidence."},
        {"name": "claude-record-observations", "reviewer": "claude", "targets": [
            file("claude", name) for name in (
                "test_r3_verified_basis.py", "test_r3_cross_corpus_recorder.py",
                "test_probe_recorder_residuals.py")],
         "interpretation": "Mostly printed observations. Inspect retained records/output separately; successful pytest phases do not prove basis wording or even successful CLI recording."},
        {"name": "claude-retained-boundary", "reviewer": "claude", "targets": [
            file("claude", "test_r2_boundary_probes.py")],
         "interpretation": "Mixed direct refusal assertions and printed old bypass probes. Preserve actual diagnostics and do not infer assertions from test names."},
        {"name": "claude-retained-codex-selected", "reviewer": "claude", "targets": [
            file("claude", "test_codex_r2_round2_adversarial_copy.py") + "::" + name
            for name in ("test_owner_counterpart_cannot_select_a_different_file",
                         "test_private_anchor_replacement_cannot_restore_spend")],
         "interpretation": "Exactly the two functions selected by Claude queue2; they duplicate Codex evidence and are not extra unique cases."},
    ]


NOTES = """# Byte-exact round-3 reviewer witnesses for round-4 task 9

This bundle copies the witnesses selected by the two review reports and their
saved serial queues. `manifest.json` binds the original full paths, copied
bytes, reports, queue sources, local import closure and generated target lists.
No witness is edited, imported or executed by the copy helper. Original scratch
files remain untouched. This is preparation, not test or acceptance evidence.

Run each `targets/*.json` through the existing pinned review runner with
`--targets-json`, from its final archive, with at most two workers. Keep separate
processes for the two reviewers: they use bare `round2_binding_source` and
`round2_recorder_source` imports. Pytest's normal prepend import mode admits the
sibling copied helpers. Those helpers have historical test functions but are
dependencies only, not extra test targets. The final archive's `tests.*`
fixtures and production modules remain the runtime inputs, not copied old
implementations. Their preparation-time hashes are informational; the runner's
final source snapshot is authoritative. No new test counts are claimed until
collection under that final source.

## Interpret the original outcomes literally

- Codex's two public `build_phase` witnesses and two native registration cases
  should now refuse before reads/authority; the committed round-4 regressions
  independently assert that behavior.
- Claude's nested in-place edit should record `asserted`, the current bundle
  digest and unverified input gaps. Its unchanged nested control can verify the
  bundle against the bound chunk digest, while source/chunk sidecar gaps remain.
  Root-relative rendering stays asserted. The original witness only prints
  these facts and can pass even after a CLI error. The new committed recorder
  regressions provide assertions; a probe pass alone does not prove the flip.
- Cross-corpus records remain caller-asserted; they do not establish consumption
  of the old corpus. Passing observations are not added to acceptance counts.
- The retained locator regex can expect a later authority diagnostic instead
  of the earlier D76 refusal. The old fake-create defect assertion should fail
  after the repaired guard. The original `dataclasses.replace(init=False)`
  expectation is interpreter-sensitive; a separate portable probe is retained.
  Do not change an original witness or count unreachable assertions as passed.
- Registry forgery intentionally rewrites private internals and remains outside
  the invariant's hostile-Python guarantee. Allocator loops that never observe
  reuse are inconclusive on reuse even if their other assertions pass.

## Capture and SG2 limitations

The unchanged runner captures passing stdout without enabling passing-test JUnit
logs. Its phase ledger therefore cannot establish printed wording flips. Use
the committed round-4 assertion tests and retained output records for those
claims; if observations are separately logged, identify that execution rather
than pretending it came from an unlogged passing phase.

`tests/claude/sg2_child_preconditions.py` is a standalone diagnostic, not a pytest test.
It accepts CHECKOUT, NON_GIT_COPY and FRESH_TEMP arguments and creates only its
temporary Git repository. It demonstrates `d76_suite_common.source()` review
attestation preconditions, which intentionally remain strict. Its statement
that ordinary SG2 tests inherit those preconditions is historical after round 4.
Keep it unchanged and report that limit. Do not call its absence of test cases a
successful replay, or invoke a new adapter with an obsolete `--layout` command.
Ordinary dirty-checkout and non-Git SG2 acceptance must instead use the final
generic utility and all three actual SG2 test nodes, with review attestation
explicitly off. The current strict review adapter is a separate opt-in path.

The reports' ordinary D76/SG2, run-lock and native-launch test references point
to committed repository tests. They are not copied into this bundle; task 9's
separate D76/ordering/journal coverage owns those tests. Historical queue scripts
are hashed as selection evidence, never executed by this bundler. Unused
`test_r2_classification_proof.py` is not included: Claude's report-selected
round-3 replacement is `test_r3_classification_proof.py`.
"""


def inventory(directory: Path) -> dict:
    """Include ignored/hidden files and reject symlinks before moving payloads."""
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('bundle symlink is unsupported: ' + str(path))
        if path.is_file():
            raw = regular_bytes(path)
            result[str(path.relative_to(directory))] = {'sha256': sha(raw), 'bytes': len(raw)}
        elif not path.is_dir():
            raise ValueError('bundle contains a nonregular entry: ' + str(path))
    return result


def relocate_existing(repo: Path, execution: Path, expected: str, report: Path) -> int:
    """R4-I18: preserve payload bytes while making their test-only placement explicit."""
    destination = repo / BUNDLE
    if destination.resolve(strict=True) != destination:
        raise ValueError('physical bundle path required')
    if (not report.is_absolute() or '..' in report.parts or report.exists() or report.is_symlink()
            or report.parent.resolve(strict=True) != report.parent or report.is_relative_to(repo)):
        raise ValueError('fresh external physical report path required')
    manifest_path = destination / 'manifest.json'
    raw_manifest = regular_bytes(manifest_path)
    if sha(raw_manifest) != expected:
        raise ValueError('existing manifest SHA differs')
    manifest = json.loads(raw_manifest)
    if manifest['repository'] != str(repo) or manifest['source_execution_root'] != str(execution):
        raise ValueError('existing source/repository roots differ')
    if (destination / 'tests').exists() or (destination / 'tests').is_symlink():
        raise ValueError('relocated payload destination must be fresh')
    before = inventory(destination)
    expected_files = {'manifest.json', 'README.md'}
    payloads, originals, test_functions = [], {}, {}
    for row in manifest['files']:
        relative = Path(row['repository_relative_path']).relative_to(BUNDLE)
        if len(relative.parts) != 2 or relative.parts[0] not in FILES:
            raise ValueError('unexpected old payload path: ' + str(relative))
        reviewer, name = relative.parts
        if name not in {*FILES[reviewer], 'review-report.md'}:
            raise ValueError('unexpected payload name: ' + name)
        old = destination / relative
        new = destination / 'tests' / relative
        raw = regular_bytes(old)
        source = Path(row['source']['path'])
        if (row['destination'] != source_metadata(old, raw)
                or row['source'] != source_metadata(source, regular_bytes(source))
                or regular_bytes(source) != raw or row['bytes_equal'] is not True):
            raise ValueError('recorded/original payload bytes differ: ' + str(old))
        originals[source] = raw
        expected_files.add(str(relative))
        payloads.append((old, new, raw, row))
        if name.startswith('test_'):
            test_functions['tests/' + str(relative)] = functions(raw, str(source))
    expected_payloads = {reviewer + '/' + name for reviewer, names in FILES.items()
                         for name in [*names, 'review-report.md']}
    if {str(old.relative_to(destination)) for old, _, _, _ in payloads} != expected_payloads or len(payloads) != 24:
        raise ValueError('exact 24-file payload roster required')
    old_groups = manifest['replay_groups']
    new_groups = groups(test_functions)
    expected_groups = json.loads(json.dumps(old_groups))
    for group in expected_groups:
        group['targets'] = [target.replace(BUNDLE + '/', BUNDLE + '/tests/', 1) for target in group['targets']]
    if new_groups != expected_groups:
        raise ValueError('replay target change extends beyond the placement prefix')
    target_updates = []
    for row, old_group, new_group in zip(manifest['target_files'], old_groups, new_groups, strict=True):
        path = destination / 'targets' / (old_group['name'] + '.json')
        raw = regular_bytes(path)
        if row != source_metadata(path, raw) or json.loads(raw) != old_group['targets']:
            raise ValueError('existing target file differs: ' + str(path))
        expected_files.add(str(path.relative_to(destination)))
        target_updates.append((path, raw, json_bytes(new_group['targets'])))
    readme_path = destination / 'README.md'
    old_readme = regular_bytes(readme_path)
    new_readme = old_readme.replace(b'`claude/sg2_child_preconditions.py`',
                                   b'`tests/claude/sg2_child_preconditions.py`')
    if manifest['readme'] != source_metadata(readme_path, old_readme) or new_readme != NOTES.encode():
        raise ValueError('README change extends beyond the placement path')
    if set(before) != expected_files:
        raise ValueError('bundle inventory has missing/extra files')
    for row in [*manifest['reports'], *manifest['selection_queue_sources']]:
        path = Path(row['path'])
        raw = regular_bytes(path)
        if any(row[key] != source_metadata(path, raw)[key] for key in ('path', 'bytes', 'sha256')):
            raise ValueError('external selection evidence changed: ' + str(path))
        originals[path] = raw
    helper = Path(__file__).resolve(strict=True)
    helper_raw = regular_bytes(helper)
    proof = {'issue': 'R4-I18', 'complete': False, 'tests_executed': False,
             'before_manifest_sha256': expected, 'before_files': before,
             'producer': source_metadata(helper, helper_raw), 'payloads': []}
    with report.open('xb') as stream:
        stream.write(json_bytes(proof))
    try:
        # The first file is the canary: the same rename/readback path must
        # preserve its bytes before the other 23 files can move.
        for old, new, raw, row in payloads:
            if regular_bytes(old) != raw:
                raise ValueError('payload changed before relocation: ' + str(old))
            new.parent.mkdir(parents=True, exist_ok=True)
            if new.exists() or new.is_symlink():
                raise ValueError('payload destination is not fresh: ' + str(new))
            old.rename(new)
            if regular_bytes(new) != raw or old.exists():
                raise ValueError('relocated payload differs: ' + str(new))
            proof['payloads'].append({'before_path': str(old), 'after_path': str(new),
                                      'before_sha256': sha(raw), 'after_sha256': sha(regular_bytes(new)),
                                      'bytes': len(raw), 'byte_identical': True})
            if len(proof['payloads']) == 1:
                proof['canary'] = dict(proof['payloads'][0])
                report.write_bytes(json_bytes(proof))
            row['destination'] = source_metadata(new, raw)
            row['repository_relative_path'] = str(new.relative_to(repo))
        for reviewer in FILES:
            (destination / reviewer).rmdir()  # Only now-empty old directories.
        for path, old, new in target_updates:
            if regular_bytes(path) != old:
                raise ValueError('target changed during relocation')
            path.write_bytes(new)
            if regular_bytes(path) != new:
                raise ValueError('target write did not persist')
        readme_path.write_bytes(new_readme)
        if regular_bytes(readme_path) != new_readme:
            raise ValueError('README write did not persist')
        for row in manifest['local_import_closure']:
            for key in ('importer', 'destination'):
                row[key] = 'tests/' + row[key]
        manifest['replay_groups'] = new_groups
        manifest['target_files'] = [source_metadata(path, regular_bytes(path)) for path, _, _ in target_updates]
        manifest['readme'] = source_metadata(readme_path, new_readme)
        manifest['helper'] = source_metadata(helper, helper_raw)
        manifest['standalone_diagnostic']['path'] = BUNDLE + '/tests/claude/sg2_child_preconditions.py'
        manifest_path.write_bytes(json_bytes(manifest))
        if json.loads(regular_bytes(manifest_path)) != manifest:
            raise ValueError('manifest write did not persist')
        for path, raw in originals.items():
            if regular_bytes(path) != raw:
                raise ValueError('external original changed during relocation: ' + str(path))
        if regular_bytes(helper) != helper_raw:
            raise ValueError('producer changed during relocation')
        after = inventory(destination)
        expected_after = {('tests/' + name if name in expected_payloads else name) for name in before}
        if set(after) != expected_after:
            raise ValueError('relocated inventory differs')
        proof.update(complete=True, after_files=after, originals_unchanged=True,
                     after_manifest_sha256=sha(regular_bytes(manifest_path)))
    except Exception as exc:
        proof['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        report.write_bytes(json_bytes(proof))
    print(json.dumps({'report': str(report), 'sha256': sha(regular_bytes(report)),
                      'manifest_sha256': proof['after_manifest_sha256'], 'byte_identical_payloads': len(payloads),
                      'replay_groups': len(new_groups), 'tests_executed': False}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--relocate-existing", action="store_true")
    parser.add_argument("--before-manifest-sha256")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    execution = args.execution_root.resolve(strict=True)
    if args.relocate_existing:
        if not args.before_manifest_sha256 or args.report is None:
            parser.error('--relocate-existing requires --before-manifest-sha256 and --report')
        return relocate_existing(repo, execution, args.before_manifest_sha256, args.report)
    if args.before_manifest_sha256 or args.report:
        parser.error('relocation proof arguments require --relocate-existing')
    destination = repo / BUNDLE
    if destination.exists() or destination.is_symlink():
        raise ValueError("bundle destination must be fresh: " + str(destination))
    originals = {}
    prepared = []
    report_rows = []
    queues = []
    test_functions = {}
    local_imports = []
    fixture_modules = set()
    for reviewer, selected in FILES.items():
        source_dir = execution / "scratch-5213r3check" / reviewer / "scripts/adhoc"
        for name, role in selected.items():
            source = source_dir / name
            raw = regular_bytes(source)
            originals[source] = raw
            relative = "tests/" + reviewer + "/" + name
            imported = imports(raw, str(source))
            declared_tests = functions(raw, str(source))
            if name.startswith("test_"):
                test_functions[relative] = declared_tests
            for module in imported:
                local = source_dir / (module + ".py")
                if local.is_file():
                    if module + ".py" not in selected:
                        raise ValueError("uncopied local dependency: " + str(local))
                    local_imports.append({"importer": relative, "module": module,
                                          "destination": "tests/" + reviewer + "/" + module + ".py"})
                if module.startswith("tests."):
                    fixture_modules.add(module)
            prepared.append((source, relative, role, raw, imported, declared_tests))
        report = execution / "plans/reviews" / ("pr5213_d13c1711e_" + reviewer + "_recheck_2026-11-02.md")
        raw = regular_bytes(report)
        originals[report] = raw
        prepared.append((report, "tests/" + reviewer + "/review-report.md", "historical_report", raw, [], []))
        report_rows.append(source_metadata(report, raw))
        for name in QUEUES[reviewer]:
            path = source_dir / name
            raw = regular_bytes(path)
            originals[path] = raw
            queues.append({"reviewer": reviewer, **source_metadata(path, raw)})
    fixture_rows = []
    for module in sorted(fixture_modules):
        path = repo / (module.replace(".", "/") + ".py")
        raw = regular_bytes(path)
        fixture_rows.append({"module": module, "relative_path": str(path.relative_to(repo)),
                             **source_metadata(path, raw),
                             "role": "preparation_snapshot_only_use_final_archive_fixture"})
    replay_groups = groups(test_functions)
    for group in replay_groups:
        for target in group["targets"]:
            relative, _, function = target.removeprefix(BUNDLE + "/").partition("::")
            if relative not in test_functions or function and function not in test_functions[relative]:
                raise ValueError("replay target does not name a copied top-level test: " + target)
    helper = Path(__file__).resolve(strict=True)
    helper_raw = regular_bytes(helper)
    destination.mkdir(parents=True, exist_ok=False)
    copied = []
    for source, relative, role, raw, imported, declared_tests in prepared:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        actual = regular_bytes(target)
        if actual != raw:
            raise ValueError("copied bytes differ: " + str(target))
        copied.append({"source": source_metadata(source, raw),
                       "destination": source_metadata(target, actual),
                       "repository_relative_path": str(target.relative_to(repo)),
                       "bytes_equal": True, "role": role,
                       "imports": imported, "declared_test_functions": declared_tests})
    target_files = []
    for group in replay_groups:
        target = destination / "targets" / (group["name"] + ".json")
        target.parent.mkdir(exist_ok=True)
        raw = json_bytes(group["targets"])
        with target.open("xb") as stream:
            stream.write(raw)
        target_files.append(source_metadata(target, regular_bytes(target)))
    readme = destination / "README.md"
    with readme.open("x", encoding="utf-8") as stream:
        stream.write(NOTES)
    for path, raw in originals.items():
        if regular_bytes(path) != raw:
            raise ValueError("original changed during copying: " + str(path))
    if regular_bytes(helper) != helper_raw:
        raise ValueError("copy helper changed during execution")
    manifest = {
        "schema_version": 1, "date": DATE, "purpose": "PR #5213 round-4 task9 reviewer witness replay preparation",
        "reviewed_head": REVIEWED_HEAD, "source_execution_root": str(execution),
        "repository": str(repo), "bundle": str(destination),
        "helper": source_metadata(helper, helper_raw), "files": copied,
        "reports": report_rows, "selection_queue_sources": queues,
        "local_import_closure": local_imports, "runtime_fixture_preparation_snapshots": fixture_rows,
        "replay_groups": replay_groups, "target_files": target_files,
        "readme": source_metadata(readme, regular_bytes(readme)),
        "originals_unchanged_after_copy": True, "witnesses_executed": False,
        "acceptance": "not_assessed", "counts": "Final-source pytest collection required; no new count is inferred from AST functions.",
        "standalone_diagnostic": {
            "path": BUNDLE + "/tests/claude/sg2_child_preconditions.py",
            "argv": ["CHECKOUT", "NON_GIT_COPY", "FRESH_TEMP"],
            "pytest_target": False, "current_claim": "review-only source attestation preconditions, not ordinary SG2 portability",
        },
    }
    path = destination / "manifest.json"
    with path.open("xb") as stream:
        stream.write(json_bytes(manifest))
    persisted = regular_bytes(path)
    if json.loads(persisted) != manifest:
        raise ValueError("manifest round trip differs")
    print(json.dumps({"manifest": str(path), "sha256": sha(persisted),
                      "copied_files": len(copied), "replay_groups": len(replay_groups),
                      "originals_unchanged": True, "tests_executed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
