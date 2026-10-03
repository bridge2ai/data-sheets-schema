"""Neutral local engineering only; genuine helpers, no provider/native calls."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, source_review
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attempt_supervisor as supervisor
from data_sheets_schema import native_supervisor_gates as gates
from data_sheets_schema import native_supervisor_authority as authority


def make_case(root):
    root.mkdir()
    corpus = root/'corpus'; corpus.mkdir()
    full = {'id': 'https://example.org/offline-neutral', 'name': 'offline-neutral',
            'title': 'Offline Neutral Dataset',
            'description': 'This synthetic dataset supports offline software verification.'}
    bundle = ('FILE: neutral.txt\nPATH: neutral.txt\n'
        'AI-authored synthetic software fixture, not empirical research evidence.\n'
        + '\n'.join(str(v) for v in full.values())+'\n').encode()
    (corpus/'bundle.txt').write_bytes(bundle)
    (corpus/'chunks.yaml').write_text(chunking.dump_manifest(chunking.build_manifest(corpus/'bundle.txt')))
    (corpus/'sources.yaml').write_text(yaml.safe_dump({'projects': {'EXAMPLE': {'sources': [
        {'id': 'neutral_documentation', 'processed_file': 'neutral.txt', 'source_type': 'documentation'}]}}}))
    spec = api.RunSpec(project='EXAMPLE', arm='baseline', method='claudecode_direct', label='neutral_full_chain',
        condition='generic_v9', bundle=corpus/'bundle.txt', chunk_manifest=corpus/'chunks.yaml',
        manifest=corpus/'sources.yaml', profile='neutral', render_version=16, runtime='Claude Code (direct)',
        provider='neutral fixture (no provider)', run_date='2026-10-02', prompt_text_env=True,
        native_source_attribution_version=1, native_source_attribution_max_checks=3)
    full_text = yaml.safe_dump(full, sort_keys=False)
    manifest = yaml.safe_load((corpus/'chunks.yaml').read_bytes())
    receipt = {'bundle_md5': hashlib.md5(bundle).hexdigest(), 'chunks': [
        {'id': row['id'], 'status': 'extracted', 'extracted': [
            {'slot': key, 'snippet': value} for key, value in full.items()]}
        for row in manifest['chunks']]}
    def review(artifact):
        inventory = source_review.inventory(full_text, artifact)
        return {'artifact': artifact, 'sha256': inventory['sha256'], 'values': [
            {'path': item['path'], 'claims': [{'text': item['text'], 'verdict': 'supported',
                'attributed_to': ['neutral.txt'], 'claim_status': 'fact', 'source_status': 'fact',
                'evidence': [{'source': 'neutral.txt', 'chunk': manifest['chunks'][0]['id'], 'quote': item['text']}],
                'reason': 'This explicitly synthetic source states this exact neutral fixture value.'}]}
            for item in inventory['values']]}
    audit = {'findings': [], 'summary': 'The four synthetic values are unchanged.',
             'source_review': review('original_full')}
    report = '# Reconciliation\n\nAll four synthetic values are retained unchanged.\n\n## Evidence assertions\n```json\n'+json.dumps(
        {'claims': [], 'source_review': review('final_full')})+'\n```\n'
    fixture = root/'fixture.json'
    fixture.write_bytes(draft._encoded({'full': full_text, 'receipt': yaml.safe_dump(receipt),
        'audit': json.dumps(audit), 'report': report}))
    instruction = root/'instruction.md'; instruction.write_text(spec.instruction)
    raw = draft._encoded(draft.registration(spec))
    selected = root/'composition.json'; selected.write_bytes(draft._encoded(composition.composition(raw, instruction)))
    synthetic = {'model': 'neutral-fixture-model', 'auxiliary_models': [], 'effort': 'neutral-fixture-effort',
        'limits': {'contextWindow': 100000, 'maxOutputTokens': 10000}, 'runtime_version': 'neutral-local-v1',
        'usage': {'input_tokens': 10, 'output_tokens': 2, 'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0},
        'model_usage': {'neutral-fixture-model': {'inputTokens': 10, 'outputTokens': 2,
            'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0, 'contextWindow': 100000, 'maxOutputTokens': 10000}},
        'cost_usd': 0}
    value = supervisor.registration(selected, fixture, attempt_id='attempt-one',
        attempt_directory=root/'attempt-one', evidence_directory=root/'evidence',
        deadline_seconds=180, synthetic_runtime=synthetic)
    return {'spec': spec, 'value': value, 'raw': draft._encoded(value), 'root': root}


@pytest.fixture
def case(tmp_path):
    return make_case(tmp_path/'neutral')


def test_real_complete_neutral_chain(case, monkeypatch):
    # No old executable discovery/auth/launch entry point may be used.
    with authority.loaded_dependencies(case['value']['dependencies']) as modules:
        for module, names in [('prepare_direct', ['auth_evidence']), ('run_direct_canary', ['main']),
                              ('run_api_canary', ['main']), ('budgeted_cborg', ['cborg_client'])]:
            for name in names:
                if hasattr(modules[module], name):
                    monkeypatch.setattr(modules[module], name, lambda *a, **k: pytest.fail('live path invoked'))
        result = supervisor.supervise(case['raw'])
    assert result['engineering_completion'], json.dumps(result, indent=2)
    assert set(result['gates']) == set(supervisor.GATES)
    assert all(g['checked'] is True and g['passed'] is True for g in result['gates'].values())
    assert result['gates']['receipts']['floors'] and not any(result['gates']['receipts']['floors'].values())
    assert all(result[key] == 'not_assessed' for key in supervisor.UNASSESSED)
    assert supervisor.read_final(case['raw']) == result
    with pytest.raises(ValueError, match='new|resume'):
        supervisor.supervise(case['raw'])


@pytest.mark.parametrize('change', ['mode', 'kind', 'version_bool', 'deadline_bool', 'unknown', 'raw_composition'])
def test_authority_refuses_before_reserving(case, change):
    value = deepcopy(case['value'])
    if change == 'mode': value['execution'] = 'native'
    elif change == 'kind': value['kind'] = 'd4d_direct_arm_registration'
    elif change == 'version_bool': value['version'] = True
    elif change == 'deadline_bool': value['deadline_seconds'] = True
    elif change == 'unknown': value['argv'] = ['anything']
    else:
        path = Path(value['composition']); path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises((ValueError, KeyError)):
        supervisor.supervise(draft._encoded(value))
    assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('field', ['model', 'effort', 'limits', 'usage', 'runtime_version', 'model_usage', 'auxiliary_models', 'cost_usd'])
def test_missing_neutral_selection_is_never_defaulted(case, field):
    value = deepcopy(case['value']); del value['synthetic_runtime'][field]
    with pytest.raises(ValueError):
        supervisor.supervise(draft._encoded(value))
    assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('boundary', ['registration.json', 'started.json'])
def test_partial_start_consumes_attempt_without_dispatch(case, monkeypatch, boundary):
    write = supervisor.durable_new
    def broken(path, raw):
        if Path(path).name == boundary:
            (Path(path).parent/'injected-partial').write_bytes(raw[:12])
            raise OSError('injected durable start failure')
        return write(path, raw)
    monkeypatch.setattr(supervisor, 'durable_new', broken)
    with pytest.raises(OSError, match='durable start'):
        supervisor.supervise(case['raw'])
    assert (case['root']/'attempt-one/injected-partial').exists()
    with pytest.raises(ValueError, match='new|resume'):
        supervisor.supervise(case['raw'])


def test_additive_loader_rejects_foreign_origin_and_restores_state(case, monkeypatch):
    from types import SimpleNamespace
    before = list(sys.path)
    marker = SimpleNamespace(__file__='/foreign/run_direct_canary.py')
    monkeypatch.setitem(sys.modules, 'run_direct_canary', marker)
    with pytest.raises(ValueError, match='another origin'):
        with authority.loaded_dependencies(case['value']['dependencies']):
            pytest.fail('foreign dependency admitted')
    assert sys.path == before and sys.modules['run_direct_canary'] is marker


def test_durable_writer_never_replaces_existing_result(tmp_path):
    target = tmp_path/'final.json'; target.write_bytes(b'original')
    with pytest.raises(FileExistsError):
        supervisor.durable_new(target, b'new')
    assert target.read_bytes() == b'original'
    assert list(tmp_path.glob('.final.json.pending-*'))


def test_other_helper_interpreter_refuses_before_attempt(case):
    selected = Path(case['value']['composition'])
    value = draft._json(selected.read_bytes())
    reg = draft._json(value['registration_raw_json'])
    spec = api.RunSpec.from_render_spec(reg['render_spec'], project=reg['project'], method=reg['method'], label=reg['label'])
    spec._agentic_toolchain = {**spec._agentic_toolchain, 'python': '/bin/echo'}
    instruction = Path(value['instruction_path']); instruction.write_text(spec.instruction)
    raw = draft._encoded(draft.registration(spec))
    selected.write_bytes(draft._encoded(composition.composition(raw, instruction)))
    with pytest.raises(ValueError, match='exact pinned local interpreter'):
        supervisor.registration(selected, case['value']['fixture'], attempt_id='attempt-one',
            attempt_directory=case['value']['attempt_directory'], evidence_directory=case['value']['evidence_directory'],
            deadline_seconds=180, synthetic_runtime=case['value']['synthetic_runtime'])
    assert not (case['root']/'attempt-one').exists()


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    case = make_case(tmp_path_factory.mktemp('supervisor-completed')/'neutral')
    result = supervisor.supervise(case['raw'])
    assert result['engineering_completion'], result['first_stop']
    with authority.loaded_dependencies(case['value']['dependencies']) as controls:
        prepared = gates.capture(case['value']['composition'], case['value']['attempt_directory'], controls)
        projections = gates.project(prepared, case['root']/'probe-projections')
        yield case, result, prepared, projections, controls


@pytest.mark.parametrize('mutation', ['missing_inputs', 'missing_chunks', 'wrong_bundle_path', 'missing_bundle_hash',
    'wrong_bundle_md5', 'wrong_bundle_sha', 'wrong_chunk_path', 'missing_chunk_sha', 'wrong_chunk_sha',
    'wrong_rule', 'wrong_name', 'bool_count', 'wrong_count', 'policy_mismatch'])
def test_captured_receipts_refuse_same_real_wrapper_failures(completed, tmp_path, mutation):
    case, _, prepared, _, controls = completed
    record = deepcopy(prepared['record'])
    if mutation == 'missing_inputs': record.pop('inputs')
    elif mutation == 'missing_chunks': record['inputs'].pop('chunks')
    elif mutation == 'wrong_bundle_path': record['inputs']['bundle_path'] = '/different/bundle.txt'
    elif mutation == 'missing_bundle_hash':
        record['inputs'].pop('bundle_sha256', None); record['inputs'].pop('bundle_md5', None)
    elif mutation == 'wrong_bundle_md5': record['inputs']['bundle_md5'] = '0'*32
    elif mutation == 'wrong_bundle_sha': record['inputs']['bundle_sha256'] = '0'*64
    elif mutation == 'wrong_chunk_path': record['inputs']['chunks']['path'] = '/different/chunks.yaml'
    elif mutation == 'missing_chunk_sha': record['inputs']['chunks'].pop('sha256')
    elif mutation == 'wrong_chunk_sha': record['inputs']['chunks']['sha256'] = '0'*64
    elif mutation == 'wrong_rule': record['inputs']['chunks']['rule'] = 'different'
    elif mutation == 'wrong_name': record['inputs']['chunks']['bundle_name'] = 'different.txt'
    elif mutation == 'bool_count': record['inputs']['chunks']['chunk_count'] = True
    elif mutation == 'wrong_count': record['inputs']['chunks']['chunk_count'] += 1
    else: record.setdefault('prompts', {}).setdefault('request', {}).setdefault('spec', {})['receipt_completion_version'] = 1
    target = tmp_path/'changed-provenance.yaml'; target.write_text(yaml.safe_dump(record))
    class SpecProxy:
        provenance_path = target
        def __getattr__(self, key): return getattr(case['spec'], key)
    registered = prepared['state'].reg['inputs']
    expected = controls['run_api_canary'].check_canary_receipts(SpecProxy(), {
        'bundle': registered['bundle'], 'chunks': registered['chunk_manifest']})
    assert expected['passed'] is False, (mutation, expected)
    try:
        actual = gates.receipt_gate(prepared, record, prepared['schema_paths'], prepared['phase1_original'], controls)
    except (ValueError, KeyError, TypeError):
        actual = {'passed': False}
    assert actual['passed'] is False, (mutation, actual)


def test_captured_receipts_equal_actual_current_canary(completed):
    case, _, prepared, _, controls = completed
    registered = prepared['state'].reg['inputs']
    expected = controls['run_api_canary'].check_canary_receipts(case['spec'], {
        'bundle': registered['bundle'], 'chunks': registered['chunk_manifest']})
    actual = gates.receipt_gate(prepared, prepared['record'], prepared['schema_paths'], prepared['phase1_original'], controls)
    assert expected['passed'] is actual['passed'] is True
    assert actual['floors'] == expected['floors']
    for field in ('chunks', 'slots', 'snippets', 'findings', 'findings_gated'):
        assert actual['receipts'][field] == expected['receipts'][field]


@pytest.mark.parametrize('change', ['report_bytes', 'report_missing', 'captured_hardlink', 'captured_mtime'])
def test_readback_binds_generated_report_and_captured_metadata(completed, tmp_path, change):
    case = completed[0]
    assert supervisor.read_final(case['raw'])['engineering_completion']
    report = case['root']/'evidence/attribution-replay.json'
    full = Path(case['spec']._agentic_artifact_paths['full'])
    raw, report_stat, full_stat = report.read_bytes(), report.stat(), full.stat()
    extra = tmp_path/'new-probe-alias'
    try:
        if change == 'report_bytes': report.write_bytes(raw+b'\n')
        elif change == 'report_missing': report.rename(extra)
        elif change == 'captured_hardlink': os.link(full, extra)
        else: os.utime(full, ns=(full_stat.st_atime_ns, full_stat.st_mtime_ns+1_000_000))
        with pytest.raises((OSError, ValueError), match='generated replay|metadata|regular'):
            supervisor.read_final(case['raw'])
    finally:
        if change == 'report_missing': extra.rename(report)
        if change == 'report_bytes': report.write_bytes(raw)
        if change == 'captured_hardlink': extra.unlink()
        os.utime(report, ns=(report_stat.st_atime_ns, report_stat.st_mtime_ns))
        os.utime(full, ns=(full_stat.st_atime_ns, full_stat.st_mtime_ns))
    assert supervisor.read_final(case['raw'])['engineering_completion']


@pytest.mark.parametrize('boundary', ['directory_fsync', 'staging_unlink'])
def test_actual_marker_publication_failure_keeps_unusable_two_link_evidence(tmp_path, monkeypatch, boundary):
    import stat
    target = tmp_path/'published.json'
    ordinary_fsync, ordinary_unlink = os.fsync, os.unlink
    def fsync(fd):
        if boundary == 'directory_fsync' and target.exists() and stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError('injected marker directory fsync failure')
        return ordinary_fsync(fd)
    def unlink(path, *args, **kwargs):
        if boundary == 'staging_unlink' and Path(path).name.startswith('.published.json.pending-'):
            raise OSError('injected marker staging unlink failure')
        return ordinary_unlink(path, *args, **kwargs)
    monkeypatch.setattr(os, 'fsync', fsync); monkeypatch.setattr(os, 'unlink', unlink)
    with pytest.raises(OSError, match='marker'):
        supervisor.durable_new(target, b'{"fixture":true}\n')
    assert target.stat().st_nlink == 2 and list(tmp_path.glob('.published.json.pending-*'))
    with pytest.raises(ValueError, match='single-link'):
        supervisor._file(target, 'publication marker')


@pytest.mark.parametrize('mutation,gate', [
    ('exit_bool', 'terminal'), ('missing_init', 'terminal'), ('wrong_model', 'terminal'),
    ('no_usage', 'accounting'), ('bool_usage', 'accounting'), ('negative_usage', 'accounting'),
    ('foreign_model', 'accounting'), ('wrong_limits', 'accounting'), ('missing_cost', 'accounting'),
    ('changed_fixture_count', 'accounting'), ('float_fixture_cost', 'accounting'),
    ('pending_workers', 'shutdown'), ('first_stop', 'first_stop'), ('live_failure', 'live_attribution'),
    ('phase_drop', 'phase_history'), ('bad_schema', 'schema'), ('different_pair', 'pair'),
    ('evidence_failure', 'evidence'), ('missing_receipt', 'receipts'), ('malformed_receipt', 'receipts')])
def test_independent_required_gate_cannot_be_lost(completed, tmp_path, mutation, gate):
    case, result, source, projections, controls = completed
    # Reuse immutable captured source/metadata, copying only the declared test
    # counterfactual. No published trace or source fixture is rewritten.
    prepared = {**source, 'events': deepcopy(source['events']), 'final_result': deepcopy(source['final_result'])}
    prepared['snapshot'] = deepcopy(source['snapshot'])
    copies = dict(projections)
    status, shutdown, live, first_stop = 0, deepcopy(result['shutdown']), deepcopy(result['gates']['live_attribution']['result']), None
    terminal = next(event for event in prepared['events'] if event.get('type') == 'result')
    if mutation == 'exit_bool': status = False
    elif mutation == 'missing_init': prepared['events'] = [e for e in prepared['events'] if e.get('subtype') != 'init']
    elif mutation == 'wrong_model': next(e for e in prepared['events'] if e.get('subtype') == 'init')['model'] = 'other'
    elif mutation == 'no_usage': terminal.pop('usage')
    elif mutation == 'bool_usage': terminal['usage']['input_tokens'] = True
    elif mutation == 'negative_usage': terminal['usage']['output_tokens'] = -1
    elif mutation == 'foreign_model': terminal['modelUsage']['foreign'] = {'outputTokens': 1}
    elif mutation == 'wrong_limits': terminal['modelUsage']['neutral-fixture-model']['contextWindow'] = 1
    elif mutation == 'missing_cost': terminal.pop('total_cost_usd')
    elif mutation == 'changed_fixture_count': terminal['usage']['input_tokens'] += 1
    elif mutation == 'float_fixture_cost': terminal['total_cost_usd'] = 0.0
    elif mutation == 'pending_workers': shutdown['unfinished_control_workers'] = 1
    elif mutation == 'first_stop': first_stop = 'earlier controller failure'
    elif mutation == 'live_failure': live['draft_gate_passed'] = False
    elif mutation == 'phase_drop':
        prepared['events'] = [e for e in prepared['events'] if not any(
            block.get('name') == 'Bash' and 'derive core' in (block.get('input') or {}).get('command', '')
            for block in (e.get('message') or {}).get('content', []))]
    elif mutation in ('bad_schema', 'different_pair'):
        path = str(source['snapshot'].path(case['spec']._agentic_artifact_paths['core']))
        raw = b'not_a_real_slot: invalid\n' if mutation == 'bad_schema' else b'id: https://example.org/different\nname: offline-neutral\ntitle: Offline Neutral Dataset\n'
        prepared['snapshot'].raw[path] = raw
        copy = tmp_path/'core.yaml'; copy.write_bytes(raw); copies[path] = copy
    elif mutation == 'evidence_failure': prepared['final_result']['findings'] = [{'kind': 'injected evidence failure'}]
    else:
        path = str(source['snapshot'].path(case['spec']._agentic_artifact_paths['receipt']))
        if mutation == 'missing_receipt': prepared['snapshot'].raw.pop(path)
        else: prepared['snapshot'].raw[path] = b'[]\n'
    checked = gates.check(prepared, copies, {**case['value']['synthetic_runtime'],
        'attempt_directory': case['value']['attempt_directory']}, controls,
        exit_code=status, shutdown=shutdown, live=live, first_stop=first_stop)
    assert set(checked) == set(supervisor.GATES)
    assert checked[gate]['passed'] is False, (mutation, checked[gate])


def test_sealed_checks_do_not_read_original_artifact_paths(completed, monkeypatch):
    case, result, prepared, projections, controls = completed
    protected = set(prepared['snapshot'].raw)
    ordinary_bytes, ordinary_text = Path.read_bytes, Path.read_text
    def check_bytes(path, *args, **kwargs):
        assert str(path.absolute()) not in protected, f'live artifact reread: {path}'
        return ordinary_bytes(path, *args, **kwargs)
    def check_text(path, *args, **kwargs):
        assert str(path.absolute()) not in protected, f'live artifact reread: {path}'
        return ordinary_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_bytes', check_bytes)
    monkeypatch.setattr(Path, 'read_text', check_text)
    checked = gates.check(prepared, projections, {**case['value']['synthetic_runtime'],
        'attempt_directory': case['value']['attempt_directory']}, controls, exit_code=0,
        shutdown=result['shutdown'], live=result['gates']['live_attribution']['result'], first_stop=None)
    assert all(row['passed'] for row in checked.values()), {key: row for key, row in checked.items() if not row['passed']}


@pytest.mark.parametrize('boundary', ['final.json', 'published.json'])
def test_failed_final_publication_cannot_resume_or_claim_published(case, monkeypatch, boundary):
    ordinary = supervisor.durable_new
    def broken(path, raw):
        if Path(path).name == boundary:
            raise OSError('injected final publication failure')
        return ordinary(path, raw)
    monkeypatch.setattr(supervisor, 'durable_new', broken)
    with pytest.raises(OSError, match='final publication'):
        supervisor.supervise(case['raw'])
    assert (case['root']/'attempt-one/transcript.jsonl').is_file()
    assert not (case['root']/'evidence/published.json').exists()
    with pytest.raises((OSError, ValueError)):
        supervisor.read_final(case['raw'])
    with pytest.raises(ValueError, match='new|resume'):
        supervisor.supervise(case['raw'])
