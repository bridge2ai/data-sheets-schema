"""Real API dispatcher/state machine with invented SDK replies, never a provider."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, shared_generation as sg
from data_sheets_schema import receipt_completion as receipts, usage_ledger as ledger
from data_sheets_schema import source_heading_routing as draft, source_heading_runtime as routing
from data_sheets_schema import source_heading_admission as admission
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for
from tests.test_shared_generation_runtime import Script, response, offline, files
from tests.test_source_heading_runtime import declaration, encoded


@pytest.fixture(scope='module')
def draft_files():
    root = Path(__file__).resolve().parents[1]
    source = encoded({'@context': {'rai': draft.RAI}, '@graph': [{'@id': 'urn:synthetic',
        'completeness': 'A sample dataset is planned.',
        'rai:dataCollectionMissingData': 'A sample dataset is planned.'}]})
    row = {'id': 'row', 'heading': 'Completeness', 'profile_id': 'synthetic',
        'local_property': 'completeness', 'external_property': 'rai:dataCollectionMissingData',
        'external_uri': draft.RAI + 'dataCollectionMissingData'}
    profile = {'format': 'source_heading_profile_v1', 'id': 'synthetic', 'authority_status': 'draft/unreviewed',
        'prefixes': {'rai': draft.RAI}, 'bindings': [{'row_id': 'row', 'source_sha256': draft._sha(source),
            'entity_pointer': '/@graph/0', 'entity_id': 'urn:synthetic',
            'local_value_sha256': draft._sha(b'A sample dataset is planned.'),
            'external_value_sha256': draft._sha(b'A sample dataset is planned.'), 'evidence_id': 'synthetic'}]}
    return draft.prepare(base=b'', source=source, profile=encoded(profile),
        crosswalk=encoded({'format': 'source_heading_crosswalk_v1', 'authority_status': 'draft/unreviewed', 'rows': [row]}),
        scope=encoded({'source_sha256': draft._sha(source), 'entity_pointers': ['/@graph/0']}),
        schema_path=root/'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        ttl=(root/'src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl').read_bytes(),
        recommendations=(root/'notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv').read_bytes(),
        comprehensive=(root/'src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv').read_bytes())


def selected_spec(tmp_path, draft_files, mode='declared_heading_spans_v1', *, cli_arm=False, profile=None, source_naming=None):
    base = specification(tmp_path)
    if profile is not None:
        base = replace(base, profile=profile)
    if cli_arm:
        base = replace(base, arm='BASELINE (input documents only)', method='claudecode_api')
    base.bundle.write_bytes(b'FILE: protocol.txt\nPATH: protocol.txt\nCompleteness\n'
                           b'A sample dataset is planned.\nMaintenance Plan\n'
                           b'No sensitivity assertion is supplied.\n')
    manifest = chunking.build_manifest(base.bundle)
    base.chunk_manifest.write_text(chunking.dump_manifest(manifest))
    bundle = base.bundle.read_bytes()
    if mode == 'declared_heading_spans_v1':
        controls = declaration(bundle, manifest)
    else:
        doc = routing._documents(bundle, manifest)[0][1]
        start = bundle.index(b'A sample dataset is planned.')
        controls = {'selection': encoded({'format': 'source_heading_value_membership_v1', 'rows': [
            {'evidence_id': 'synthetic', 'value_kind': kind, 'document_ordinal': 1,
             'document_sha256': doc['sha256'], 'byte_range': [start, start+28]}
            for kind in ('local', 'external')]})}
    capture = routing.prepare_condition(draft_files=draft_files, mode=mode, bundle=bundle,
        manifest=base.chunk_manifest.read_bytes(), max_projection_bytes=2_000_000, **controls)
    path = tmp_path/'routing.json'; path.write_bytes(capture)
    if source_naming is not None:
        source = tmp_path/'selected-source.yaml'
        source.write_text(yaml.safe_dump({'projects': {'EXAMPLE': {'sources': [
            {'id': 'protocol', 'processed_file': 'protocol.txt', 'source_type': 'documentation', 'priority': 1}],
            'naming': source_naming}}}))
        base = replace(base, manifest=source, manifest_line=type(base).__dataclass_fields__['manifest_line'].default)
    reg = registration_for(base)
    condition = routing.MODES[mode]
    reg.update(format=sg.ROUTING_FORMAT, selection=sg.descriptor(version=2, condition=condition),
        routing={'mode': mode, 'artifact': sg.file_pin(path), 'generation_limits': {
            'max_request_bytes': 32_000_000, 'max_input_tokens_per_call': 850_000,
            'max_output_tokens': 128_000, 'context_limit_tokens': 900_000,
            'context_limit_basis': 'Synthetic fixture, not a measured capacity guarantee',
            'max_calls': 10, 'aggregate_input_tokens': 4_000_000, 'aggregate_output_tokens': 1_280_000}})
    reg['receipt'].update(format='receipt_completion_registration_v3', condition=condition,
        runtime_policy_sha256=receipts.policy_identity(version=3)['sha256'])
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    return replace(base, condition=condition, render_version=27, shared_generation_version=2,
        shared_generation_registration=raw.decode(), api_playbook_version=3,
        receipt_completion_version=3, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        provider=reg['runtime']['provider'])


class RoutingScript(Script):
    def create(self, **kwargs):
        blocks = [p['text'] for p in kwargs['messages'][-1]['content']]
        if receipts.policy_text(version=3) in blocks:
            # Recognition of the selected receipt policy is the only fixture
            # extension. Actual supplied kwargs are retained without rewriting.
            self.calls.append(deepcopy(kwargs)); self.phases.append(receipts.PHASE)
            inventory = json.loads(blocks[0])
            return response(yaml.safe_dump({'rereceipt': [{'path': p, 'unsupported': True,
                'reason': 'Synthetic unknown support; independent judgment required.'}
                for p in inventory['requested_paths']]}))
        return super().create(**kwargs)


def client(spec):
    messages = RoutingScript(spec)
    c = SimpleNamespace(messages=messages, base_url='https://example.invalid', max_retries=2)
    c.with_options = lambda **kw: SimpleNamespace(messages=messages, base_url=c.base_url, max_retries=kw['max_retries'])
    return c


def normalized(call):
    result = {k: deepcopy(v) for k, v in call.items() if k not in ('extra_body',)}
    if 'extra_body' in call:
        result.update(deepcopy(call['extra_body']))
    return result


def test_actual_sent_routing_counts_usage_and_completed_zero_calls(tmp_path, draft_files):
    spec = selected_spec(tmp_path, draft_files)
    c = client(spec)
    result = api.execute(spec, client=c)
    assert result['validation_problems'] == []
    assert c.messages.phases == ['full', receipts.PHASE, 'typed_audit_worker',
        'typed_audit_omission', 'typed_audit_integration', 'reconcile_full', 'report']
    wire = sg.routing_context(spec)
    for actual in c.messages.calls:
        matches = [p for m in actual['messages'] if m['role'] == 'user' for p in m['content']
                   if p.get('text', '').startswith(routing.MARKER)]
        assert matches == [{'type': 'text', 'text': wire}]
    assert len(c.messages.count_calls) == len(c.messages.calls) == 7
    # Every endpoint count is for the same exact logical send. The SDK count
    # endpoint intentionally omits output/temperature fields.
    for count, actual in zip(c.messages.count_calls, c.messages.calls):
        expected = {k: actual[k] for k in ('model', 'system', 'messages', 'thinking', 'extra_body') if k in actual}
        assert count == expected
    state = ledger._read(spec)[admission.KEY]
    ordinary_calls = [call for phase, call in zip(c.messages.phases, c.messages.calls) if admission.ordinary(phase)]
    assert len(state['rows']) == 3
    for row, actual in zip(state['rows'], ordinary_calls):
        request = admission._load(row['request'])
        assert request['payload'] == normalized(actual)
        assert request['count']['request_sha256'] == sg.sha(sg.canonical(normalized(actual)))
        assert row['usage_id'] in {r['usage_id'] for r in result['usage']}
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    assert record['shared_generation']['protocol'] == 'shared_generation_v2'
    assert record['shared_generation']['routing']['scientific_eligibility'] is False
    before = files(spec)
    replay = client(spec)
    again = api.execute(replace(spec), client=replay)
    assert again['already_complete'] and not replay.messages.calls and not replay.messages.count_calls
    assert files(spec) == before
    # The real completed path must refuse a lost ordinary admission even if
    # legacy usage, final records, typed acceptance and receipt remain intact.
    path = ledger.ledger_path(spec); old = path.read_bytes()
    value = json.loads(old); value[admission.KEY]['rows'].pop(0)
    path.write_bytes(sg.canonical(value))
    try:
        with pytest.raises((ValueError, ledger.UsageLedgerError)):
            api.execute(replace(spec), client=replay)
        assert not replay.messages.calls and not replay.messages.count_calls
    finally:
        path.write_bytes(old)
    (tmp_path/'actual-counts.json').write_bytes(sg.canonical(c.messages.count_calls))
    (tmp_path/'actual-sends.json').write_bytes(sg.canonical(c.messages.calls))


@pytest.mark.parametrize('limit,value,expected_counts', [
    ('max_output_tokens', 32_000, 0), ('max_request_bytes', 1, 0),
    ('max_input_tokens_per_call', 1, 1)])
def test_actual_dispatch_refuses_bounds_before_admission(tmp_path, draft_files, limit, value, expected_counts):
    spec = selected_spec(tmp_path, draft_files)
    reg = json.loads(spec.shared_generation_registration)
    reg['routing']['generation_limits'][limit] = value
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    spec = replace(spec, shared_generation_registration=raw.decode())
    c = client(spec)
    with pytest.raises((ValueError, ledger.UsageLedgerError)):
        api.execute(spec, client=c)
    assert not c.messages.calls and len(c.messages.count_calls) == expected_counts
    state = ledger._read(spec)
    assert state['rows'] == [] and state.get('pending_call') is None
    assert not state.get(admission.KEY, {}).get('rows')


def test_actual_cli_render_selects_exact_registered_version_and_refuses_crossed_flag(tmp_path, draft_files):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    spec = selected_spec(tmp_path, draft_files, cli_arm=True)
    reg = json.loads(spec.shared_generation_registration)
    args = ['api', 'render-prompt', '--project', spec.project, '--label', spec.label,
        '--shared-generation-version', '2', '--shared-generation-registration', reg['registration_path']]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert api.resolve_prompt(spec) in result.output
    # render-prompt displays the instruction; actual build_phase carries the
    # separately registered factual projection, verified by the SDK test.
    sg.require_routing_context(spec, api.build_phase(spec, 'full', carry={}).messages)
    wrong = list(args); wrong[7] = '1'
    refused = CliRunner().invoke(cli, wrong)
    assert refused.exit_code == 1 and 'version differs from registration' in refused.output


def test_v2_record_contract_is_distinct_and_keeps_v1_closed(tmp_path):
    from data_sheets_schema.provenance import build_record, check_record
    from tests.test_shared_generation_provenance import block
    bundle = tmp_path/'source.txt'; bundle.write_text('Synthetic provenance only.\n')
    record = build_record('EXAMPLE', 'claudecode_api', 'synthetic-routing_rep1', mode='live',
        input_bundle=bundle, input_verified=True, concat_dir=tmp_path,
        manifest=None, selected_manifest=None, outputs={}).data
    v2 = {**block(), 'protocol': 'shared_generation_v2', 'routing': {'scientific_eligibility': False}}
    assert check_record({**record, 'shared_generation': v2}) == ([], None)
    for bad in ({k: v for k, v in v2.items() if k != 'routing'},
                {**v2, 'protocol': 'shared_generation_v1'}, {**v2, 'routing': None}):
        problems, failure = check_record({**record, 'shared_generation': bad})
        assert problems and failure is None


def test_strict_selected_request_and_crossed_mode_refusal(tmp_path, draft_files):
    spec = selected_spec(tmp_path, draft_files, mode='captured_json_values_v1')
    req = api.build_phase(spec, 'full', carry={})
    sg.require_routing_context(spec, req.messages)
    assert 'captured_json_values_v1' in sg.routing_context(spec)
    with pytest.raises(ValueError):
        replace(spec, condition=routing.MODES['declared_heading_spans_v1'])


def test_completed_sdk_usage_survives_routing_response_save_failure(tmp_path, draft_files, monkeypatch):
    spec = selected_spec(tmp_path, draft_files)
    c = client(spec)
    original = receipts._save
    def fail_response(spec, name, value, **kwargs):
        if name == 'routing_response.json':
            raise OSError('injected routing response persistence failure')
        return original(spec, name, value, **kwargs)
    monkeypatch.setattr(receipts, '_save', fail_response)
    with pytest.raises(OSError, match='injected routing response'):
        api.execute(spec, client=c)
    state = ledger._read(spec)
    observed = {'sends': len(c.messages.calls), 'counts': len(c.messages.count_calls),
                'rows': state['rows'], 'pending_call': state.get('pending_call'),
                'routing_journal': state.get('source_heading_admissions')}
    (tmp_path/'observation.json').write_text(json.dumps(observed,indent=2)+'\n')
    assert observed['sends'] == observed['counts'] == 1
    assert len(state['rows']) == 1, 'complete reported usage was lost before fallible routing bookkeeping'
    row = state['rows'][0]
    assert row['input_tokens'] == 100 and row['output_tokens'] == 50
    assert row['phase'] == 'full' and row['usage_id'] == state['source_heading_admissions']['rows'][0]['usage_id']
    assert state.get('pending_call') is None
    replay = client(spec)
    with pytest.raises((ValueError, ledger.UsageLedgerError)):
        api.execute(replace(spec), client=replay)
    assert not replay.messages.calls and not replay.messages.count_calls

"""Draft saved-reader controls, copied into the owned test file after reader exit."""
def test_actual_completed_capture_is_portable_and_refuses_changed_bytes(tmp_path, draft_files, monkeypatch):
    import base64
    import builtins
    import io
    import os
    import socket
    import subprocess
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    from data_sheets_schema import source_heading_completed as complete
    spec = selected_spec(tmp_path, draft_files)
    c = client(spec)
    result = api.execute(spec, client=c)
    raw = Path(result['routing_completed_capture']['path']).read_bytes()
    initial = complete.recheck_completed(raw)
    assert initial['complete'] and initial['scientific_eligibility'] is False
    value = json.loads(raw)
    forbidden = {os.path.abspath(row['path']) for row in value['files']}
    ledger_pin = next(p for p in value['files'] if p['path'] == value['selection']['ledger'])
    saved_ledger = json.loads(base64.b64decode(value['blobs'][ledger_pin['sha256']]))
    forbidden.add(saved_ledger[complete.FORM_KEY]['naming']['path'])
    original = tmp_path/'output'
    preserved = tmp_path/'preserved-output'
    original.rename(preserved)
    capture = tmp_path/'relocated-capture.json'; capture.write_bytes(raw)
    original_open, original_io_open, original_resolve = builtins.open, io.open, Path.resolve
    def checked_open(fn):
        def call(path, mode='r', *args, **kwargs):
            if isinstance(path, (str, Path)) and os.path.abspath(path) in forbidden:
                raise AssertionError('original captured path opened: ' + str(path))
            if any(flag in mode for flag in ('w', 'a', '+', 'x')):
                raise AssertionError('pure reader attempted a write')
            return fn(path, mode, *args, **kwargs)
        return call
    original_os_open = os.open
    def checked_os_open(path, flags, *args, **kwargs):
        if isinstance(path, (str, bytes, Path)) and os.path.abspath(os.fsdecode(path)) in forbidden:
            raise AssertionError("original captured path opened through os.open")
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("pure reader attempted an os.open write")
        return original_os_open(path, flags, *args, **kwargs)
    def checked_resolve(path, *args, **kwargs):
        if os.path.abspath(path) in forbidden:
            raise AssertionError('original captured path resolved: ' + str(path))
        return original_resolve(path, *args, **kwargs)
    def forbidden_call(*a, **k):
        raise AssertionError('pure reader attempted a network/child/execution call')
    try:
        with monkeypatch.context() as m:
            m.setattr(builtins, 'open', checked_open(original_open))
            m.setattr(io, 'open', checked_open(original_io_open))
            m.setattr(Path, 'resolve', checked_resolve)
            m.setattr(os, 'open', checked_os_open)
            m.setattr(socket, 'getaddrinfo', forbidden_call)
            m.setattr(subprocess, 'Popen', forbidden_call)
            m.setattr(socket.socket, 'connect', forbidden_call)
            m.setattr(api, 'execute', forbidden_call)
            m.setattr(c.messages, 'create', forbidden_call)
            m.setattr(c.messages, 'count_tokens', forbidden_call)
            assert complete.recheck_completed(raw) == initial
            output = CliRunner().invoke(cli, ['api', 'check-routing-completed', str(capture)])
            assert output.exit_code == 0, output.output + repr(output.exception)
            assert json.loads(output.output) == initial
            changed_display = deepcopy(value)
            changed_display['selection']['path_display']['core_source'] = 'unrelated-record.yaml'
            with pytest.raises(ledger.UsageLedgerError, match='original core differs'):
                complete.recheck_completed(sg.canonical(changed_display))
            reg = json.loads(spec.shared_generation_registration)
            def with_schema_claims(claims):
                altered = deepcopy(value)
                pin = next(p for p in altered['files'] if p['path'] == altered['selection']['paths']['provenance'])
                previous = pin['sha256']
                record = yaml.safe_load(base64.b64decode(altered['blobs'][previous]))
                record['schema'].update(claims)
                changed = yaml.safe_dump(record, sort_keys=False).encode()
                pin.update(sha256=sg.sha(changed), bytes=len(changed))
                altered['blobs'][pin['sha256']] = base64.b64encode(changed).decode()
                if not any(p['sha256'] == previous for p in altered['files']):
                    del altered['blobs'][previous]
                return sg.canonical(altered)
            import hashlib
            md5s = {}
            for name in ('full', 'core'):
                root = reg['inputs'][name + '_schema']['sources'][0]
                md5s[name + '_md5'] = hashlib.md5(base64.b64decode(value['blobs'][root['sha256']])).hexdigest()
                with pytest.raises(ledger.UsageLedgerError, match='schema MD5 claim'):
                    complete.recheck_completed(with_schema_claims({name + '_md5': '0' * 32}))
                with pytest.raises(ledger.UsageLedgerError, match='schema path claim'):
                    complete.recheck_completed(with_schema_claims({name + '_path': 'unrelated/schema.yaml'}))
            assert complete.recheck_completed(with_schema_claims(md5s)) == initial
            targets = (str(spec.full_path), str(spec.core_path), str(spec.report_path),
                       str(spec.bundle), str(api._receipt_path(spec)),
                       reg['inputs']['full_schema']['sources'][0]['path'], reg['routing']['artifact']['path'])
            for logical in targets:
                altered = deepcopy(value)
                pin = next(p for p in altered['files'] if p['path'] == logical)
                previous = pin['sha256']
                changed = base64.b64decode(altered['blobs'][previous]) + b'\n# altered captured bytes\n'
                pin.update(sha256=sg.sha(changed), bytes=len(changed))
                altered['blobs'][pin['sha256']] = base64.b64encode(changed).decode()
                if not any(p['sha256'] == previous for p in altered['files']):
                    del altered['blobs'][previous]
                with pytest.raises((ValueError, ledger.UsageLedgerError)):
                    complete.recheck_completed(sg.canonical(altered))
            # Ledger content is directly selected by path, so these honest
            # outer rehashes reach generation/accounting/chronology checks.
            for kind in ('usage_id', 'usage_counter', 'lost_admission', 'lost_typed_stage'):
                altered = deepcopy(value)
                pin = next(p for p in altered['files'] if p['path'] == altered['selection']['ledger'])
                previous = pin['sha256']
                data = json.loads(base64.b64decode(altered['blobs'][previous]))
                if kind == 'usage_id': data['rows'][0]['usage_id'] = 'foreign-call'
                elif kind == 'usage_counter': data['rows'][0]['input_tokens'] += 1
                elif kind == 'lost_admission': data[admission.KEY]['rows'].pop(0)
                else: data['typed_audit']['stages'].pop(0)
                changed = sg.canonical(data)
                pin.update(sha256=sg.sha(changed), bytes=len(changed))
                altered['blobs'][pin['sha256']] = base64.b64encode(changed).decode()
                if not any(p['sha256'] == previous for p in altered['files']): del altered['blobs'][previous]
                with pytest.raises((ValueError, ledger.UsageLedgerError)):
                    complete.recheck_completed(sg.canonical(altered))
            missing = deepcopy(value)
            provenance_pin = next(p for p in value['files'] if p['path'] == value['selection']['paths']['provenance'])
            record = yaml.safe_load(base64.b64decode(value['blobs'][provenance_pin['sha256']]))
            original_full = next(p['path'] for p in record['intermediates'] if p['phase'].endswith('_full.yaml'))
            omitted = next(p for p in missing['files'] if p['path'] == original_full)
            missing['files'].remove(omitted)
            if not any(p['sha256'] == omitted['sha256'] for p in missing['files']): del missing['blobs'][omitted['sha256']]
            with pytest.raises((ValueError, ledger.UsageLedgerError)):
                complete.recheck_completed(sg.canonical(missing))
    finally:
        preserved.rename(original)
    assert raw == capture.read_bytes()


def test_actual_regated_report_captured_lineage(tmp_path, draft_files):
    from data_sheets_schema import source_heading_completed as complete
    spec = selected_spec(tmp_path, draft_files)
    c = client(spec)
    c.messages.bad_report = True
    result = api.execute(spec, client=c)
    assert c.messages.phases[-2:] == ['report', 'report_regate']
    captured = Path(result['routing_completed_capture']['path']).read_bytes()
    checked = complete.recheck_completed(captured)
    assert checked['complete'] and len(checked['usage']) == 8
    assert checked['checks']['evidence_assertions']['findings'] == []


@pytest.mark.parametrize('module', ['american_spelling.py', 'profiles.py'])
def test_selected_registration_binds_actual_normalization_bytes(tmp_path, draft_files, monkeypatch, module):
    from data_sheets_schema import resources
    spec = selected_spec(tmp_path, draft_files)
    registration = spec.shared_generation_registration.encode()
    selected = sg.parse_registration(registration)
    name = 'src/data_sheets_schema/' + module
    original = resources.resource_path
    raw = original(name).read_bytes()
    copy = tmp_path/'installed-normalizer.py'
    copy.write_bytes(raw)
    # Only the implementation location is redirected to an identical owned
    # copy; the actual descriptor and registration checker read its real bytes.
    monkeypatch.setattr(resources, 'resource_path', lambda p: copy if str(p) == name else original(p))
    assert sg.parse_registration(registration) == selected
    copy.write_bytes(raw + b'\n# changed installed normalizer\n')
    with pytest.raises(ValueError, match='descriptor|selection|registration'):
        sg.parse_registration(registration)


def test_nonempty_captured_vocabulary_does_not_resolve_original_path(tmp_path, draft_files, monkeypatch):
    import os
    from data_sheets_schema import source_heading_completed as complete
    spec = selected_spec(tmp_path, draft_files, profile='bridge2ai')
    spec.bind_api_header_values(api._model_settings())
    captured = sg.capture(spec)
    expected = sg.digest_text(spec, 'Dataset')
    frozen = complete._CompletedSpec.from_render_spec(spec.render_spec(), project=spec.project, method=spec.method, label=spec.label)
    frozen._captured_authority = captured
    reg = captured.document()
    pin = reg['inputs']['profile']['vocabulary']
    assert captured.raw(pin['path'])
    spec._captured_path_display = {'bundle_name': 'stray live override'}
    def live_boundary(*args, **kwargs):
        raise RuntimeError('actual live canonical boundary reached')
    with monkeypatch.context() as m:
        m.setattr(chunking, 'canonical_name', live_boundary)
        with pytest.raises(RuntimeError, match='actual live canonical boundary'):
            sg.marked_bundle(spec)
    forbidden = {os.path.abspath(path) for path, _ in captured.files}
    original_resolve, original_read = Path.resolve, Path.read_bytes
    def resolve(path, *a, **kw):
        if os.path.abspath(path) in forbidden:
            raise AssertionError('captured authority path resolved')
        return original_resolve(path, *a, **kw)
    def read(path, *a, **kw):
        if os.path.abspath(path) in forbidden:
            raise AssertionError('captured authority path read')
        return original_read(path, *a, **kw)
    monkeypatch.setattr(Path, 'resolve', resolve)
    monkeypatch.setattr(Path, 'read_bytes', read)
    assert sg.digest_text(frozen, 'Dataset') == expected
    assert complete._authority(reg, captured.registration, complete._Reader(captured.files)).identity() == captured.identity()
    changed = tuple((name, raw + b'\n# changed captured vocabulary\n' if name == pin['path'] else raw)
                    for name, raw in captured.files)
    with pytest.raises(ValueError, match='authority bytes differ'):
        complete._authority(reg, captured.registration, complete._Reader(changed))


def test_selected_form_captures_actual_default_instrument_per_invocation(tmp_path, draft_files, monkeypatch):
    import os
    from data_sheets_schema import grounding, identifiers
    from data_sheets_schema.run_schema import IdentifierRules
    from data_sheets_schema import source_heading_completed as complete
    spec = selected_spec(tmp_path, draft_files, source_naming={'canonical_label': 'Other Project', 'variants': ['Different Programme']})
    spec.bind_api_header_values(api._model_settings())
    authority = sg.capture(spec)
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.full_path.write_text('description: Sample Programme\n')
    spec.core_path.write_text('description: Sample Programme\n')
    cwd = tmp_path/'caller'; default = cwd/'data/preprocessed/source_manifest.yaml'
    default.parent.mkdir(parents=True)
    default.write_bytes(b'naming:\r\n  EXAMPLE:\r\n    canonical_label: Sample Project\r\n    variants: [Sample Programme]\r\n')
    monkeypatch.chdir(cwd)
    # The actual selected producer calls the same form worker and stores the
    # bytes it read during that call, not those found later by the exporter.
    expected = grounding.form_facts(spec.full_path, spec.core_path)
    original_full = spec.full_path.read_bytes()
    original_core = spec.core_path.read_bytes()
    read_naming = grounding._capture_declared_naming
    def mutate_after_first_pass():
        observed = read_naming()
        spec.full_path.write_bytes(original_full + b'# changed with the same counts\n')
        return observed
    with monkeypatch.context() as m:
        m.setattr(grounding, '_capture_declared_naming', mutate_after_first_pass)
        first = complete.measure_form(spec)
    assert first == expected and first['gc_label_variant_occurrences'] == 2
    original_row = deepcopy(ledger._read(spec)[complete.FORM_KEY])
    assert original_row['full'] == sg.file_pin(spec.full_path, original_full)
    assert original_row['full']['sha256'] != sg.sha(spec.full_path.read_bytes())
    assert original_row['naming']['path'] == str(default)
    assert b'Sample Programme' in __import__('base64').b64decode(original_row['naming']['base64'])
    # A warm second invocation sees current default bytes; selected source
    # metadata remains different and unchanged throughout.
    default.write_text('naming: {}\n')
    second = complete.measure_form(spec)
    assert second['gc_label_variant_occurrences'] == 0
    assert ledger._read(spec)[complete.FORM_KEY]['naming']['sha256'] != original_row['naming']['sha256']
    default.unlink()
    third = complete.measure_form(spec)
    assert third['gc_label_variant_occurrences'] == 0
    assert ledger._read(spec)[complete.FORM_KEY]['naming']['present'] is False
    frozen = complete._CompletedSpec.from_render_spec(spec.render_spec(), project=spec.project, method=spec.method, label=spec.label)
    frozen._paths = {'full':str(spec.full_path), 'core':str(spec.core_path)}
    frozen._captured_authority = authority
    frozen._ledger = ledger._read(spec)
    frozen._ledger[complete.FORM_KEY] = original_row
    rules = IdentifierRules(frozenset(identifiers.declared_prefixes()),
        frozenset(identifiers.uriorcurie_slots()), frozenset(identifiers.person_slots()), ())
    current_full = spec.full_path.read_text()
    full, core = original_full.decode(), original_core.decode()
    with pytest.raises(ledger.UsageLedgerError, match='measurement identity'):
        complete._captured_form(frozen, current_full, core, rules)
    def deny(*a, **kw):
        raise AssertionError('saved form reopened original files')
    with monkeypatch.context() as m:
        m.setattr(Path, 'read_bytes', deny); m.setattr(Path, 'read_text', deny); m.setattr(Path, 'resolve', deny)
        assert complete._captured_form(frozen, full, core, rules) == first
        frozen._ledger[complete.FORM_KEY] = deepcopy(original_row)
        frozen._ledger[complete.FORM_KEY]['naming']['base64'] = 'e30='
        with pytest.raises(ValueError, match='bytes differ'):
            complete._captured_form(frozen, full, core, rules)
