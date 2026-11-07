"""U3D-R5 round 2: structural output, real receipt predicates, CLI binding."""
import json
from copy import deepcopy

import pytest
from click.testing import CliRunner

from data_sheets_schema import receipts as rc, canary
from data_sheets_schema.cli import receipts as cli
from tests.test_native_shared_selection import declaration
from tests.test_native_u3d_receipt_policy import selected
from tests.test_receipts import _manifest_and_texts, _receipt, FULL


def assessment(mutation=None):
    manifest, texts = _manifest_and_texts()
    receipt = _receipt(manifest['bundle_md5'])
    if mutation == 'missing': receipt['chunks'].pop()
    if mutation == 'open': receipt['chunks'][0]['status'] = 'pending'
    if mutation == 'duplicate': receipt['chunks'].append(deepcopy(receipt['chunks'][0]))
    if mutation == 'snippet': receipt['chunks'][1]['extracted'][0]['snippet'] = 'An invented quotation absent from the source material.'
    block = rc.check(receipt, manifest, texts, FULL, manifest['bundle_md5'], FULL, instrument_version=4)
    structural = canary.receipt_floors(block)
    return {**block, 'expected': True, 'native_receipt_stage': 'phase1_initial',
            'final_stage_complete': False, 'passed': not any(structural.values()),
            'structural_receipt_floors': structural,
            'coverage_floor': {'state': 'pending', 'passed': False}}


@pytest.mark.parametrize('mutation', [None, 'missing', 'open', 'duplicate', 'snippet'])
def test_real_receipt_structure(mutation):
    result = rc.initial_structure_result(assessment(mutation))
    assert result['structure_passed'] is (mutation is None)
    assert result['mode'] == 'initial_structure'
    assert result['floors'] == 'pending'
    assert result['floor_acceptance_claimed'] is False


@pytest.mark.parametrize('change', [{'checked': False}, {'native_receipt_stage': 'final'},
    {'structural_receipt_floors': {}}, {'final_stage_complete': True}])
def test_unchecked_or_final_assessment_refused(change):
    assert not rc.initial_structure_result({**assessment(), **change})['structure_passed']


@pytest.mark.parametrize('registered', [False, True])
@pytest.mark.parametrize('mutation', [None, 'missing', 'open', 'duplicate', 'snippet'])
def test_cli_initial_json(declaration, monkeypatch, registered, mutation):
    # Real selection/registration capture; supplied assessment tests the CLI
    # exit/JSON boundary. Importing the real path owner still requires B, so
    # these tests remain blocked until that merge. Real predicates run above.
    selected(declaration, registered=registered)
    from data_sheets_schema import native_shared_capture
    from pathlib import Path
    root = Path(declaration['stage_root']).parent
    paths = {'full': root / 'full.yaml', 'receipt': root / 'receipt.yaml',
             'provenance': root / 'absent.yaml', 'core_dir': root}
    monkeypatch.setattr(native_shared_capture, 'selected_receipt_paths', lambda _: paths)
    monkeypatch.setattr(rc, 'block_for', lambda *a, **k: assessment(mutation))
    args = ['check', '--label', declaration['run']['label'], '--project', declaration['run']['project'],
            '--native-shared-selection', declaration['registration_path'], '--initial-structure']
    result = CliRunner().invoke(cli.receipts, args)
    assert result.exit_code == (0 if mutation is None else 1), result.output
    output = json.loads(result.output)
    assert output['mode'] == 'initial_structure'
    assert output['floors'] == 'pending' and output['floor_acceptance_claimed'] is False
    assert not paths['provenance'].exists()
    both = CliRunner().invoke(cli.receipts, [*args, '--strict'])
    assert both.exit_code == 2 and 'mutually exclusive' in both.output


def test_selection_identity_mismatch_refused(declaration):
    result = CliRunner().invoke(cli.receipts, ['check', '--label', 'wrong-label',
        '--project', declaration['run']['project'], '--native-shared-selection',
        declaration['registration_path'], '--initial-structure'])
    assert result.exit_code != 0 and 'belongs to another' in result.output


def test_flags_refused_before_selection_or_receipt_io():
    result = CliRunner().invoke(cli.receipts, ['check', '--label', 'local', '--project', 'NEUTRAL',
        '--initial-structure', '--strict'])
    assert result.exit_code == 2 and 'mutually exclusive' in result.output


def test_initial_requires_native_selection():
    result = CliRunner().invoke(cli.receipts, ['check', '--label', 'local', '--project', 'NEUTRAL',
        '--initial-structure'])
    assert result.exit_code == 2 and 'requires --native-shared-selection' in result.output
