#!/usr/bin/env python3
"""Independently verify sixty repeat plans against accepted first scores.

2026-11-26, repeat-scoring assignment for PR 6366. Inputs are saved plans,
accepted first-run evidence and a before-inventory. Output is one fresh JSON
receipt. No scorer is imported or launched and no evaluation is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys


HEAD = "9452a5c49a0533d86c5e08c1093021036ef98830"
RUNNER = "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
ORCHESTRATOR = "scripts/adhoc/repeat_root_scope_scoring_20261126.py"
INSTRUMENT = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
FROZEN = {
    "rubric10-semantic": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20-semantic": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}
HEX = re.compile(r"[0-9a-f]{64}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(value):
    path = Path(os.path.abspath(value))
    require(not any(part.is_symlink() for part in (path, *path.parents)),
            "symlink in verification input")
    return path


def read(path):
    path = physical(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= 256 * 1024 * 1024,
            "verification input must be a bounded nonempty regular file")
    return path.read_bytes()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def document(path):
    raw = read(path)
    value = json.loads(raw, object_pairs_hook=pairs)
    require(isinstance(value, dict), "verification JSON must be a mapping")
    return value, sha(raw)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, timeout=60).stdout


def relative(path, root):
    return physical(path).relative_to(physical(root)).as_posix()


def change_argument(argv, flag, old, new):
    require(argv.count(flag) == 1, "expected one argument " + flag)
    index = argv.index(flag) + 1
    require(index < len(argv) and argv[index] == str(old), "unexpected path argument " + flag)
    argv[index] = str(new)


def relocated_plan(baseline, root, run):
    """Enumerate all permitted path changes, then compare the entire plan."""
    expected = deepcopy(baseline)
    old_root, old_run = physical(baseline["repo_root"]), physical(baseline["run_directory"])

    def under_root(value):
        return str(root / relative(value, old_root))

    def under_run(value):
        return str(run / relative(value, old_run))

    for field in ("repo_root", "runner", "output", "validation_cwd"):
        expected[field] = under_root(baseline[field])
    for field in ("run_directory", "working_directory", "codex_home"):
        expected[field] = under_run(baseline[field])
    for name, item in expected["inputs"].items():
        if name != "agent-definition.md":
            item["source"] = under_root(item["source"])
    for field in ("artifacts", "isolated_inputs"):
        expected[field] = {name: under_run(path) for name, path in baseline[field].items()}
    expected["validation_sha256"] = {under_root(path): digest
                                      for path, digest in baseline["validation_sha256"].items()}
    change_argument(expected["command"], "--cd", old_run / "working", run / "working")
    change_argument(expected["command"], "--output-last-message", old_run / "raw-response.json",
                    run / "raw-response.json")
    for flag, old, new in (
        ("--file", old_run / "candidate_evaluation.json", run / "candidate_evaluation.json"),
        ("--input", baseline["inputs"]["record.yaml"]["source"], expected["inputs"]["record.yaml"]["source"]),
        ("--agent-definition", old_run / "working/agent-definition.md", run / "working/agent-definition.md"),
        ("--scope-context", baseline["inputs"]["scope-context.json"]["source"],
         expected["inputs"]["scope-context.json"]["source"]),
    ):
        change_argument(expected["validation_command"], flag, old, new)
    if "caller-context.yaml" in baseline["inputs"]:
        change_argument(expected["validation_command"], "--context",
                        baseline["inputs"]["caller-context.yaml"]["source"],
                        expected["inputs"]["caller-context.yaml"]["source"])
    expected["commands_shell"] = [shlex.join(expected["command"]), shlex.join(expected["validation_command"])]
    return expected


def first_inventory(path):
    values = {}
    for line in read(path).decode().splitlines():
        digest, name = line.split(None, 1)
        require(HEX.fullmatch(digest) is not None and name not in values, "invalid before-inventory row")
        relative_path = PurePosixPath(name)
        require(not relative_path.is_absolute() and ".." not in relative_path.parts,
                "before-inventory path is not relative")
        values[name] = digest
    require(len(values) == 30, "before-inventory must contain thirty first scores")
    return values


def check_scorer_arguments(job):
    argv = job["scorer_argv"]
    require(isinstance(argv, list) and len(argv) % 2 == 0 and all(isinstance(x, str) for x in argv),
            "scorer argv must contain explicit option/value pairs")
    arguments = {}
    for index in range(0, len(argv), 2):
        flag = argv[index]
        require(flag.startswith("--") and flag not in arguments, "duplicate or positional scorer argument")
        arguments[flag] = argv[index + 1]
    plan, identity = job["plan"], job["plan"]["identity"]
    expected = {"--repo-root": plan["repo_root"], "--method-directory": identity["method"],
                "--label": identity["label"], "--record": plan["inputs"]["record.yaml"]["source"],
                "--rubric": identity["rubric"], "--semantic-version": "6.0",
                "--scope-context": plan["inputs"]["scope-context.json"]["source"],
                "--run-directory": plan["run_directory"], "--validation-venv": plan["validation_venv"],
                "--auth-file": plan["auth_file"]}
    if "caller-context.yaml" in plan["inputs"]:
        expected["--context"] = plan["inputs"]["caller-context.yaml"]["source"]
    require(set(arguments) == set(expected) | {"--codex-binary", "--poetry-binary", "--timeout"},
            "scorer argv field set differs")
    for flag, value in expected.items():
        require(arguments[flag] == value, "scorer argv disagrees with saved plan: " + flag)
    for flag, selected in (("--codex-binary", plan["command"][0]),
                           ("--poetry-binary", plan["validation_command"][0])):
        found = shutil.which(arguments[flag])
        require(found is not None and str(Path(found).absolute()) == selected, "scorer executable entrypoint differs")
    require(arguments["--timeout"].isdigit() and 0 < int(arguments["--timeout"]) <= 7200,
            "scorer timeout is outside its unchanged bound")


def verify(args):
    original = physical(args.original_root)
    batch, batch_sha = document(args.plans)
    require(batch.get("mode") == "REPEAT_PLAN" and batch.get("scorer_head") == HEAD and batch.get("job_count") == 60,
            "repeat plan must bind the original head and exactly sixty jobs")
    orchestration = {"path": str(original / ORCHESTRATOR), "sha256": sha(read(original / ORCHESTRATOR))}
    require(batch.get("orchestration") == orchestration and batch.get("accepted_canary_job") is None,
            "fresh plan helper identity or canary state differs")
    jobs = batch.get("jobs")
    require(isinstance(jobs, list) and len(jobs) == 60, "repeat roster length differs")
    before = first_inventory(args.evaluations_before)
    baselines, first_outputs = {}, set()
    baseline_paths = sorted(physical(args.baseline_runs).glob("*/plan.json"))
    require(len(baseline_paths) == 30, "expected exactly thirty immediate baseline run directories")
    for path in baseline_paths:
        plan, plan_sha = document(path)
        receipt_path = path.with_name("receipt.json")
        receipt, receipt_sha = document(receipt_path)
        identity = plan["identity"]
        key = (identity["d4d_file"], identity["rubric"])
        require(key not in baselines and identity["version"] == "6.0"
                and plan["instrument"] == INSTRUMENT, "duplicate or wrong baseline identity")
        require(physical(plan["repo_root"]) == original and physical(plan["run_directory"]) == path.parent,
                "baseline root or run path differs")
        require(receipt.get("status") == "VALIDATED_AND_PUBLISHED"
                and receipt.get("codex_exit") == receipt.get("validator_exit") == 0
                and receipt.get("auth_copy_absent") is True, "baseline did not complete accepted scoring")
        require(receipt.get("plan_sha256") == sha(json.dumps(plan, sort_keys=True).encode()),
                "baseline receipt does not bind its plan")
        output = physical(plan["output"])
        name = relative(output, original)
        require(name in before and receipt.get("output") == str(output), "baseline output identity differs")
        digest = sha(read(output))
        require(digest == before[name] == receipt.get("output_sha256") == receipt.get("validator_input_sha256"),
                "baseline output differs from accepted or inventoried bytes")
        require(sha(read(path.parent / "candidate_evaluation.json")) == digest,
                "baseline accepted snapshot differs")
        require(not (path.parent / "codex-home/auth.json").exists(), "baseline retained an authentication copy")
        require(not git(original, "ls-files", "--", name).strip(), "first score became tracked")
        first_outputs.add(name)
        baselines[key] = (plan, physical(path), plan_sha, physical(receipt_path), receipt_sha)
    require(first_outputs == set(before), "baseline output roster differs from before-inventory")

    roots, keys, ids, destinations = {}, set(), set(), set()
    runs, outputs, export_dirs, manifests = set(), set(), set(), set()
    streams, rows, git_hashes, source_hashes, executable_hashes = Counter(), [], {}, {}, {}

    def check_source(root, path, digest):
        name = relative(path, root)
        key = str(physical(path))
        if key not in source_hashes:
            source_hashes[key] = sha(read(path))
        require(source_hashes[key] == digest, "planned source bytes changed: " + name)
        if name not in git_hashes:
            git_hashes[name] = sha(git(root, "show", HEAD + ":" + name))
        require(git_hashes[name] == digest, "planned source differs from original scoring head: " + name)

    for job in jobs:
        require(isinstance(job, dict) and job.get("skip") is False, "fresh roster may not skip a scoring")
        require(job.get("orchestration") == orchestration, "job names another orchestration helper")
        scoring, generation = job["scoring_replicate"], job["generation_replicate"]
        require(type(scoring) is int and scoring in (2, 3) and type(generation) is int and generation in (1, 2, 3),
                "invalid scoring or generation replicate")
        plan = job["plan"]
        identity = plan["identity"]
        key = (identity["d4d_file"], identity["rubric"])
        require(key in baselines and (*key, scoring) not in keys, "unexpected or duplicate repeat job")
        keys.add((*key, scoring))
        require(isinstance(job["id"], str) and job["id"] and job["id"] not in ids, "duplicate job identifier")
        ids.add(job["id"])
        require(identity["label"].endswith(f"_rep{generation}"), "generation stream differs from record label")
        streams[generation] += 1
        baseline, base_path, base_sha, receipt_path, receipt_sha = baselines[key]
        require(physical(job["baseline_plan_path"]) == base_path and job["baseline_plan_sha256"] == base_sha
                and physical(job["baseline_receipt_path"]) == receipt_path
                and job["baseline_receipt_sha256"] == receipt_sha, "repeat baseline binding differs")
        root, run = physical(plan["repo_root"]), physical(plan["run_directory"])
        require(root != original and roots.setdefault(scoring, root) == root, "repeat checkout identity differs")
        require(plan == relocated_plan(baseline, root, run), "repeat plan changes more than enumerated paths")
        check_scorer_arguments(job)
        require(sha(plan["prompt"].encode()) == plan["prompt_sha256"], "prompt digest differs")
        require(plan["inputs"]["agent-definition.md"]["sha256"] == FROZEN[identity["rubric"]],
                "composed definition moved")
        require(relative(plan["runner"], root) == RUNNER, "runner path differs")
        check_source(root, plan["runner"], plan["runner_sha256"])
        for name, item in plan["inputs"].items():
            if name != "agent-definition.md":
                check_source(root, item["source"], item["sha256"])
        for path, digest in plan["validation_sha256"].items():
            check_source(root, path, digest)
        for prefix in ("source", "overrides"):
            provenance = plan["definition_provenance"]
            check_source(root, root / provenance[prefix + "_path"], provenance[prefix + "_sha256"])
        for path, digest in plan["executable_sha256"].items():
            if path not in executable_hashes:
                executable_hashes[path] = sha(read(Path(path).resolve(strict=True)))
            require(executable_hashes[path] == digest, "bound executable bytes changed")
        family = identity["rubric"].removesuffix("-semantic") + "_semantic"
        filename = f"{identity['project']}_{identity['label']}_evaluation.json"
        output = physical(plan["output"])
        require(output == root / "data/evaluation_llm" / family / "label_aware" / INSTRUMENT / filename,
                "repeat runner output differs from unchanged placement")
        destination = physical(job["destination"])
        require(destination == original / "data/evaluation_repeats" / INSTRUMENT / f"scoring_rep{scoring}" / family / filename,
                "repeat destination differs from isolated convention")
        export_dir, manifest = physical(job["export_directory"]), physical(job["manifest_path"])
        require(run.name == job["id"] and export_dir == run.parent / "export-manifests" / job["id"]
                and manifest == export_dir / "manifest.json", "private repeat evidence layout differs")
        for path, collection in ((run, runs), (output, outputs), (destination, destinations),
                                 (export_dir, export_dirs), (manifest, manifests)):
            require(path not in collection and not path.exists(), "repeat output is not unique and fresh")
            collection.add(path)
        rows.append({"id": job["id"], "scoring_replicate": scoring, "generation_replicate": generation,
                     "prompt_sha256": plan["prompt_sha256"], "baseline_plan_sha256": base_sha,
                     "baseline_receipt_sha256": receipt_sha, "destination": str(destination)})
    require(keys == {(*key, scoring) for key in baselines for scoring in (2, 3)}, "incomplete sixty-job roster")
    require(dict(streams) == {1: 20, 2: 20, 3: 20} and len(set(roots.values())) == 2,
            "expected three streams of twenty and two disjoint scoring checkouts")
    require(len(runs | outputs | destinations | export_dirs | manifests) == 300,
            "repeat paths alias another output role")
    for root in roots.values():
        require(git(root, "rev-parse", "HEAD").decode().strip() == HEAD, "repeat checkout moved from original head")
        require(physical(git(root, "rev-parse", "--show-toplevel").decode().strip()) == root,
                "scoring root is not the checkout root")
        require(not git(root, "status", "--porcelain", "--untracked-files=no").strip(), "repeat checkout has tracked edits")
        require(all(other == root or (root not in other.parents and other not in root.parents)
                    for other in (*roots.values(), original)), "scoring and original checkouts overlap")
        for path in runs | export_dirs:
            require(root != path and root not in path.parents and original not in path.parents,
                    "private run or export evidence overlaps a scoring or original checkout")
    for name, digest in before.items():
        require(sha(read(original / name)) == digest and not git(original, "ls-files", "--", name).strip(),
                "first-score bytes or untracked status changed during verification")
    observed = set()
    for family in ("rubric10_semantic", "rubric20_semantic"):
        directory = original / "data/evaluation_llm" / family / "label_aware" / INSTRUMENT
        observed.update(relative(path, original) for path in directory.glob("*_evaluation.json"))
    require(observed == set(before), "original first-score file inventory changed")
    for path, digest in source_hashes.items():
        require(sha(read(path)) == digest, "bound source changed during verification")
    for path, digest in executable_hashes.items():
        require(sha(read(Path(path).resolve(strict=True))) == digest, "bound executable changed during verification")
    require(sha(read(original / ORCHESTRATOR)) == orchestration["sha256"], "orchestration changed during verification")
    return {"status": "PASSED", "plans_sha256": batch_sha,
            "baseline_count": 30, "job_count": 60, "stream_counts": dict(streams),
            "scorer_head": HEAD, "scoring_checkouts": {str(key): str(value) for key, value in roots.items()},
            "orchestration": orchestration,
            "evaluations_before_sha256": sha(read(args.evaluations_before)),
            "original_evaluations_unchanged": True, "original_evaluations_untracked": True,
            "full_plan_equality_modulo_enumerated_paths": True, "jobs": rows,
            "unique_source_files_verified": len(source_hashes),
            "scoring_calls": 0, "evaluation_writes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plans", "baseline-runs", "evaluations-before", "original-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args)
        with physical(args.output).open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps({"status": "PASSED", "receipt": str(args.output),
                          "sha256": sha(read(args.output))}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
