"""Selected caller scope reaches actual semantic requests before admission."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import typed_audit_runtime as runtime, usage_ledger as ledger
from tests.test_shared_generation_selection import external, offline, selected  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec


RECORD = 'id: urn:example\nname: Example\n'
CARRY = {'Completed full record': RECORD, 'Completed core record': RECORD,
         'Reconciled full record': RECORD, 'Original full record': RECORD,
         'Original core record': RECORD, 'Audit findings': '{"findings":[]}'}


def _context_registration(base, update):
    reg = registration_for(base)
    path = Path(reg['inputs']['context']['path'])
    context = json.loads(path.read_bytes())
    update(context)
    # Preserve noncanonical whitespace too: requests bind raw input bytes.
    path.write_text(json.dumps(context, ensure_ascii=False, indent=3) + '\n')
    reg['inputs']['context'] = sg.file_pin(path)
    return reg


def _blocks(messages):
    return [part['text'] for message in messages if message['role'] == 'user'
            and isinstance(message['content'], list) for part in message['content']
            if part.get('type') == 'text']


def _scope(spec):
    block = sg.generation_context(spec)
    return block, json.loads(block[len(sg.GENERATION_CONTEXT_HEADER):])


def test_different_captured_scopes_change_every_selected_phase_without_manifest(external):
    base = replace(external, manifest=None, profile='bridge2ai', profile_basis='test caller')
    wires = []
    for release in ('alpha-release-unique', 'beta-release-unique'):
        def changed(context):
            context['scopes'][0].update(release=release, scope='Only ' + release)
            context['source_policy'] = {'priority': ['protocol'], 'basis': release + ' policy'}
            context['vocabulary'] = {'declared-name': release}
        reg = _context_registration(base, changed)
        spec = selected_spec(base, reg)
        expected, payload = _scope(spec)
        pin = reg['inputs']['context']
        assert payload['context'] == {'identity': pin, 'raw_json': Path(pin['path']).read_text()}
        assert json.loads(payload['context']['raw_json'])['source_policy']['basis'] == release + ' policy'
        assert json.loads(payload['context']['raw_json'])['vocabulary'] == {'declared-name': release}
        assert payload['source_manifest'] is None
        vocab = reg['inputs']['profile']['vocabulary']
        assert vocab is not None
        assert payload['profile']['vocabulary'] == {'identity': vocab, 'raw_text': Path(vocab['path']).read_text()}
        assert payload['profile']['name'] == 'bridge2ai'
        current = {}
        for phase in ('full', 'core', 'reconcile_full', 'reconcile_core', 'report'):
            req = api.build_phase(spec, phase, carry=CARRY)
            assert _blocks(req.messages).count(expected) == 1
            sg.require_generation_context(spec, req.messages)
            current[phase] = sg.canonical({'system': req.system, 'messages': req.messages})
        wires.append(current)
    assert all(wires[0][phase] != wires[1][phase] for phase in wires[0])


def test_full_readdress_inherits_exact_scope_once(selected):
    original = api.build_phase(selected, 'full', carry={})
    followup = api.build_readdress(original, 'original full response', [{'path': '/name'}])
    assert followup.messages[:-2] == original.messages
    sg.require_generation_context(selected, followup.messages)
    runtime.require_request(selected, 'full_readdress', {'messages': followup.messages})


def test_real_regate_helper_preserves_scope_and_selected_report_instruction(selected, monkeypatch):
    selected.full_path.parent.mkdir(parents=True, exist_ok=True)
    selected.full_path.write_text(RECORD)
    selected.core_path.parent.mkdir(parents=True, exist_ok=True)
    selected.core_path.write_text(RECORD)
    calls = []
    def capture(spec, phase, *args, **kwargs):
        calls.append((phase, deepcopy(kwargs)))
        sg.require_generation_context(spec, kwargs['messages'])
        raise RuntimeError('stop after capturing actual helper request')
    monkeypatch.setattr(api, '_call_with_usage', capture)
    settings = api._model_settings()
    assert api._regenerate_report(selected, object(), settings, [], CARRY,
        phase='report_regate', contradictions=[{'kind': 'synthetic', 'detail': 'check'}]) is False
    assert len(calls) == 1 and calls[0][0] == 'report_regate'
    texts = _blocks(calls[0][1]['messages'])
    assert texts.count(sg.generation_context(selected)) == 1
    assert texts[-1] == api.phase_instruction('report_regate', 25)
    assert api.phase_instruction('report', 25) not in texts


def test_selected_shape_repair_adds_only_scope_metadata(selected, monkeypatch):
    selected.full_path.parent.mkdir(parents=True, exist_ok=True)
    selected.full_path.write_text(RECORD)
    errors = ['synthetic shape finding']
    expected = api.build_repair('full', RECORD, errors, profile=selected.profile_obj,
                               _captured_digest=sg.digest_text(selected, 'Dataset'))
    calls = []
    monkeypatch.setattr(api, '_validator_lines', lambda *args: (errors, None))
    def capture(spec, phase, *args, **kwargs):
        calls.append((phase, deepcopy(kwargs)))
        runtime.require_request(spec, phase, kwargs)
        raise RuntimeError('stop after actual selected repair construction')
    monkeypatch.setattr(api, '_call_with_usage', capture)
    result = api._repair_invalid(selected, object(), api._model_settings(), [])
    assert len(calls) == 1 and calls[0][0] == 'repair_full'
    messages = deepcopy(calls[0][1]['messages'])
    block = messages[0]['content'].pop(-2)
    assert block == {'type': 'text', 'text': sg.generation_context(selected)}
    assert messages == expected.messages
    assert calls[0][1]['system'] == expected.system
    assert messages[0]['content'][-1]['text'] == api.REPAIR_INSTRUCTION
    assert selected.bundle.read_text() not in '\n'.join(_blocks(calls[0][1]['messages']))
    assert result[0]['outcome'].startswith('call failed: stop after')


def test_scope_mutations_refuse_before_usage_admission_or_delivery(selected, monkeypatch):
    expected = sg.generation_context(selected)
    good = {'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': expected}]}]}
    observed = []
    monkeypatch.setattr(api, '_require_surviving_accounting', lambda *_: None)
    monkeypatch.setattr(api, '_begin_usage_call', lambda *a: observed.append('admission'))
    monkeypatch.setattr(api, '_call_with_retry', lambda *a, **k: observed.append('delivery'))
    for change in ('drop', 'foreign', 'policy', 'vocabulary', 'duplicate', 'competing',
                   'assistant_only', 'wrong_type', 'extra_key', 'nested'):
        for phase in ('full', 'full_readdress', 'full_receipt_completion',
                      runtime.WORKER_PHASE, runtime.OMISSION_PHASE, runtime.INTEGRATION_PHASE,
                      'reconcile_full', 'report', 'report_regate', 'report_after_repair',
                      'repair_full', 'repair_core'):
            damaged = deepcopy(good)
            parts = damaged['messages'][0]['content']
            if change == 'drop': parts.clear()
            elif change in ('foreign', 'policy', 'vocabulary'):
                # A well-formed, rehashed alternative, not merely broken JSON.
                value = json.loads(expected[len(sg.GENERATION_CONTEXT_HEADER):])
                context = json.loads(value['context']['raw_json'])
                if change == 'foreign': context['scopes'][0]['release'] = 'other release'
                elif change == 'policy': context['source_policy'] = {'basis': 'other policy'}
                else: context['vocabulary'] = {'different': 'vocabulary'}
                raw = sg.canonical(context)
                value['context']['raw_json'] = raw.decode()
                value['context']['identity'].update(sha256=sg.sha(raw), bytes=len(raw))
                parts[0]['text'] = sg.GENERATION_CONTEXT_HEADER + sg.canonical(value).decode()
            elif change == 'duplicate': parts.append(deepcopy(parts[0]))
            elif change == 'competing': parts.append({'type': 'text', 'text': sg.GENERATION_CONTEXT_HEADER + '{}'})
            elif change == 'assistant_only': damaged['messages'][0]['role'] = 'assistant'
            elif change == 'wrong_type': parts[0]['type'] = 'image'
            elif change == 'extra_key': parts[0]['unregistered'] = True
            else: parts[0]['text'] = json.dumps({'quoted_record': expected})
            with pytest.raises(ledger.UsageLedgerError, match='captured generation scope'):
                api._call_with_usage(selected, phase, 1, 'synthetic', object(), **damaged)
    assert observed == []
    assert not selected.provenance_path.exists()


def test_live_context_drift_refuses_before_actual_admission(selected, monkeypatch):
    req = api.build_phase(selected, 'full', carry={})
    context = Path(sg.capture(selected).document()['inputs']['context']['path'])
    context.write_bytes(context.read_bytes() + b'\n')
    monkeypatch.setattr(api, '_require_surviving_accounting', lambda *_: None)
    monkeypatch.setattr(api, '_begin_usage_call', lambda *a: pytest.fail('usage admitted despite context drift'))
    monkeypatch.setattr(api, '_call_with_retry', lambda *a, **k: pytest.fail('delivery despite context drift'))
    with pytest.raises(ValueError, match='authority changed'):
        api._call_with_usage(selected, 'full', 1, 'synthetic', object(), messages=req.messages)


@pytest.mark.parametrize('owners', [['', ''], ['/creators/0'], ['', '/creators/0', '/creators/0']])
def test_impossible_scope_inventory_refuses_before_client_and_outputs(external, monkeypatch, owners):
    def changed(context):
        row = context['scopes'][0]
        context['scopes'] = [dict(row, owner=owner) for owner in owners]
    reg = _context_registration(external, changed)
    before = {str(p): p.read_bytes() for p in external.bundle.parent.rglob('*') if p.is_file()}
    monkeypatch.setattr(api, '_client', lambda: pytest.fail('client built for impossible scope inventory'))
    # Write caller authority first; production capture must not create run files.
    Path(reg['registration_path']).write_bytes(sg.canonical(reg))
    before[str(Path(reg['registration_path']))] = sg.canonical(reg)
    with pytest.raises(ValueError, match='root once and name distinct owners'):
        spec = selected_spec(external, reg)
        api.execute(spec)
    after = {str(p): p.read_bytes() for p in external.bundle.parent.rglob('*') if p.is_file()}
    assert after == before
    assert not external.out_dir.exists()


def test_unique_future_owner_is_deferred_until_record_exists(external):
    from data_sheets_schema import audit_omissions
    reg = _context_registration(external, lambda context: context['scopes'].append(
        dict(context['scopes'][0], owner='/creators/0')))
    spec = selected_spec(external, reg)
    captured = sg.preflight(spec, api._model_settings())
    assert api.build_phase(spec, 'full', carry={}).messages
    assert not spec.full_path.exists()
    receipt = yaml.safe_dump({'bundle_md5': hashlib.md5(spec.bundle.read_bytes()).hexdigest(), 'chunks': []}).encode()
    with pytest.raises(ValueError, match='distinct existing typed owners'):
        audit_omissions.prepare(record=RECORD.encode(), bundle=spec.bundle.read_bytes(),
            manifest=spec.chunk_manifest.read_bytes(), receipt=receipt,
            context=captured.raw(reg['inputs']['context']['path']),
            schema_path=captured.full_schema.sources[0][1], schema_snapshot=captured.full_schema,
            max_output_tokens=4000)


def test_actual_cli_scope_delivery_regate_and_completed_replay(tmp_path, monkeypatch):
    """One real CLI/controller pipeline, with a scripted SDK and real checks."""
    import importlib
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_runtime import CandidatesScript, scripted_client, files
    module = importlib.import_module('data_sheets_schema.cli.api')
    base = replace(specification(tmp_path), arm=module.ARMS['baseline'][0],
                   method=module.ARMS['baseline'][1], label='scope-cli-synthetic_rep1')
    reg = registration_for(base)
    spec = selected_spec(base, reg)
    assert reg['inputs']['source_manifest'] is None
    peer = CandidatesScript(spec, bad_report=True)
    monkeypatch.setattr(api, '_client', lambda: scripted_client(peer))
    args = ['api', 'run', '--project', spec.project, '--label', spec.label,
            '--out-dir', str(spec.out_dir), '--shared-generation-version', '1',
            '--shared-generation-registration', reg['registration_path'], '--yes']
    originals = {path: raw for path, raw in sg.capture(spec).files}
    result = CliRunner().invoke(cli, args)
    (tmp_path / 'scope-cli-output.txt').write_text(result.output)
    assert result.exit_code == 0, (result.output, result.exception)
    phases = ['full', 'full_receipt_completion', runtime.WORKER_PHASE,
              runtime.OMISSION_PHASE, runtime.INTEGRATION_PHASE, 'reconcile_full',
              'report', 'report_regate']
    assert peer.phases == phases
    expected = sg.generation_context(spec)
    calls = []
    for phase, call in zip(phases, peer.calls):
        sg.require_generation_context(spec, call['messages'])
        assert _blocks(call['messages']).count(expected) == 1
        calls.append({'phase': phase, 'sha256': sg.sha(sg.canonical(call)),
                      'scope_sha256': sg.sha(expected.encode())})
    assert spec.provenance_path.exists()
    accounting = ledger._read(spec)
    assert [row['phase'] for row in accounting['rows']] == phases
    assert accounting.get('pending_call') is None
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    assert record['shared_generation']['scientific_support'] == 'unverified evaluator declarations'
    baseline = files(spec)
    no_calls = CandidatesScript(spec)
    repeated = api.execute(replace(spec), client=scripted_client(no_calls))
    assert repeated['already_complete'] and repeated['validation_problems'] == []
    assert no_calls.calls == [] and files(spec) == baseline
    monkeypatch.setattr(api, '_client', lambda: scripted_client(no_calls))
    refused = CliRunner().invoke(cli, args)
    (tmp_path / 'scope-cli-reuse-output.txt').write_text(refused.output)
    assert refused.exit_code == 1 and 'a run label is never reused' in refused.output
    assert no_calls.calls == [] and files(spec) == baseline
    assert all(Path(path).read_bytes() == raw for path, raw in originals.items())
    (tmp_path / 'scope-pipeline-proof.json').write_text(json.dumps({
        'phases': phases, 'actual_sent_wires': calls,
        'accounting_rows': accounting['rows'],
        'ledger_sha256': sg.sha(ledger.ledger_path(spec).read_bytes()),
        'provenance_sha256': sg.sha(spec.provenance_path.read_bytes()),
        'registration_sha256': sg.sha(spec.shared_generation_registration.encode()),
        'source_identities': [{'path': path, 'sha256': sg.sha(raw), 'bytes': len(raw)}
                              for path, raw in originals.items()],
        'completed_replay_no_calls': True, 'cli_reuse_refused_without_calls': True,
        'all_originals_preserved': True, 'provider_calls': False,
        'scientific_approval': False}, indent=2) + '\n')
