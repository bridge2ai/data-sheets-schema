"""Fresh-interpreter loader-transition test for PR 5968, 2026-11-16.

Inputs: repository test assertions and installed dependencies. Output: a success
line only after every original transition assertion passes. No native or provider
executable is invoked, and no cache authority is rebound.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import pytest
from tests.test_native_catalog_fast_guards import (
    _assert_loader_transition_with_same_marker_and_empty_slot_cache,
)


def main():
    with pytest.MonkeyPatch.context() as patch:
        _assert_loader_transition_with_same_marker_and_empty_slot_cache(patch)
    print('loader transition assertions passed')


if __name__ == '__main__':
    main()
