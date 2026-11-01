#!/usr/bin/env python3
# Purpose: reproduce and verify the scanner ConfigError fix for #5364's CI.
# Inputs: this checkout, local origin/main/A13 objects, prior acceptance ledger.
# Outputs: fresh validation logs, XML, scans and inertness evidence; 2026-10-29.
"""Run serially through validate_receipts_v5_merge_20261029.py --script."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import prove_receipts_v5_inertness_20261029 as inertness
import validate_receipts_v5_r4_r6_20261029 as acceptance

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes/receipts_v5_ci_validation_2026-10-29"
RUNNER = ROOT / "scripts/adhoc/receipts_v5_ci_offline_20261029.py"
SCANNER = ROOT / ".claude/skills/d4d-generation-specificity-audit/scan.py"
MAIN = "49dd8f0eb7d9a6a349fd3bab8749804786ddb82b"


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    assert path.stat().st_size


def command(args):
    return [sys.executable, "-S", "-B", str(RUNNER), *args]


def run(label, args, allowed=(0,)):
    started = time.monotonic()
    print(f"Starting {label}", flush=True)
    with (OUT / f"{label}.log").open("w") as log:
        result = subprocess.run(command(args), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    row = {"command": command(args), "returncode": result.returncode,
           "seconds": time.monotonic() - started, "load": os.getloadavg(),
           "receipts_sha256": hashlib.sha256((ROOT / "src/data_sheets_schema/receipts.py").read_bytes()).hexdigest()}
    save(f"{label}.execution.json", row)
    assert (OUT / f"{label}.log").stat().st_size
    print(f"Finished {label}: exit {result.returncode}, {row['seconds']:.1f}s", flush=True)
    assert result.returncode in allowed, (label, result.returncode)


def test_counts(path):
    counts = Counter()
    for case in ET.parse(path).getroot().iter("testcase"):
        counts["failed" if case.find("failure") is not None or case.find("error") is not None
               else "skipped" if case.find("skipped") is not None else "passed"] += 1
    return dict(counts)


def pytest(label, paths, extra=(), worker=None):
    # The suite forbids adding paths under notes/ during a pytest session.
    with tempfile.TemporaryDirectory(prefix=f"codex-v5ci-{label}-xml-") as temporary:
        xml = Path(temporary) / "pytest.xml"
        try:
            prefix = ["--script", str(worker), "--"] if worker else ["--"]
            run(label, [*prefix, *paths, *extra,
                        f"--basetemp={Path(tempfile.gettempdir()) / ('codex-v5ci-' + label + '-pt')}",
                        f"--junitxml={xml}"])
        finally:
            if xml.is_file():
                shutil.copyfile(xml, OUT / f"{label}.xml")
        assert xml.stat().st_size
        print(json.dumps(test_counts(xml), sort_keys=True), flush=True)


def related_modules():
    # Include ignored files: this inventory defines the scope of the coverage claim.
    found = subprocess.check_output(
        ["rg", "-l", "--hidden", "--no-ignore", "receipts|specificity", "tests", "-g", "*.py"],
        cwd=ROOT, text=True).splitlines()
    found = [path for path in found if Path(path).name.startswith("test_") or Path(path).name.endswith("_test.py")]
    return sorted(set(found) | {"tests/test_neutral_generation_schema.py", "tests/test_profiles.py",
                               "tests/test_external_dataset_onboarding.py"})


def scans(suffix=""):
    head_label, main_label = f"scan_head{suffix}", f"scan_main{suffix}"
    run(head_label, ["--script", str(SCANNER), "--", "--root", str(ROOT),
                    "--report", str(OUT / f"{head_label}.md"), "--json", str(OUT / f"{head_label}.json")], (0, 1))
    with tempfile.TemporaryDirectory(prefix="codex-v5ci-main-") as temporary:
        base = Path(temporary) / "main"
        base.mkdir()
        archive = Path(temporary) / "main.tar"
        inertness.git("archive", "--format=tar", f"--output={archive}", MAIN)
        subprocess.run(["tar", "-xf", str(archive), "-C", str(base)], check=True)
        assert (base / SCANNER.relative_to(ROOT)).read_bytes() == SCANNER.read_bytes()
        run(main_label, ["--script", str(base / SCANNER.relative_to(ROOT)), "--", "--root", str(base),
                        "--report", str(OUT / f"{main_label}.md"), "--json", str(OUT / f"{main_label}.json")], (0, 1))
    head, main = [json.loads((OUT / f"{label}.json").read_text()) for label in (head_label, main_label)]
    # Line positions can move when v5 code is added; compare the actual finding content.
    def key(hit):
        return json.dumps({k: v for k, v in hit.items() if k not in {"line", "end_line"}}, sort_keys=True)
    delta = Counter(map(key, head["violations"])) - Counter(map(key, main["violations"]))
    save(f"scan_comparison{suffix}.json", {"main": MAIN, "main_totals": main["totals"], "head_totals": head["totals"],
                                         "new_violations": [json.loads(k) for k in delta.elements()]})
    print(json.dumps({"main": main["totals"], "head": head["totals"], "new_violations": sum(delta.values())}), flush=True)
    assert not delta


def collect():
    # Root collection also discovers historical notes; keep its outcome distinct
    # from the complete tests/ collection used by the CI workflow.
    run("collect_root_resumed", ["--", ".", "--collect-only", "-q",
        f"--basetemp={Path(tempfile.gettempdir()) / 'codex-v5ci-collect-root'}"], (0, 2))
    run("collect_all_resumed", ["--", "tests", "--collect-only", "-q",
        f"--basetemp={Path(tempfile.gettempdir()) / 'codex-v5ci-collect-all'}"])
    inventory = {}
    for shard in (4, 6):
        run(f"collect_shard{shard}", ["--", "tests", "--collect-only", "-p", "utils.pytest_shard",
            f"--ci-shard={shard}/6", "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary",
            f"--basetemp={Path(tempfile.gettempdir()) / ('codex-v5ci-collect' + str(shard))}"])
        nodes = [line for line in (OUT / f"collect_shard{shard}.log").read_text().splitlines()
                 if line.startswith("tests/") and "::" in line]
        files = sorted({node.split("::", 1)[0] for node in nodes})
        assert nodes and files
        inventory[str(shard)] = {"tests": len(nodes), "modules": len(files), "nodeids": nodes,
                                 "receipt_scanner_modules": sorted(set(files) & set(related_modules()))}
        save("shard_selection.json", inventory)
        print(f"Shard {shard}/6: {len(nodes)} tests in {len(files)} modules", flush=True)


def checkpointed_related():
    modules = json.loads((OUT / "related_modules.json").read_text())
    source_hash = hashlib.sha256((ROOT / "src/data_sheets_schema/receipts.py").read_bytes()).hexdigest()
    inventory = {}
    for index, module in enumerate(modules):
        label = f"related_{index:02d}"
        execution, xml = OUT / f"{label}.execution.json", OUT / f"{label}.xml"
        prior = json.loads(execution.read_text()) if execution.is_file() else {}
        if prior.get("returncode") == 0 and prior.get("receipts_sha256") == source_hash and xml.is_file():
            assert test_counts(xml).get("failed", 0) == 0
            print(f"Retaining completed {module}", flush=True)
        else:
            if execution.exists() or xml.exists():
                attempt = 1
                while (OUT / f"{label}_attempt{attempt}").exists():
                    attempt += 1
                archived = OUT / f"{label}_attempt{attempt}"
                archived.mkdir()
                for suffix in ("log", "xml", "execution.json"):
                    path = OUT / f"{label}.{suffix}"
                    if path.exists():
                        path.rename(archived / path.name)
            try:
                pytest(label, [module], extra=("-vv", "--tb=short"))
            except AssertionError:
                # Keep the full roster running serially, with failures durable
                # as soon as their module completes rather than at batch exit.
                if not execution.is_file() or not xml.is_file():
                    raise
        inventory[label] = {"module": module, "tests": test_counts(xml),
                            "returncode": json.loads(execution.read_text())["returncode"]}
        save("related_checkpoints.json", inventory)
    assert all(row["returncode"] == 0 for row in inventory.values()), "related modules need isolated follow-up"


def verify_surviving_evidence():
    source_hash = hashlib.sha256((ROOT / "src/data_sheets_schema/receipts.py").read_bytes()).hexdigest()
    for label, expected in (("scanner", {"passed": 357}),
                            ("acceptance", {"passed": 899, "skipped": 19})):
        execution = json.loads((OUT / f"{label}.execution.json").read_text())
        assert execution["returncode"] == 0 and execution["receipts_sha256"] == source_hash
        assert test_counts(OUT / f"{label}.xml") == expected
    ledger = json.loads((OUT / "inertness/inertness.json").read_text())
    assert set(ledger["slices"]) == {"corpus", "report", "chorus", "assembly"}
    assert all(row["equal"] for row in ledger["slices"].values())
    base = (OUT / "inertness.log").read_text().splitlines()[0].rsplit(" in ", 1)[1] + "/a13"
    for kind in ("corpus", "report", "chorus"):
        for label, tree in (("base", base), ("head", str(ROOT))):
            raw = (OUT / f"inertness/raw/{kind}_{label}.json").read_bytes().replace(tree.encode(), b"<TREE>")
            assert hashlib.sha256(raw).hexdigest() == ledger["slices"][kind][f"{label}_sha256"]
    for label in ("base", "head"):
        assembly = json.loads((OUT / f"inertness/raw/assembly_{label}.json").read_text())
        for key, value in ledger["slices"]["assembly"]["identities"].items():
            assert assembly[key] == value
    assert not inertness.git("diff", ledger["head"], "--", "src/", "tests/")
    save("resumed_evidence_check.json", {"receipts_sha256": source_hash,
         "scanner": 357, "acceptance": {"passed": 899, "skipped": 19},
         "inertness": "all four saved comparisons reverified", "source_and_tests_unchanged": True})


def prepare():
    """Use only the existing local submodule, at the superproject's exact pin."""
    target = ROOT / "fairscape_models"
    source = ROOT.parent.parent / "data-sheets-schema/fairscape_models"
    pin = inertness.git("ls-tree", "HEAD", "fairscape_models").decode().split()[2]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == pin
    assert not list(target.iterdir()), "preserve any preexisting submodule files"
    subprocess.run(["git", "clone", "--shared", "--no-checkout", str(source), str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "-c", "core.hooksPath=/dev/null", "checkout", "--detach", pin], check=True)
    assert (target / "fairscape_models/rocrate.py").stat().st_size
    save("submodule.json", {"source": str(source), "commit": pin, "network": False})


