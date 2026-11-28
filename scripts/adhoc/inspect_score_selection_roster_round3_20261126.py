"""Inspect the independent real-preview project roster for issue 6399.

2026-11-26. Read-only inputs: caller corpus and selected default source manifest.
Output: a fresh structural JSON receipt outside that corpus, with no scores.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--projects", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = args.corpus_root.resolve(strict=True)
    output = args.output.absolute()
    if output.is_relative_to(corpus) or output.is_relative_to(ROOT):
        raise ValueError("write the receipt outside source and corpus")
    protected_ids = {(path.stat().st_dev, path.stat().st_ino) for path in (corpus, ROOT)}
    for parent in (output, *output.parents):
        if parent.is_symlink():
            raise ValueError("symlink output route refused")
        try:
            info = parent.stat()
        except FileNotFoundError:
            continue
        if (info.st_dev, info.st_ino) in protected_ids:
            raise ValueError("output aliases protected input ancestry")
    os.chdir(corpus)
    from data_sheets_schema.registry import default_manifest_path, load_registry
    path = default_manifest_path()
    before = path.read_bytes()
    names = sorted(load_registry(path).projects())
    expected = sorted(set(args.projects))
    value = {"manifest": str(path), "manifest_sha256": hashlib.sha256(before).hexdigest(),
             "manifest_projects": names, "real_series_projects": expected,
             "manifest_only": sorted(set(names) - set(expected)),
             "series_only": sorted(set(expected) - set(names)),
             "project_sets_equal": names == expected,
             "manifest_bytes_unchanged": path.read_bytes() == before}
    with output.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if json.loads(output.read_bytes()) != value:
        raise ValueError("saved roster receipt differs")
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
