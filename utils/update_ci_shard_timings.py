"""Build file-duration estimates from a completed run's downloaded JUnit files."""
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def build(results, root, run_id, commit):
    modules = {}
    for name in subprocess.check_output(
            ["git", "ls-files", "tests"], cwd=root, text=True).splitlines():
        if name.endswith(".py"):
            modules[name[:-3].replace("/", ".")] = name
    weights, cases, artifacts = defaultdict(Decimal), set(), []
    files = sorted(results.rglob("pytest.xml"))
    if not files:
        raise ValueError("no pytest.xml artifacts found")
    for path in files:
        artifacts.append({"path": str(path.relative_to(results)),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for case in ET.parse(path).iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                raise ValueError("use a successful run for timing estimates")
            identity = (case.attrib["classname"], case.attrib["name"])
            if identity in cases:
                raise ValueError(f"duplicate case across artifacts: {identity}")
            cases.add(identity)
            candidates = [module for module in modules
                          if identity[0] == module or identity[0].startswith(module + ".")]
            if not candidates:
                raise ValueError(f"cannot map collected case to a repository file: {identity}")
            duration = Decimal(case.attrib["time"])
            if not duration.is_finite() or duration < 0:
                raise ValueError(f"invalid recorded duration: {identity}")
            weights[modules[max(candidates, key=len)]] += duration
    if not cases:
        raise ValueError("no test cases in the supplied artifacts")
    return {"schema_version": 1,
            "source": {"run_id": run_id, "commit": commit,
                       "url": f"https://github.com/bridge2ai/data-sheets-schema/actions/runs/{run_id}",
                       "test_cases": len(cases), "artifacts": artifacts},
            "method": "Sum JUnit case times by collected file, with a 0.001-second floor. These are scheduling estimates, not wall-clock predictions or a test allowlist. Untimed collected files use the median known duration; obsolete entries are ignored.",
            "file_seconds": {name: float(max(seconds, Decimal("0.001")))
                             for name, seconds in sorted(weights.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("utils/ci_test_durations.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    value = build(args.results, root, args.run_id, args.commit)
    args.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"files": len(value["file_seconds"]),
                      "test_cases": value["source"]["test_cases"]}))


if __name__ == "__main__":
    main()
