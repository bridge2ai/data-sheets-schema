"""Registered receipt results gate every next dispatch without a baseline (#4277)."""
import copy
from dataclasses import replace
import importlib
import json
import socket

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, canary, receipt_completion_policy as cp, receipts, run_lock
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external
from tests.test_receipt_completion_policy import registration


@pytest.fixture
def batch_env(external, tmp_path, monkeypatch):
    module = importlib.import_module('data_sheets_schema.cli.api')
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **kw: pytest.fail('network forbidden'))
    released, calls, outputs = [], [], []
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: tmp_path / 'batch-lock')
    monkeypatch.setattr(run_lock, 'release', released.append)
    monkeypatch.setattr(module, '_plan_or_refuse', lambda s: {'approx_total_input_tokens': 0})

    def invoke(modes, *, pending=False, legacy=False, flags=()):
        reg = registration({'state': 'pending', 'mode': 'diagnostic_pilot'} if pending else None)
        spec = replace(external, condition='generic_v8', receipt_completion_version=0 if legacy else 1,
                       receipt_completion_registration=None if legacy else json.dumps(reg))
        policy = cp.select_policy(spec.render_spec()) if not legacy else None
        monkeypatch.setattr(module, '_spec', lambda *args, **kw: replace(spec, label=args[2]))

        def execute(s):
            mode = modes[len(calls)]
            calls.append(s.label)
            if mode == 'exception':
                raise RuntimeError('synthetic generation failure')
            receipt = {'checked': True, 'expected': True, 'instrument': receipts.RERECEIPTS_INSTRUMENT,
                       'slots': {'with_receipt': 3, 'receiptable': 3}, 'findings': [],
                       'chunks': {'total': 1, 'reviewed': 1}, 'snippets': {'verified': 1}}
            if policy is not None:
                receipt[cp.BLOCK_KEY] = cp.block_identity(policy)
            if mode == 'failed': receipt['slots']['with_receipt'] = 0
            if mode == 'empty': receipt['slots'] = {'with_receipt': 0, 'receiptable': 0}
            if mode == 'unchecked': receipt['checked'] = False
            if mode == 'legacy_block': receipt.pop(cp.BLOCK_KEY)
            if mode == 'malformed': receipt['slots']['with_receipt'] = True
            if mode == 'wrong_policy':
                different = {**reg, 'registration_id': 'different-registration'}
                receipt[cp.BLOCK_KEY]['registration'] = cp.registration_identity(json.dumps(different).encode())
            checks = {'pair': {'ran': True, 'errors': 0},
                      'report': {'checked': True, 'claims_checked': 1, 'findings': []},
                      'grounding': {'checked': True, 'distinct': {'absent': 0}},
                      'form': {'checked': True, 'organisational_fragments': 0,
                               'undeclared_prefix_occurrences': 0, 'british_spellings': 0}}
            if mode != 'missing': checks['receipts'] = receipt
            path = tmp_path / (s.label + '.yaml')
            path.write_text(yaml.safe_dump({'run': {'project': s.project}, 'checks_for_test': copy.deepcopy(checks)}))
            outputs.append(path)
            return {'usage': [], 'skipped': [], 'checks': checks,
                    'validation_problems': [{'artifact': 'full', 'error': 'invalid'}] if mode == 'invalid' else [],
                    'outputs': {'provenance': str(path)}}
        monkeypatch.setattr(api, 'execute', execute)
        regpath = tmp_path / 'registration.json'; regpath.write_text(json.dumps(reg))
        args = ['api', 'batch', '--projects', spec.project, '--manifest', str(spec.manifest),
                '--project-bundle', f'{spec.project}={spec.bundle}', '--condition', spec.condition,
                '--replicates', str(len(modes)), '--label-prefix', 'batch-review',
                '--no-branch-guard', '--yes', '--continue-on-error']
        if not legacy:
            args += ['--receipt-completion-version', '1', '--receipt-completion-registration', str(regpath)]
        return CliRunner().invoke(cli, args + list(flags))
    return invoke, calls, released, outputs


@pytest.mark.parametrize('mode', ['failed', 'empty', 'missing', 'unchecked', 'legacy_block',
                                 'malformed', 'wrong_policy', 'exception', 'invalid'])
def test_registered_gate_stops_without_baseline_even_with_continue(batch_env, mode):
    invoke, calls, released, outputs = batch_env
    result = invoke([mode, 'passed'])
    assert result.exit_code == 1, result.output
    assert calls == ['batch-review_rep1']
    assert len(released) == 1
    assert '--no-canary-gate' not in result.output
    if mode not in ('exception', 'invalid'):
        assert yaml.safe_load(outputs[0].read_text())['canary']['status'] != canary.OK


def test_passing_registered_results_allow_fanout_and_record_no_baseline(batch_env):
    invoke, calls, released, outputs = batch_env
    result = invoke(['passed', 'passed'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 2 and len(released) == 1
    for path in outputs:
        verdict = yaml.safe_load(path.read_text())['canary']
        assert verdict['status'] == canary.OK
        assert 'no historical baseline requested' in verdict['basis']
        row = next(r for r in verdict['rows'] if r['metric'] == 'registered receipt coverage')
        assert row['coverage']['state'] == 'passed'


@pytest.mark.parametrize('mode', ['failed', 'exception', 'invalid'])
def test_later_failed_registered_result_stops_remaining_runs(batch_env, mode):
    invoke, calls, released, outputs = batch_env
    result = invoke(['passed', mode, 'passed'])
    assert result.exit_code == 1, result.output
    assert len(calls) == 2 and len(released) == 1


def test_single_pending_diagnostic_runs_without_claiming_gate_pass(batch_env):
    invoke, calls, released, outputs = batch_env
    result = invoke(['passed'], pending=True)
    assert result.exit_code == 0, result.output
    assert len(calls) == 1 and len(released) == 1
    assert 'registered receipt coverage=pending' in result.output
    assert 'gate passed' not in result.output
    assert 'canary' not in yaml.safe_load(outputs[0].read_text())


@pytest.mark.parametrize('flags,pending', [([], True), (['--no-canary-gate'], False)])
def test_pending_fanout_and_explicit_bypass_refused_before_dispatch(batch_env, flags, pending):
    invoke, calls, released, outputs = batch_env
    result = invoke(['passed', 'passed'], pending=pending, flags=flags)
    assert result.exit_code == 1 and not calls and not released, result.output


def test_legacy_default_still_has_no_implicit_gate(batch_env):
    invoke, calls, released, outputs = batch_env
    result = invoke(['failed', 'failed'], legacy=True)
    assert result.exit_code == 0, result.output
    assert len(calls) == 2 and len(released) == 1
    assert all('canary' not in yaml.safe_load(path.read_text()) for path in outputs)


def test_requested_baseline_remains_required(batch_env, monkeypatch):
    invoke, calls, released, outputs = batch_env
    monkeypatch.setattr(canary, 'baseline_for', lambda *a: {'pair errors': None})
    monkeypatch.setattr(canary, 'report_basis', lambda *a: {})
    result = invoke(['passed', 'passed'], flags=['--canary-baseline', 'missing-baseline'])
    assert result.exit_code == 1, result.output
    assert len(calls) == 1 and len(released) == 1
    assert 'no baseline' in result.output
