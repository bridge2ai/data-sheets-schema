"""Export immutable scanner baseline for issues 6245–6248, 2026-11-15.

Input: local Git candidate f5c7c312f. Output: validated scanner input export
in the assigned scratch directory. Reuses the retained manifest exporter.
"""
from pathlib import Path
import sys

import native_u5_inputs_20261108 as inputs


def main():
    inputs.SCRATCH = Path(sys.argv[1]).resolve()
    commit = inputs.git('rev-parse', 'f5c7c312f').decode().strip()
    label = 'scanner-candidate-' + commit[:9]
    inputs.materialize(label, commit, inputs.BASE_SCAN_PATHS)
    tree, manifest = inputs.checked_scanner_input(label, commit)
    assert (tree / '.claude/skills/d4d-generation-specificity-audit/scan.py').stat().st_size
    print(tree)
    print('commit:', commit)
    print('entries:', manifest['entry_count'])
    print('bytes:', manifest['total_blob_bytes'])


if __name__ == '__main__':
    main()
