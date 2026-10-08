"""Compare the fixed 22-version panel in separate baseline/candidate processes.

Read-only measurements; outputs must be new external directories. No provider,
certification write, historical-table regeneration or policy change is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

sys.dont_write_bytecode = True
DRIVER = Path(__file__).resolve()
PANEL = "notes/attainability_join_context_2026-10-02.json"
PANEL_SHA = "1b4be55e6acf998c05349c0fb034f15ece68edcdca0a102e1664c4590e9aea09"
SCRIPT = "scripts/measure_unhyphenated_line_splits.py"
BASELINE_COMMIT = "8730ba98335392aba539b5c99e0b61918be917ab"
BASELINE_SCRIPT = {"sha256": "56615e0f7ffd371bafaa7bf79dde9565c35cc829f2b95bbfb594d67e69b53fad",
                   "bytes": 22640}
# Bind the reviewed implementation bytes, independently of later evidence commits.
CANDIDATE_SCRIPT_SHA = "bd2d3f23c97c6e03eeba1cf32a02e53027710f7794ccfd734ed66061ae42770c"
SOURCE_FILES = (SCRIPT, *(f"src/data_sheets_schema/{name}.py" for name in
                         ("attainability", "chunking", "provenance", "corpus", "resources")))
IDENTITY = ("bundle", "md5", "sha256", "bytes", "records")
METRICS = ("lines", "letter_breaks", "joinable_breaks", "split_words", "wraps_that_join", "moved",
           "moved_if_every_break_joins", "hyphenated_breaks", "mixed_windows", "most_in_one_window",
           "window_moves", "compare_mixed_windows", "compare_most_in_one_window", "moved_if_up_to_k_breaks_join")
FORMAT = "d4d_shared_line_join_replay_v1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def equal(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    raw = path.read_bytes()
    return {"sha256": sha(raw), "bytes": len(raw)}


def identity(row):
    return {key: row[key] for key in IDENTITY}


def load_panel(path):
    raw = path.read_bytes()
    require(sha(raw) == PANEL_SHA, "historical panel bytes differ")
    panel = json.loads(raw)
    rows = panel["measurement"]["rows"]
    require(len(rows) == 22 and sum(row["records"] for row in rows) == 279,
            "historical panel membership differs")
    require(len({(row["bundle"], row["md5"], row["sha256"]) for row in rows}) == 22,
            "duplicate historical version")
    for row in rows:
        path = Path(row["bundle"])
        require(not path.is_absolute() and ".." not in path.parts, "panel path is not repository relative")
    return panel


def external_output(path, protected):
    output = path.absolute()
    require(output.resolve() == output and not output.exists(), "output must be a new physical directory")
    require(output.parent.is_dir(), "output parent must already exist")
    for root in protected:
        root = root.resolve()
        require(output != root and root not in output.parents and output not in root.parents,
                "output overlaps an input directory")
    return output


def publish(output, value):
    output.mkdir()
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def run(args):
    repo = args.repo.resolve(strict=True)
    output = external_output(args.output, (repo, DRIVER.parents[2]))
    panel = load_panel(repo / PANEL)
    words = args.words.resolve(strict=True)
    require(pin(words)["sha256"] == panel["measurement"]["words"]["sha256"], "word-list bytes differ")
    source_before = {path: pin(repo / path) for path in SOURCE_FILES}
    bundles = sorted({row["bundle"] for row in panel["measurement"]["rows"]})

    def disk_inputs():
        return {path: pin(repo / path) if (repo / path).is_file() else None for path in bundles}

    before, words_before = disk_inputs(), pin(words)
    os.chdir(repo)
    sys.path.insert(0, str(repo / "src"))
    module = ModuleType("d4d_line_join_replay_measure")
    module.__file__ = str(repo / SCRIPT)
    sys.modules[module.__name__] = module
    # Execute the selected script's bytes directly, never a cached script .pyc.
    exec(compile((repo / SCRIPT).read_bytes(), module.__file__, "exec"), module.__dict__)
    dictionary, words_identity = module.load_words(words)
    require(words_identity["entries"] == panel["measurement"]["words"]["entries"], "word-list entry count differs")
    require(module.at.GATE_JOINS_PER_WINDOW == 2 and module.at.GATE_COMPARE_WINDOW == 10,
            "certification bounds differ")
    rows = []
    for expected in panel["measurement"]["rows"]:
        row = {"identity": identity(expected)}
        try:
            raw, basis = module.at.resolve_bytes(expected["bundle"], md5=expected["md5"],
                sha256=expected["sha256"], disk=repo / expected["bundle"])
            require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"], "resolved bytes differ")
            measured = module.measure(raw.decode("utf-8"), dictionary, compare_window=10, joins_per_window=2)
            require(set(measured) == set(METRICS), "measurement output keys differ")
            row.update(status="measured", resolution=basis, measurement=measured,
                       historical_equal=equal(measured, {key: expected[key] for key in METRICS}))
        except Exception as error:
            row.update(status="unmeasured", error={"type": type(error).__name__, "message": str(error)})
        rows.append(row)
    source_after = {path: pin(repo / path) for path in SOURCE_FILES}
    after = disk_inputs()
    preserved = (source_before == source_after and before == after and pin(words) == words_before
                 and pin(repo / PANEL)["sha256"] == PANEL_SHA)
    complete = all(row["status"] == "measured" for row in rows)
    table = {"words": panel["measurement"]["words"], "mixed_window_lines": module.at.MIXED_WINDOW_LINES,
             "compare_window": 10, "joins_per_window": 2, "unreadable_records": [],
             "rows": [{**row["identity"], **row["measurement"]} if row["status"] == "measured" else
                      {**row["identity"], "error": row["error"]["message"]} for row in rows]}
    value = {"format": FORMAT, "kind": "measurement", "panel_sha256": PANEL_SHA,
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "driver_sha256": sha(DRIVER.read_bytes()), "source_before": source_before,
        "source_after": source_after, "word_list": panel["measurement"]["words"],
        "disk_inputs_before": before, "disk_inputs_after": after, "inputs_preserved": preserved,
        "versions": 22, "historical_provenance_records": 279, "complete": complete, "rows": rows,
        "markdown": module.markdown(table),
        "settings": {"compare_window": 10, "joins_per_window": 2, "join_context_lines": None},
        "scientific_scoring_eligible": False,
        "scope": "Fixed historical panel; no current-corpus, provider, calibration or exhaustive-absence claim"}
    publish(output, value)
    return 0 if complete and preserved and all(row.get("historical_equal") is True for row in rows) else 1


def compare(args):
    output = external_output(args.output, (args.baseline.parent, args.candidate.parent, DRIVER.parents[2]))
    require(args.baseline.resolve() != args.candidate.resolve(), "baseline and candidate reports are the same file")
    raw = [path.read_bytes() for path in (args.baseline, args.candidate)]
    require(raw[0] != raw[1], "baseline and candidate reports are identical")
    values = [json.loads(item) for item in raw]
    panel = load_panel(DRIVER.parents[2] / PANEL)
    expected = [identity(row) for row in panel["measurement"]["rows"]]
    for value in values:
        require(value["format"] == FORMAT and value["kind"] == "measurement", "unexpected replay report")
        require(value["panel_sha256"] == PANEL_SHA and [row["identity"] for row in value["rows"]] == expected,
                "replay panel differs")
        require(value["inputs_preserved"] is True and value["source_before"] == value["source_after"]
                and value["disk_inputs_before"] == value["disk_inputs_after"], "replay inputs changed")
        require(all(row["status"] == "measured" and set(row["measurement"]) == set(METRICS)
                    for row in value["rows"]), "replay has unmeasured versions")
    left, right = values
    require(left["repo_commit"] == BASELINE_COMMIT, "baseline commit differs")
    require(left["source_before"][SCRIPT] == BASELINE_SCRIPT, "baseline script differs")
    candidate_script = pin(DRIVER.parents[2] / SCRIPT)
    require(candidate_script["sha256"] == CANDIDATE_SCRIPT_SHA, "current candidate script differs from reviewed identity")
    require(right["source_before"][SCRIPT] == candidate_script, "candidate script differs")
    require(left["word_list"] == right["word_list"] == panel["measurement"]["words"], "replay dictionaries differ")
    require(left["settings"] == right["settings"] == {
        "compare_window": 10, "joins_per_window": 2, "join_context_lines": None}, "replay settings differ")
    require(left["driver_sha256"] == right["driver_sha256"] == sha(DRIVER.read_bytes()), "replay drivers differ")
    require(all(left["source_before"][path] == right["source_before"][path]
                for path in SOURCE_FILES if path != SCRIPT), "shared matcher/dependency bytes differ")
    rows = [{"identity": expected[i], "baseline_candidate_equal": equal(a["measurement"], b["measurement"]),
             "historical_equal": equal(a["measurement"], {
                 key: panel["measurement"]["rows"][i][key] for key in METRICS}) and equal(b["measurement"], {
                 key: panel["measurement"]["rows"][i][key] for key in METRICS})}
            for i, (a, b) in enumerate(zip(left["rows"], right["rows"]))]
    same = all(row["baseline_candidate_equal"] and row["historical_equal"] for row in rows)
    markdown_equal = left["markdown"] == right["markdown"]
    publish(output, {"format": FORMAT, "kind": "comparison", "versions": 22, "rows": rows,
        "equal": same and markdown_equal, "markdown_equal": markdown_equal,
        "panel_sha256": PANEL_SHA, "baseline_report_sha256": sha(raw[0]),
        "candidate_report_sha256": sha(raw[1]),
        "baseline_source": {"commit": BASELINE_COMMIT, "script": BASELINE_SCRIPT},
        "candidate_source": {"observed_commit": right["repo_commit"], "script": candidate_script},
        "scientific_scoring_eligible": False})
    return 0 if same and markdown_equal else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--repo", required=True, type=Path)
    run_parser.add_argument("--words", default=Path("/usr/share/dict/words"), type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    collect_parser = sub.add_parser("compare")
    collect_parser.add_argument("--baseline", required=True, type=Path)
    collect_parser.add_argument("--candidate", required=True, type=Path)
    collect_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args) if args.command == "run" else compare(args)


if __name__ == "__main__":
    raise SystemExit(main())
