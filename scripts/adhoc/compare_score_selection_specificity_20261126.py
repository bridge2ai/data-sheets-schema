"""Compare full D128 arrays for issue 6385, 2026-11-26.

Inputs: baseline and candidate scanner JSON. Output: a fresh JSON receipt with
exact added/removed objects and a separate line-independent comparison. No
scanner data, source files, policy or evaluation evidence is modified.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def counter(values):
    return Counter(json.dumps(value, sort_keys=True) for value in values)


def compare(before, after):
    left, right = counter(before), counter(after)
    return {"before_count": len(before), "after_count": len(after),
            "ordered_equal": before == after,
            "added": [json.loads(item) for item in (right - left).elements()],
            "removed": [json.loads(item) for item in (left - right).elements()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview-doc", type=Path)
    args = parser.parse_args()
    raw = [path.read_bytes() for path in (args.baseline, args.candidate)]
    before, after = map(json.loads, raw)
    result = {"baseline": str(args.baseline), "candidate": str(args.candidate),
              "baseline_sha256": digest(raw[0]), "candidate_sha256": digest(raw[1]),
              "candidate_self_test": after.get("self_test"), "arrays": {}}
    for key in ("hits", "violations", "test_dependencies"):
        assert isinstance(before[key], list) and isinstance(after[key], list), key
        item = compare(before[key], after[key])
        # This diagnostic never substitutes for the complete objects above.
        no_lines = lambda rows: [{k: v for k, v in row.items() if k != "line"} for row in rows]
        item["without_line_numbers"] = compare(no_lines(before[key]), no_lines(after[key]))
        result["arrays"][key] = item
    if args.preview_doc:
        content = args.preview_doc.read_text()
        assert chr(64) not in content
        blocks = re.findall(r"^```bash\n(.*?)^```", content, flags=re.MULTILINE | re.DOTALL)
        assert blocks and "--execute" not in "\n".join(blocks)
        check = subprocess.run(["bash", "-n"], input="\n".join(blocks), text=True,
                               capture_output=True, timeout=20)
        assert check.returncode == 0, check.stderr
        result["preview_commands"] = {"path": str(args.preview_doc), "sha256": digest(content.encode()),
                                      "bash_n_exit": 0, "commands_executed": False}
    rendered = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    with args.output.open("xb") as stream:
        stream.write(rendered)
    assert args.output.read_bytes() == rendered
    print(json.dumps({"receipt": str(args.output), "sha256": digest(rendered),
                      "arrays": {key: {k: value[k] for k in ("before_count", "after_count", "ordered_equal")}
                                 for key, value in result["arrays"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