def summarize():
    checkpoints = json.loads((OUT / "related_checkpoints.json").read_text())
    modules = json.loads((OUT / "related_modules.json").read_text())
    assert modules == sorted(set(related_modules()) - set(acceptance.modules())
                             - {"tests/test_generation_specificity_skill.py"})
    assert [row["module"] for row in checkpoints.values()] == modules
    source_hash = hashlib.sha256((ROOT / "src/data_sheets_schema/receipts.py").read_bytes()).hexdigest()
    primary_labels = ["scanner_resumed", "acceptance", *checkpoints, "offline_related"]
    primary, total, related = {}, Counter(), Counter()
    for label in primary_labels:
        counts = test_counts(OUT / f"{label}.xml")
        execution = json.loads((OUT / f"{label}.execution.json").read_text())
        assert execution["returncode"] == 0 and not counts.get("failed", 0), label
        assert execution["receipts_sha256"] == source_hash, label
        primary[label] = counts
        total.update(counts)
        if label in checkpoints:
            related.update(counts)
    assert primary["scanner_resumed"] == {"passed": 357}
    assert primary["acceptance"] == {"passed": 899, "skipped": 19}
    for label in ("collect_all_resumed", "collect_shard4", "collect_shard6"):
        assert json.loads((OUT / f"{label}.execution.json").read_text())["returncode"] == 0
    collected = sum(int(count) for count in re.findall(
        r"^tests/[^\n]+\.py: (\d+)$", (OUT / "collect_all_resumed.log").read_text(), re.M))
    assert collected
    root_errors = [line for line in (OUT / "collect_root_resumed.log").read_text().splitlines()
                   if line.startswith("ERROR ")]
    changed = inertness.git("diff", "--name-only", "93edcc76c").decode().splitlines()
    protected = [path for path in changed if path.startswith(("data/", "src/download/", ".claude/", ".github/"))
                 or path.endswith(("STATUS.md", "shared_generation.py")) or "decision" in path.lower()]
    assert not protected
    summary = {
        "tested_source_head": inertness.git("rev-parse", "HEAD").decode().strip(),
        "receipts_sha256": source_hash,
        "python": sys.version, "executable": sys.executable,
        "dependencies": {name: importlib.metadata.version(name) for name in ("pytest", "PyYAML", "linkml-runtime")},
        "poetry_lock_sha256": hashlib.sha256((ROOT / "poetry.lock").read_bytes()).hexdigest(),
        "primary_tests": primary, "primary_totals": dict(total), "related_totals": dict(related),
        "primary_module_count": len(modules) + len(acceptance.modules()) + 2,
        "related_modules": checkpoints, "acceptance_modules": acceptance.modules(),
        "collection": {"ci_tests": collected, "root_errors": root_errors,
                       "shards": json.loads((OUT / "shard_selection.json").read_text())},
        "historical_test_attempts": {path.stem: test_counts(path) for path in sorted(OUT.glob("*.xml"))
                                     if path.stem not in primary_labels},
        "executions": {path.name.removesuffix(".execution.json"): json.loads(path.read_text())
                       for path in sorted(OUT.glob("*.execution.json"))},
        "scan": json.loads((OUT / "scan_comparison_resumed.json").read_text()),
        "inertness": json.loads((OUT / "inertness/inertness.json").read_text()),
        "protected_paths_changed": protected,
        "limits": ["Local Python 3.13.12; CI uses Python 3.12.",
                   "Shard 4 and 6 selection collected exactly; complete shards were not executed.",
                   "Whole-root collection encounters historical optional-dependency/import/network errors; CI tests/ collection passes.",
                   "related.log is an interrupted pre-reboot attempt and contributes no passing test count.",
                   "Inertness uses the same four prior scopes and path normalization; the known N11 assembly difference is outside those identity keys."],
        "artifact_sha256": {str(path.relative_to(OUT)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "validation.json"},
    }
    save("validation.json", summary)
    print(json.dumps({"tests": summary["primary_totals"], "related": summary["related_totals"],
                      "ci_collected": collected, "root_collection_errors": len(root_errors),
                      "new_violations": summary["scan"]["new_violations"]}, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("scanner", "acceptance", "related", "checkpointed_related", "selected", "verify_surviving", "offline_related", "scan", "rescan", "inertness", "prepare", "collect", "shard4", "shard6", "summarize"))
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    phase = options.phase
    OUT.mkdir(exist_ok=True)
    if phase == "scanner":
        pytest("scanner", ["tests/test_generation_specificity_skill.py"])
    elif phase == "acceptance":
        pytest("acceptance", acceptance.modules())
    elif phase == "related":
        modules = sorted(set(related_modules()) - set(acceptance.modules()) - {"tests/test_generation_specificity_skill.py"})
        save("related_modules.json", modules)
        pytest("related", modules)
    elif phase == "checkpointed_related":
        checkpointed_related()
    elif phase == "selected":
        label, *nodes = options.extra
        assert label.isidentifier() and nodes
        pytest(label, nodes, extra=("-vv", "--tb=short"))
    elif phase == "verify_surviving":
        verify_surviving_evidence()
    elif phase == "offline_related":
        pytest("offline_related", ["notes/matched_cborg_2026-09-13/native_controls/test_native_phase_history.py"],
               worker=ROOT / "scripts/adhoc/receipts_v5_ci_notes_20261029.py")
    elif phase == "scan":
        scans()
    elif phase == "rescan":
        scans("_resumed")
    elif phase == "inertness":
        inertness.OUT = OUT / "inertness"
        (inertness.OUT / "raw").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="codex-v5ci-a13-") as temporary:
            base, chorus = inertness.rebuild_inputs(Path(temporary))
            # prove(full) first runs and verifies fresh one-record canaries.
            inertness.prove("full", base, chorus)
    elif phase == "collect":
        collect()
    elif phase == "prepare":
        prepare()
    elif phase.startswith("shard"):
        pytest(phase, ["tests"], ["-p", "utils.pytest_shard", f"--ci-shard={phase[-1]}/6",
               "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary"])
    else:
        summarize()


if __name__ == "__main__":
    main()
