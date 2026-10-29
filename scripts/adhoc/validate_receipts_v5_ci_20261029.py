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
RUNNER = ROOT / "scripts/adhoc/validate_receipts_v5_merge_20261029.py"
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


def pytest(label, paths, extra=()):
    # The suite forbids adding paths under notes/ during a pytest session.
    with tempfile.TemporaryDirectory(prefix=f"codex-v5ci-{label}-xml-") as temporary:
        xml = Path(temporary) / "pytest.xml"
        try:
            run(label, ["--", *paths, *extra,
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


def scans():
    run("scan_head", ["--script", str(SCANNER), "--", "--root", str(ROOT),
                      "--report", str(OUT / "scan_head.md"), "--json", str(OUT / "scan_head.json")], (0, 1))
    with tempfile.TemporaryDirectory(prefix="codex-v5ci-main-") as temporary:
        base = Path(temporary) / "main"
        base.mkdir()
        archive = Path(temporary) / "main.tar"
        inertness.git("archive", "--format=tar", f"--output={archive}", MAIN)
        subprocess.run(["tar", "-xf", str(archive), "-C", str(base)], check=True)
        assert (base / SCANNER.relative_to(ROOT)).read_bytes() == SCANNER.read_bytes()
        run("scan_main", ["--script", str(base / SCANNER.relative_to(ROOT)), "--", "--root", str(base),
                          "--report", str(OUT / "scan_main.md"), "--json", str(OUT / "scan_main.json")], (0, 1))
    head, main = [json.loads((OUT / f"scan_{label}.json").read_text()) for label in ("head", "main")]
    # Line positions can move when v5 code is added; compare the actual finding content.
    def key(hit):
        return json.dumps({k: v for k, v in hit.items() if k not in {"line", "end_line"}}, sort_keys=True)
    delta = Counter(map(key, head["violations"])) - Counter(map(key, main["violations"]))
    save("scan_comparison.json", {"main": MAIN, "main_totals": main["totals"], "head_totals": head["totals"],
                                  "new_violations": [json.loads(k) for k in delta.elements()]})
    print(json.dumps({"main": main["totals"], "head": head["totals"], "new_violations": sum(delta.values())}), flush=True)
    assert not delta


def collect():
    for shard in (4, 6):
        run(f"collect_shard{shard}", ["--", "tests", "--collect-only", "-p", "utils.pytest_shard",
            f"--ci-shard={shard}/6", "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary",
            f"--basetemp={Path(tempfile.gettempdir()) / ('codex-v5ci-collect' + str(shard))}"])


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("scanner", "acceptance", "related", "scan", "inertness", "prepare", "collect", "shard4", "shard6", "summarize"))
    phase = parser.parse_args().phase
    OUT.mkdir(exist_ok=True)
    if phase == "scanner":
        pytest("scanner", ["tests/test_generation_specificity_skill.py"])
    elif phase == "acceptance":
        pytest("acceptance", acceptance.modules())
    elif phase == "related":
        modules = sorted(set(related_modules()) - set(acceptance.modules()) - {"tests/test_generation_specificity_skill.py"})
        save("related_modules.json", modules)
        pytest("related", modules)
    elif phase == "scan":
        scans()
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
        save("validation.json", {
            "head": inertness.git("rev-parse", "HEAD").decode().strip(),
            "python": sys.version, "executable": sys.executable,
            "dependencies": {name: importlib.metadata.version(name) for name in ("pytest", "PyYAML", "linkml-runtime")},
            "poetry_lock_sha256": hashlib.sha256((ROOT / "poetry.lock").read_bytes()).hexdigest(),
            "tests": {path.stem: test_counts(path) for path in sorted(OUT.glob("*.xml"))},
            "scan": json.loads((OUT / "scan_comparison.json").read_text()),
            "inertness": json.loads((OUT / "inertness/inertness.json").read_text()),
            "artifact_sha256": {str(path.relative_to(OUT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "validation.json"},
        })


if __name__ == "__main__":
    main()
