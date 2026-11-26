"""Run six read-only selection previews and bind their evidence, issue 6385.

2026-11-26. Inputs: explicit tool/corpus/receipt roots and registered series.
Outputs: fresh stdout/stderr files and a JSON receipt under the supplied evidence
directory. Never runs a selection write, scorer, provider, or refused output.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60).decode().strip()


def snapshot(args):
    files = set()
    for project in args.projects:
        for number in (1, 2, 3):
            label = args.config + "_rep" + str(number)
            for method in (args.method, args.method + "_core"):
                directory = args.corpus_root / "data/d4d_concatenated" / method / label
                files.update(directory.glob(project + "_*.yaml"))
                files.update(directory.glob(project + "_reconciliation.md"))
            for family in ("rubric10", "rubric20"):
                name = project + "_" + label + "_evaluation.json"
                first = (args.corpus_root / "data/evaluation_llm" / (family + "_semantic") /
                         "label_aware" / args.instrument / name)
                files.add(first)
                for scoring in (2, 3):
                    files.add(args.corpus_root / "data/evaluation_repeats" / args.instrument /
                              ("scoring_rep" + str(scoring)) / (family + "_semantic") / name)
    for root in (args.baseline_receipts, args.repeat_receipts):
        for name in ("plan.json", "receipt.json"):
            files.update(root.glob("*/" + name))
        files.update(root.glob("export-manifests/*/manifest.json"))
        files.update(root.glob("replacement-attempts/*.json"))
    return {str(path): sha(path) for path in sorted(files)}


def section(text, title):
    marker = title + ":\n"
    if marker not in text:
        raise ValueError("preview omitted " + title)
    return json.JSONDecoder().raw_decode(text.split(marker, 1)[1])[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tool-root", "corpus-root", "python", "baseline-receipts", "repeat-receipts", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("config", "instrument", "method"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--projects", nargs=5, required=True)
    args = parser.parse_args()
    for value in [*args.projects, args.method, args.config, args.instrument]:
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", value):
            raise ValueError("series identifiers must be single path components")
    if len(set(args.projects)) != 5:
        raise ValueError("five distinct projects are required")
    output_root = args.evidence.resolve()
    for supplied in (args.tool_root, args.corpus_root, args.baseline_receipts, args.repeat_receipts):
        protected = supplied.resolve()
        if output_root == protected or protected in output_root.parents or output_root in protected.parents:
            raise ValueError("evidence must be disjoint from source, corpus and receipt inputs")
    if git(args.tool_root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("commit source changes before running the real-data previews")
    args.evidence.mkdir(parents=True, exist_ok=False)
    before = snapshot(args)
    (args.evidence / "before.json").write_text(json.dumps(before, indent=2, sort_keys=True) + "\n")
    source_head = git(args.tool_root, "rev-parse", "HEAD")
    corpus_head = git(args.corpus_root, "rev-parse", "HEAD")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(args.tool_root / "src"),
               GIT_OPTIONAL_LOCKS="0")
    common = ["--method", args.method, "--config", args.config, "--score-instrument", args.instrument,
              "--score-receipts", str(args.baseline_receipts), "--score-receipts", str(args.repeat_receipts)]
    prefix = [str(args.python), "-B", "-m", "data_sheets_schema.cli", "runs"]
    commands = [("variation", prefix + ["score-variation", *common])]
    commands += [(project, prefix + ["select", "--project", project,
                                    "--score-policy", "score_gap_v1", *common]) for project in args.projects]
    results, preview_problem = [], None
    for name, command in commands:
        assert "--execute" not in command
        stdout, stderr = args.evidence / (name + ".stdout"), args.evidence / (name + ".stderr")
        start = time.monotonic()
        with stdout.open("xb") as out, stderr.open("xb") as err:
            completed = subprocess.run(command, cwd=args.corpus_root, env=env, stdout=out, stderr=err, timeout=1800)
        item = {"name": name, "argv": command, "exit_code": completed.returncode,
                "wall_seconds": time.monotonic() - start, "stdout": str(stdout), "stderr": str(stderr),
                "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)}
        results.append(item)
        print(json.dumps(item), flush=True)
        if completed.returncode != 0:
            break
        if name == "variation":
            table = section(stdout.read_text(), "Series evidence")
            cells = [cell for row in table for rubric in row["rubrics"].values() for cell in rubric["scorings"]]
            if len(cells) != 90 or any(cell["status"] != "measured" for cell in cells):
                preview_problem = "variation canary did not establish 90 measured cells; project previews not run"
                break
        else:
            policy = section(stdout.read_text(), "Score policy")
            if policy.get("name") != "score_gap_v1" or len(policy.get("candidates", [])) != 3:
                preview_problem = "project preview did not retain its three-candidate policy record"
                break
    after = snapshot(args)
    receipt = {"source_head": source_head, "corpus_head": corpus_head,
               "inputs_unchanged": after == before, "input_count": len(before), "outputs": results,
               "source_head_unchanged": git(args.tool_root, "rev-parse", "HEAD") == source_head,
               "corpus_head_unchanged": git(args.corpus_root, "rev-parse", "HEAD") == corpus_head,
               "execute_commands": 0, "live_calls": 0, "preview_problem": preview_problem}
    successful = not preview_problem and len(results) == 6 and all(item["exit_code"] == 0 for item in results)
    if successful:
        variation_text = Path(results[0]["stdout"]).read_text()
        table, pooled = section(variation_text, "Series evidence"), section(variation_text, "Series variation")
        cells = [cell for row in table for rubric in row["rubrics"].values() for cell in rubric["scorings"]]
        receipt.update(measured_cells=sum(cell["status"] == "measured" for cell in cells),
                       replaced_cells=sum(cell["attempt"] == 2 for cell in cells), pooled=pooled,
                       T=2 * pooled["s"] * math.sqrt(2 / 3),
                       means={project: {row["label"]: row["paired"]["mean"] for row in table
                                        if row["project"] == project} for project in args.projects},
                       maximums={family: sorted({cell["maximum"] for row in table
                                                 for cell in row["rubrics"][family]["scorings"]})
                                 for family in ("rubric10", "rubric20")},
                       selections={item["name"]: section(Path(item["stdout"]).read_text(), "Score policy")
                                   for item in results[1:]})
    receipt["status"] = "PASSED" if successful and all(receipt[key] for key in
                       ("inputs_unchanged", "source_head_unchanged", "corpus_head_unchanged")) else "BLOCKED"
    destination = args.evidence / "receipt.json"
    with destination.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(destination), "sha256": sha(destination)}), flush=True)
    return 0 if receipt["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
