"""Run the unchanged owner-delivery scenario in a fresh interpreter, #6192.

Inputs: this checkout and an exclusive output path below a pytest temporary
directory. Outputs: JSON witness after every original scenario assertion passes.
Only synthetic Python stage checks run; no provider or native executable.
2026-11-13.
"""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from tests import test_native_shared_owner_delivery as scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        raise RuntimeError('owner-delivery assertions require an unoptimized interpreter')
    root = Path(__file__).resolve().parents[2]
    assert Path(scenario.__file__).resolve() == root / 'tests/test_native_shared_owner_delivery.py'
    for module, relative in (
            (scenario.catalogs, 'native_catalog_reuse.py'),
            (scenario.initialization, 'native_catalog_initialization.py'),
            (scenario.receipts, 'native_shared_receipts.py'),
            (scenario.events, 'native_schema_event_reuse.py'),
            (scenario.stage, 'native_shared_stage.py'),
            (scenario.typed, 'typed_audit/__init__.py')):
        assert Path(module.__file__).resolve() == root / 'src/data_sheets_schema' / relative
    assert scenario.catalogs.runtime_token() is not None
    fixture_root = args.output.parent / 'owner-delivery-child'
    fixture_root.mkdir()
    supplied = scenario.supplied.__wrapped__(fixture_root)
    case = scenario.case.__wrapped__(supplied, SimpleNamespace(
        param={'schema_raw': scenario.STANDALONE_SCHEMA}))
    with pytest.MonkeyPatch.context() as patch:
        scenario._assert_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh(case, patch)
        assert scenario.initialization.INITIALIZATION_ERROR == 'unsupported current initialization'
        assert scenario.catalogs.runtime_token() is None
    observed = {'source_root': str(root), 'reuse_initially_eligible': True,
                'original_owner_assertions_completed': True,
                'unknown_initialization_refused': True}
    raw = json.dumps(observed, sort_keys=True) + '\n'
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(raw)
    assert json.loads(args.output.read_bytes()) == observed
    print(raw, end='')


if __name__ == '__main__':
    main()
