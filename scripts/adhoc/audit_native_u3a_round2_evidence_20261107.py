#!/usr/bin/env python3
"""Audit retained U3-A round-2 mutation evidence; 2026-11-07.

Inputs: explicit evidence root, frozen campaign base, selected cases, optional
prior single-MA audit. Outputs: one new exclusive JSON directly under that root.
Reads existing artifacts and local Git objects only. No imports of repository
code, archive copies, mutations, tests, native programs, providers or network.
Preserves the read/hash/Git-object and JSON/XML comparison method used in the
independent evidence audit. MG is invocation coverage; MO retains a deeper refusal.
Original audited campaign base: ff53b3f4fc0bd594f1585a38a662aa487aeb3629.
The final regression head was 5912b5713c5104c5094aec3bdb3713f3c7d6d807;
that later regression is separate evidence, not a rerun of this mutation campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

CASES = ("MA", "MB", "MC", "MD", "ME", "MF", "MG", "MI", "MJ", "MK", "ML", "MM", "MN", "MO", "MP")
SOURCE = "src/data_sheets_schema/native_execution_registration_v2.py"
HARNESS = "scripts/adhoc/mutate_native_u3a_round2_20261107.py"
RUNNER = "scripts/adhoc/run_native_u3a_tests_20261107.py"
PROFILE = b"(version 1)\n(allow default)\n(deny network*)\n"
MAX_BYTES = 16 * 1024 * 1024
FAILURE_TEXT = {
    **{case: "DID NOT RAISE" for case in ("MA", "MB", "MC", "MD", "MN", "MP")},
    "ME": "dirty closure reached consumer",
    "MF": "unsupported committed consumer admitted",
    "MG": "assert []",
    **{case: "mismatched E/C reached consumer" for case in ("MI", "MJ", "MK", "ML", "MM")},
    "MO": "Regex pattern did not match",
}
MECHANISM = {
    **{case: "The expected refusal disappears." for case in ("MA", "MB", "MC", "MD", "MN", "MP")},
    "ME": "Removing committed-source proof reaches the deliberate dirty-closure consumer trap.",
    "MF": "Removing the version guard admits the unsupported-version test consumer.",
    "MG": "Invocation-contract kill: the mandatory pinned require_envelope call is omitted; this does not establish acceptance of a malformed envelope.",
    **{case: "Removing the join guard reaches the deliberate mismatched-E/C consumer trap."
       for case in ("MI", "MJ", "MK", "ML", "MM")},
    "MO": "Early-error specificity kill: the removed outer source-pin refusal is replaced by a deeper import-graph pin refusal. Changed source is still rejected.",
}


class Refusal(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_bytes(path, artifacts):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and path.resolve(strict=True) == path, "not a physical regular artifact: " + str(path))
    before = path.stat()
    require(before.st_size <= MAX_BYTES, "artifact exceeds read bound: " + str(path))
    raw = path.read_bytes()
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    require(tuple(getattr(before, field) for field in fields)
            == tuple(getattr(after, field) for field in fields), "artifact changed during read: " + str(path))
    artifacts[str(path)] = sha(raw)
    return raw


def document(path, artifacts):
    value = json.loads(load_bytes(path, artifacts))
    require(type(value) is dict, "JSON artifact is not an object: " + str(path))
    return value


def git(tree, *args):
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "",
           "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(
        ["/usr/bin/git", "--no-replace-objects", "--no-optional-locks",
         "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *args],
        cwd=tree, env=env, capture_output=True, timeout=30, check=False)
    require(result.returncode == 0, "local Git object inspection failed: " + " ".join(args))
    require(len(result.stdout) <= MAX_BYTES, "Git object output exceeds bound")
    return result.stdout


def quiet(root):
    require(not (root / "plans/native_quiet_window.lock").exists(), "quiet-window lock exists")


def origin_check(value, tree, evidence):
    wanted = str(tree / "src/data_sheets_schema")
    require(value.get("package_paths") and
            all(path == wanted for path in value["package_paths"]), "foreign/empty package namespace")
    require(type(value.get("module_origins")) is dict and
            all(Path(path).is_relative_to(wanted) for path in value["module_origins"].values()),
            "foreign production module origin")
    require(value.get("editable_finders") == [], "editable finder is active")
    require(all(value.get(key) is True for key in ("dont_write_bytecode", "no_user_site", "safe_path")),
            "interpreter isolation witness failed")
    require(value.get("python") == str(evidence / "venv/bin/python")
            and value.get("prefix") == str(evidence / "venv"), "wrong evidence interpreter")


def junit(raw):
    root = ET.fromstring(raw)
    cases = list(root.iter("testcase"))
    failures = [failure for case in cases for failure in case.findall("failure")]
    return {"tests": len(cases), "failures": len(failures),
            "errors": sum(len(case.findall("error")) for case in cases),
            "skipped": sum(len(case.findall("skipped")) for case in cases),
            "failure_messages": [item.get("message", "") for item in failures],
            "failure_text": ["".join(item.itertext()) for item in failures],
            "failed_nodes": [case.get("name", "") for case in cases if case.find("failure") is not None]}


def audit_arm(root, case, arm, record, artifacts):
    evidence = root / ("scratch-native-u3a-r2-mutation-" + case + "-01-" + arm)
    tree = root / ("scratch-native-u3a-r2-mutation-" + case + "-01-source")
    declared = record[arm]
    require(declared["evidence"] == str(evidence), "record evidence path differs from literal case path")
    outcome = document(evidence / "outcome.json", artifacts)
    network = document(evidence / "network.json", artifacts)
    plan = document(evidence / "plan.json", artifacts)
    bootstrap = document(evidence / "bootstrap.json", artifacts)
    before = document(evidence / "origins-before.json", artifacts)
    after = document(evidence / "origins-after.json", artifacts)
    child = document(evidence / "subprocess-origins.json", artifacts)
    counts = junit(load_bytes(evidence / "pytest.xml", artifacts))
    log = load_bytes(evidence / "pytest.log", artifacts).decode("utf-8")
    profile = load_bytes(evidence / "network-denied.sb", artifacts)
    require(artifacts[str(evidence / "outcome.json")] == declared["outcome_sha256"]
            and artifacts[str(evidence / "pytest.xml")] == declared["junit_sha256"],
            "outcome/JUnit hash differs from result pin")
    require(profile == PROFILE and sha(profile) == plan["sandbox_sha256"], "sandbox profile differs")
    require(outcome.get("cleanup_verified") is True and outcome.get("forced_cleanup") is False
            and outcome.get("interrupted") is None and outcome.get("observation_errors") == []
            and outcome.get("observed_surviving_pids") == [], "observed cleanup is incomplete")
    require(outcome.get("worker", {}).get("source_origin_checks_passed") is True,
            "worker source-origin checks failed")
    require(network.get("network_bind_denied") is True and network.get("errno") == 1
            and child.get("network", {}).get("network_bind_denied") is True
            and child["network"].get("errno") == 1, "network denial witness failed")
    for witness in (before, after, child["origins"]):
        origin_check(witness, tree, evidence)
    expected_commit = record["base"] if arm == "baseline" else record["mutant_commit"]
    require(plan["source_commit"] == expected_commit and plan["source_root"] == str(tree),
            "source commit/root witness differs")
    require(plan["workers"] == 0 and plan["deadline_seconds"] == 3600, "unexpected execution budget")
    expected_env = {
        "PATH": str(evidence / "venv/bin") + ":/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(evidence / "home"), "TMPDIR": str(evidence / "tmp"), "LANG": "en_US.UTF-8",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_NO_LAZY_FETCH": "1",
        "PYTEST_ADDOPTS": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "UV_OFFLINE": "1", "PIP_NO_INDEX": "1"}
    require(plan["environment"] == expected_env, "environment differs from credential-free allowlist")
    command = ["/usr/bin/sandbox-exec", "-f", str(evidence / "network-denied.sb"),
               str(evidence / "venv/bin/python"), "-P", "-B", str(tree / RUNNER),
               "--worker", "--out", str(evidence), "--workers", "0", record["test_node"]]
    require(plan["command"] == command, "saved command differs from exact isolated test path")
    require(sha(load_bytes(tree / RUNNER, artifacts)) == plan["runner_sha256"], "runner source changed")
    require(bootstrap["test_python"] == str(evidence / "venv/bin/python")
            and bootstrap["paths"] == [str(tree / "src"), str(tree), bootstrap["dependency_site"]],
            "bootstrap source paths differ")
    require(len(bootstrap["files"]) == 3, "unexpected bootstrap file roster")
    names = set()
    for filename, digest in bootstrap["files"].items():
        path = Path(filename)
        require(path.is_relative_to(evidence / "venv"), "bootstrap pin escaped evidence venv")
        names.add(path.name)
        require(sha(load_bytes(path, artifacts)) == digest, "bootstrap file differs from pin")
    require(names == {"sitecustomize.py", "u3a_paths.pth", "pyvenv.cfg"}, "bootstrap file names differ")
    expected_tests = 10 if case == "MP" else 1
    expected_failures = (4 if case == "MP" else 1) if arm == "mutant" else 0
    for key in ("tests", "failures", "errors", "skipped"):
        require(counts[key] == declared[key], "JUnit count differs from saved result: " + key)
    require(counts["tests"] == expected_tests and counts["failures"] == expected_failures
            and counts["errors"] == 0 and counts["skipped"] == 0, "unexpected actual JUnit outcome")
    expected_rc = 1 if arm == "mutant" else 0
    require(outcome["returncode"] == declared["returncode"] == expected_rc
            and outcome["worker"]["returncode"] == expected_rc, "return-code witness differs")
    if arm == "baseline":
        require(re.search(r"\b" + str(expected_tests) + r" passed\b", log), "baseline log lacks passing summary")
    else:
        require(all(FAILURE_TEXT[case] in message for message in counts["failure_messages"]),
                "mutant failed for an unrelated reason")
        require(re.search(r"\b" + str(expected_failures) + r" failed\b", log), "mutant log lacks failure summary")
        if case == "MG":
            require("assert observed == [preparation]" in log, "MG is not the stated invocation check")
        if case == "MO":
            require("consumer import graph source differs from its pin" in log
                    and "consumer source differs from the committed package closure" in log,
                    "MO does not establish the documented redundant refusal")
        if case == "MP":
            for parameter in ("digest-", "missing_large-", "extra_workflow-", "scalar_digest-"):
                require(sum("[" + parameter in node for node in counts["failed_nodes"]) == 1,
                        "MP failed a different parameter: " + parameter)
    return {key: counts[key] for key in ("tests", "failures", "errors", "skipped")} | {
        "passed": counts["tests"] - counts["failures"], "failure_messages": counts["failure_messages"],
        "evidence": str(evidence), "cleanup": "verified for observed descendants only",
        "source_environment_network_checks": "passed"}


def audit_case(root, base, case):
    quiet(root)
    artifacts = {}
    result_path = root / ("scratch-native-u3a-r2-mutation-" + case + "-01/result.json")
    report = {"case": case, "status": "invalid", "artifacts": artifacts}
    try:
        record = document(result_path, artifacts)
        tree = root / ("scratch-native-u3a-r2-mutation-" + case + "-01-source")
        require(record["case"] == case and record["base"] == base and record["source"] == SOURCE
                and record["tree"] == str(tree) and record["status"] == "killed", "result identity differs")
        require(tree.resolve(strict=True) == tree and (tree / ".git").is_dir(), "wrong private source repository")
        mutant = record["mutant_commit"]
        require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", mutant), "invalid mutant commit")
        parents = git(tree, "rev-list", "--parents", "-n", "1", mutant).decode().split()
        require(parents == [mutant, base], "mutant is not a single child of the frozen base")
        require(git(tree, "diff-tree", "--no-commit-id", "--name-only", "-r", mutant).decode().splitlines()
                == [SOURCE], "mutant changes other source paths")
        original = git(tree, "show", base + ":" + SOURCE)
        changed = git(tree, "show", mutant + ":" + SOURCE)
        before, after = record["edit"]["before"].encode(), record["edit"]["after"].encode()
        require(before and original.count(before) == 1 and original.replace(before, after, 1) == changed,
                "mutant is not exactly the recorded single guarded edit")
        require(sha(original) == record["source_sha256"] and sha(changed) == record["mutated_source_sha256"],
                "committed source hashes differ")
        require(load_bytes(tree / SOURCE, artifacts) == changed, "retained source differs from committed mutant")
        require(sha(load_bytes(tree / HARNESS, artifacts)) == record["harness_sha256"], "mutation harness changed")
        report.update(base=base, mutant_commit=mutant, edit=record["edit"], mechanism=MECHANISM[case])
        report["baseline"] = audit_arm(root, case, "baseline", record, artifacts)
        quiet(root)
        report["mutant"] = audit_arm(root, case, "mutant", record, artifacts)
        report["status"] = "valid"
    except (Refusal, OSError, ValueError, KeyError, TypeError, ET.ParseError, subprocess.TimeoutExpired) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--case", action="append", choices=CASES, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--canary", type=Path)
    args = parser.parse_args()
    root, out = args.evidence_root, args.out
    require(root.is_absolute() and root.resolve(strict=True) == root and root.is_dir(),
            "evidence root must be an explicit physical directory")
    require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.base), "base must be a full Git identity")
    require(len(set(args.case)) == len(args.case), "duplicate selected case")
    require(out.is_absolute() and out.parent == root and out.resolve() == out
            and not out.exists() and not out.is_symlink()
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", out.name),
            "output must be a fresh literal JSON directly under the evidence root")
    quiet(root)
    script_sha = sha(Path(__file__).read_bytes())
    canary_pin = None
    if len(args.case) > 1:
        require(args.canary is not None, "audit MA end to end before multiple cases")
        prior = document(args.canary, {})
        require(prior.get("status") == "valid" and prior.get("cases") == ["MA"]
                and prior.get("base") == args.base and prior.get("evidence_root") == str(root)
                and prior.get("script_sha256") == script_sha, "canary does not bind this exact audit")
        canary_pin = sha(args.canary.read_bytes())
    reports = [audit_case(root, args.base, case) for case in args.case]
    valid = all(item["status"] == "valid" for item in reports)
    totals = {}
    if valid:
        for arm in ("baseline", "mutant"):
            totals[arm] = {key: sum(item[arm][key] for item in reports)
                           for key in ("tests", "passed", "failures", "errors", "skipped")}
    summary = {
        "version": 1, "status": "valid" if valid else "invalid", "base": args.base,
        "evidence_root": str(root), "cases": args.case, "script_sha256": script_sha,
        "canary_sha256": canary_pin, "totals": totals, "results": reports,
        "limits": [
            "Saved mutation evidence only; no test, source mutation, native program or network request was run.",
            "Campaign base is explicit. This is not a mutation campaign rerun against a later integration head.",
            "Cleanup witnesses cover observed descendants, not never-observed orphans.",
            "MG proves the required verifier call is invoked; MO preserves a deeper pin refusal.",
            "Independent controls validate synthetic software guard behavior, not positive native execution admission.",
        ]}
    with out.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": summary["status"], "out": str(out), "totals": totals}, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, OSError, ValueError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        raise SystemExit(2)

