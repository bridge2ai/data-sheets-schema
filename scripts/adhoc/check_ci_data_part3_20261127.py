"""Verify PR 6396 Part 3 preservation, manifest delta and exact-file acceptance.

2026-11-27. Inputs: the committed 93707dc32 corpus and this checkout's validator.
Outputs: hashes, runner census, optional strict-validation logs and a JSON receipt
in a fresh evidence directory. No model calls or edits to published artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from check_ci_data_corpus_preservation_20261126 import INSTRUMENT, git, manifest_delta


BASELINE = "93707dc3230fc7db0678fade30e585fba7988c5c"
MEASURED = "b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9"
REVISED = "45324f05ef4360f95620c5e9a37d7896661321177242f700f25bd22fe72cf51b"
LABEL = "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep"
NEW = tuple(
    f"data/evaluation_llm/rubric20_semantic/label_aware/{INSTRUMENT}/"
    f"CHORUS_{LABEL}{rep}_evaluation.json" for rep in (1, 3)
)


def protected(name: str) -> bool:
    return (
        name.startswith("data/evaluation_llm/")
        and f"/label_aware/{INSTRUMENT}/" in name
        and "2026-11-22b_" in Path(name).name
        and name.endswith("_evaluation.json")
    ) or (
        name.startswith("data/evaluation_scope/2026-11-22b/")
        and (name.endswith(".scope.json") or name.endswith("/scorings.tsv"))
    )


def preservation(root: Path) -> dict:
    paths = ("data/evaluation_llm", "data/evaluation_scope/2026-11-22b")
    before = {p for p in git(root, "ls-tree", "-r", "--name-only", BASELINE,
                            "--", *paths).decode().splitlines() if protected(p)}
    current = {p for p in git(root, "ls-files", "--", *paths).decode().splitlines()
               if protected(p)}
    if before != current or len(before) != 46:
        raise ValueError("protected inventory differs from the 46 baseline files")
    files = {}
    for name in sorted(before):
        content = (root / name).read_bytes()
        if content != git(root, "show", f"{BASELINE}:{name}"):
            raise ValueError("protected bytes changed: " + name)
        files[name] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    return files


def runner_census(root: Path, files: dict) -> dict:
    evaluations = {p for p in files if p.startswith("data/evaluation_llm/")}
    if len(evaluations) != 30:
        raise ValueError("expected exactly 30 protected evaluations")
    counts = Counter()
    with (root / "data/evaluation_scope/2026-11-22b/scorings.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 30 or {row["path"] for row in rows} != evaluations:
        raise ValueError("TSV rows do not cover exactly the 30 evaluations")
    for row in rows:
        name = row["path"]
        doc = json.loads((root / name).read_text())
        runner = doc["scorer_instrument"]["runner_sha256"]
        if row["sha256"] != files[name]["sha256"] or row["accepting_runner_sha256"] != runner:
            raise ValueError("TSV byte or accepting-runner identity differs: " + name)
        if runner != (REVISED if name in NEW else MEASURED):
            raise ValueError("accepting runner differs from the authorized split: " + name)
        counts[runner] += 1
    return dict(sorted(counts.items()))


def validate_new(root: Path, output: Path) -> list[dict]:
    sys.path.insert(0, str(root / "src"))
    from data_sheets_schema.root_scope_definition import compose_definition
    definition, composition = compose_definition("rubric20-semantic", repo_root=root)
    definition_path = output / "rubric20-composed-v6.md"
    with definition_path.open("xb") as handle:
        handle.write(definition)
    env = dict(os.environ)
    for key in tuple(env):
        if key.endswith("_API_KEY") or key in {
            "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL",
        }:
            del env[key]
    env.update({"PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    results = []
    for rep, name in zip((1, 3), NEW):
        label = LABEL + str(rep)
        input_path = root / f"data/d4d_concatenated/claudecode_agent/{label}/CHORUS_d4d.yaml"
        scope_path = root / f"data/evaluation_scope/2026-11-22b/{label}/CHORUS.scope.json"
        command = [sys.executable, "-B", "scripts/validate_evaluation_schema.py",
                   "--file", name, "--rubric", "rubric20-semantic", "--semantic-version", "6.0",
                   "--input", str(input_path), "--scope-context", str(scope_path),
                   "--agent-definition", str(definition_path)]
        log_path = output / f"strict-rep{rep}.log"
        with log_path.open("x") as log:
            result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        text = log_path.read_text()
        accepted = result.returncode == 0 and f"VALID {name}: rubric20-semantic" in text
        results.append({"path": name, "command": command, "exit_code": result.returncode,
                        "accepted": accepted, "log": str(log_path), "composition": composition})
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--check-manifest", action="store_true")
    ap.add_argument("--validate-new", action="store_true")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    files = preservation(root)
    doc = {"baseline": BASELINE, "head": git(root, "rev-parse", "HEAD").decode().strip(),
           "protected_count": len(files), "protected_bytes_unchanged": True, "files": files,
           "runner_counts": runner_census(root, files), "nice_value": os.getpriority(os.PRIO_PROCESS, 0)}
    if args.check_manifest:
        doc["manifest"] = manifest_delta(root, BASELINE, {p: files[p] for p in NEW})
    if args.validate_new:
        doc["strict_validation"] = validate_new(root, output)
    if files != preservation(root):
        raise ValueError("protected artifacts changed during verification")
    doc["accepted"] = all(item["accepted"] for item in doc.get("strict_validation", []))
    receipt = output / "receipt.json"
    with receipt.open("x") as handle:
        json.dump(doc, handle, indent=2, sort_keys=True)
        handle.write("\n")
    saved = json.loads(receipt.read_text())
    print(json.dumps({"accepted": saved["accepted"], "protected_count": saved["protected_count"],
                      "manifest_added": saved.get("manifest", {}).get("added_count"),
                      "runner_counts": saved["runner_counts"], "receipt": str(receipt)}))
    raise SystemExit(0 if saved["accepted"] else 1)


if __name__ == "__main__":
    main()
