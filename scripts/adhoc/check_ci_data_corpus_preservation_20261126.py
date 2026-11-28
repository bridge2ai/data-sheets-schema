"""Preserve the PR 6372/6396 corpus and bound generated-manifest changes.

2026-11-26. Inputs: tracked artifacts, a saved before ledger and optional baseline
commit. Outputs: JSON evidence in a caller-selected fresh path. No evaluation,
manifest or model output is modified. Serves the two data PR CI repairs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


INSTRUMENT = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
MANIFEST = "tests/data/evaluation_instruments.json"


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
    ).stdout


def inventory(root: Path, part: int) -> dict:
    paths = git(root, "ls-files", "-z", "--", "data/evaluation_llm",
                "data/evaluation_repeats", "data/evaluation_scope",
                "notes/root_scope_v6_scoring_variation_2026-11-26.md")
    selected = {}
    series = "2026-11-25c_" if part == 1 else "2026-11-22b_"
    for raw in paths.split(b"\0"):
        if not raw:
            continue
        name = raw.decode()
        evaluation = (name.startswith("data/evaluation_llm/")
                      and f"/label_aware/{INSTRUMENT}/" in name
                      and series in Path(name).name
                      and name.endswith("_evaluation.json"))
        if part == 1:
            repeat = (name.startswith(f"data/evaluation_repeats/{INSTRUMENT}/")
                      and (name.endswith("_evaluation.json") or name.endswith("/scorings.tsv")))
            protected = evaluation or repeat or name == "notes/root_scope_v6_scoring_variation_2026-11-26.md"
        else:
            scope = (name.startswith("data/evaluation_scope/2026-11-22b/")
                     and (name.endswith(".scope.json") or name.endswith("/scorings.tsv")))
            protected = evaluation or scope
        if protected:
            content = (root / name).read_bytes()
            selected[name] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    expected = 92 if part == 1 else 44
    if len(selected) != expected:
        raise SystemExit(f"protected inventory has {len(selected)} files; expected {expected}")
    return selected


def manifest_delta(root: Path, commit: str, files: dict) -> dict:
    old = json.loads(git(root, "show", f"{commit}:{MANIFEST}"))
    current = json.loads((root / MANIFEST).read_text())
    trimmed = json.loads(json.dumps(current))
    expected = {
        name.removeprefix("data/evaluation_llm/")
        for name in files if name.startswith("data/evaluation_llm/")
    }
    added = {}
    for rubric, block in current["rubrics"].items():
        old_entries = old["rubrics"][rubric]["evaluations"]
        for name, entry in block["evaluations"].items():
            if name in old_entries:
                continue
            qualified = rubric + "/" + name
            metadata = json.loads((root / "data/evaluation_llm" / qualified).read_text())["metadata"]
            if (entry.get("basis") != "recorded_composed_definition"
                    or entry.get("instrument_sha256") != metadata.get("instrument_sha256")):
                raise SystemExit("new manifest entry lacks the recorded composition identity: " + qualified)
            added[qualified] = entry
            del trimmed["rubrics"][rubric]["evaluations"][name]
    if set(added) != expected:
        raise SystemExit("new manifest entries differ from the protected new evaluations")
    if trimmed != old:
        raise SystemExit("existing manifest entries or non-entry metadata changed")
    return {"baseline_commit": commit, "added_count": len(added),
            "existing_entries_unchanged": True, "added_entries": added}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--part", type=int, choices=(1, 2), required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--verify", type=Path)
    ap.add_argument("--manifest-baseline")
    args = ap.parse_args()
    root = args.repo.resolve(strict=True)
    if args.output.exists():
        raise SystemExit("output must be fresh")
    files = inventory(root, args.part)
    doc = {"part": args.part, "head": git(root, "rev-parse", "HEAD").decode().strip(),
           "protected_count": len(files), "files": files}
    if args.verify:
        before = json.loads(args.verify.read_text())
        if before["part"] != args.part or before["files"] != files:
            raise SystemExit("protected paths or bytes changed")
        doc.update({"verified_against": str(args.verify), "protected_bytes_unchanged": True})
    if args.manifest_baseline:
        doc["manifest"] = manifest_delta(root, args.manifest_baseline, files)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2, sort_keys=True)
        handle.write("\n")
    saved = json.loads(args.output.read_text())
    print(json.dumps({"part": saved["part"], "protected_count": saved["protected_count"],
                      "protected_bytes_unchanged": saved.get("protected_bytes_unchanged"),
                      "manifest_added": saved.get("manifest", {}).get("added_count")}))


if __name__ == "__main__":
    main()
