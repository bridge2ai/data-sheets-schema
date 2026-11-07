"""Recover pinned U3-C observer test donors, 2026-11-07.

Inputs: local Git object 142d090bb, explicit test filenames from the roster.
Outputs: exclusively created tests in this checkout; subsequent adaptation is
reviewable separately. No fetch, network, production execution or test run.
"""
import argparse
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
DONOR = "142d090bb1cf686ef87b9105b96e0f982356b90f"
FILES = (
    "test_native_shared_observations.py",
    "test_native_shared_streams.py",
    "test_native_shared_stream_diagnostics.py",
    "test_native_shared_stream_diagnostics_adversarial.py",
    "test_native_shared_attribution.py",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", choices=FILES)
    args = parser.parse_args()
    for name in args.files:
        relative = "tests/" + name
        raw = subprocess.run(
            ["git", "--no-replace-objects", "show", DONOR + ":" + relative],
            cwd=ROOT, check=True, capture_output=True, timeout=30,
        ).stdout
        if not raw:
            raise ValueError("empty donor: " + relative)
        with (ROOT / relative).open("xb") as stream:
            stream.write(raw)
        if (ROOT / relative).read_bytes() != raw:
            raise ValueError("recovery bytes differ: " + relative)
        print(relative)


if __name__ == "__main__":
    main()
