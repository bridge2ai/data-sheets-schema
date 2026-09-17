"""Both canary controllers enforce the existing receipt floors on current files."""
from contextlib import contextmanager
import importlib
import hashlib
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner, chunking, receipts
from tests.test_download.test_api_runner import spec

CONTROLS = Path(__file__).resolve().parents[1] / 'notes/matched_cborg_2026-09-13'


@pytest.fixture
def controllers(monkeypatch):
    monkeypatch.syspath_prepend(str(CONTROLS))
    monkeypatch.syspath_prepend(str(CONTROLS/'native_controls'))
    return importlib.import_module('run_api_canary'), importlib.import_module('run_native_canary')


def fixture_record(tmp_path, case):
    bundle = tmp_path/'source.txt'
    bundle.write_text('FILE: alpha.txt\nPATH: alpha.txt\n' + '-'*80 +
                      '\nCollection begins 2020-04-03.\n' + '='*80 +
                      '\nFILE: beta.txt\nPATH: beta.txt\n' + '-'*80 +
                      '\nA separate public document describes the research team.\n')
    manifest = chunking.manifest_from_bytes(bundle.read_bytes(), bundle.name)
    chunk_file = tmp_path/'chunks.yaml'
    chunk_file.write_text(yaml.safe_dump(manifest))
    run = spec(project='EXTERNAL', bundle=bundle, manifest=None, profile='neutral',
               condition='generic_v9', chunk_manifest=chunk_file, out_dir=tmp_path/'outputs')
    run.full_path.parent.mkdir(parents=True, exist_ok=True)
    run.core_path.parent.mkdir(parents=True, exist_ok=True)
    record = {'id':'urn:example:dataset', 'name':'Example', 'title':'Example',
              'description':'Collection begins 2020-04-03.',
              'notes':'A separate public document describes the research team.'}
    run.full_path.write_text(yaml.safe_dump(record))
    run.core_path.write_text(yaml.safe_dump(record))
    run.report_path.write_text('Synthetic offline reconciliation report.\n')
    run.provenance_path.write_text(yaml.safe_dump({
        'run': {'project':run.project, 'label':run.label, 'method':run.method, 'condition':run.condition},
        'inputs': {'bundle_path':str(bundle), 'bundle_md5':manifest['bundle_md5'],
                   'chunks': {'path':str(chunk_file), 'sha256':hashlib.sha256(chunk_file.read_bytes()).hexdigest(),
                              'rule':manifest['rule'], 'bundle_name':manifest['bundle'],
                              'chunk_count':manifest['chunk_count']}}}))
    if case == 'bad_provenance':
        run.provenance_path.write_text('not a mapping')
    texts = chunking.chunk_texts(bundle.read_text(), manifest['chunks'])
    source_id = next(c['id'] for c, text in zip(manifest['chunks'], texts) if 'Collection begins' in text)
    selected = manifest['chunks'][-1]['id'] if case == 'other_chunk' else source_id
    entries = [{'id':c['id'], 'status':'nothing_relevant', 'reason':'Synthetic fixture: no extracted claim.'}
               for c in manifest['chunks']]
    if case != 'vacuous':
        target = next(c for c in entries if c['id'] == selected)
        target.update(status='extracted', extracted=[{'slot':'description',
            'snippet':'Collection begins 2020-04-02.' if case == 'false_date' else 'Collection begins 2020-04-03.'}])
        target.pop('reason')
        if case == 'other_chunk':
            # Keep one attesting quote so this case isolates attribution from vacuity.
            target['extracted'].append({'slot':'notes',
                'snippet':'A separate public document describes the research team.'})
    path = receipts.receipt_path(run.core_path.parent, run.project)
    if case != 'missing':
        path.write_text('[' if case == 'unreadable' else yaml.safe_dump({'bundle_md5':manifest['bundle_md5'], 'chunks':entries}))
    return run


@pytest.mark.parametrize('case, passed', [('valid',True), ('false_date',False), ('missing',False),
                                         ('unreadable',False), ('bad_provenance',False),
                                         ('vacuous',False), ('other_chunk',True)])
def test_current_file_receipts_use_existing_floors_without_repair(tmp_path, controllers, case, passed):
    api, _ = controllers
    run = fixture_record(tmp_path, case)
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    outcome = api.check_canary_receipts(run, run.input_identity())
    assert outcome['passed'] is passed
    if case == 'false_date':
        assert outcome['receipts']['findings_gated'] == 0
        assert outcome['floors']['snippets unverified'] == 1
    if case == 'other_chunk':
        assert outcome['receipts']['snippets']['adjacent'] + outcome['receipts']['snippets']['elsewhere'] == 1
    assert before == {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def redirect_to_historical_bytes(run, monkeypatch):
    """Exercise real receipt recovery, with only the historical-byte lookup stubbed."""
    from data_sheets_schema.canary import receipt_floors
    record = yaml.safe_load(run.provenance_path.read_bytes())
    assert receipt_floors(api_runner._receipts_block(run, record))['snippets unverified'] == 1
    alternative = run.bundle.read_bytes().replace(b'2020-04-03', b'2020-04-02')
    mapping = chunking.manifest_from_bytes(alternative, run.bundle.name)
    chunks = run.bundle.parent/'alternative_chunks.yaml'
    chunks.write_text(chunking.dump_manifest(mapping))
    record['inputs'] = {'bundle_path':'unrelated_committed_source.txt', 'bundle_md5':mapping['bundle_md5'],
        'chunks': {'path':str(chunks), 'sha256':hashlib.sha256(chunks.read_bytes()).hexdigest(),
                   'bundle_name':mapping['bundle'], 'rule':mapping['rule'], 'chunk_count':mapping['chunk_count']}}
    run.provenance_path.write_text(yaml.safe_dump(record))
    receipt_file = receipts.receipt_path(run.core_path.parent, run.project)
    receipt = yaml.safe_load(receipt_file.read_bytes())
    receipt['bundle_md5'] = mapping['bundle_md5']
    receipt_file.write_text(yaml.safe_dump(receipt))
    lookups = []
    def historical(path, md5=None, sha256=None):
        assert path == record['inputs']['bundle_path'] and md5 == mapping['bundle_md5']
        lookups.append(path)
        return alternative, {'commit':'synthetic-history', 'date':'2020-01-01',
                             'md5':md5, 'sha256':hashlib.sha256(alternative).hexdigest()}
    monkeypatch.setattr('data_sheets_schema.provenance.bundle_bytes_for', historical)
    recovered = api_runner._receipts_block(run, record)
    assert recovered['checked'] and not any(receipt_floors(recovered).values())
    assert recovered['bundle_basis']['source'] == 'git blob'
    assert len(lookups) == 1
    return lookups


@pytest.mark.parametrize('change', ['missing_inputs', 'missing_bundle_path', 'missing_bundle_hash',
                                    'bundle_hash', 'bundle_sha', 'bundle_path', 'chunk_path',
                                    'chunk_hash', 'chunk_rule', 'chunk_name', 'chunk_count'])
def test_provenance_cannot_change_registered_receipt_inputs(tmp_path, controllers, change):
    api, _ = controllers
    run = fixture_record(tmp_path, 'valid')
    registered = run.input_identity()
    record = yaml.safe_load(run.provenance_path.read_bytes()); inputs = record['inputs']
    if change == 'missing_inputs': del record['inputs']
    elif change == 'missing_bundle_path': del inputs['bundle_path']
    elif change == 'missing_bundle_hash': del inputs['bundle_md5']
    elif change == 'bundle_hash': inputs['bundle_md5'] = '0'*32
    elif change == 'bundle_sha': inputs['bundle_sha256'] = '0'*64
    elif change in {'bundle_path', 'chunk_path'}:
        source = run.bundle if change == 'bundle_path' else run.chunk_manifest
        alias = tmp_path/('same_bytes_'+source.name); alias.write_bytes(source.read_bytes())
        if change == 'bundle_path': inputs['bundle_path'] = str(alias)
        else: inputs['chunks']['path'] = str(alias)
    elif change == 'chunk_hash': inputs['chunks']['sha256'] = '0'*64
    elif change == 'chunk_rule': inputs['chunks']['rule']['max_lines'] += 1
    elif change == 'chunk_name': inputs['chunks']['bundle_name'] = 'elsewhere.txt'
    elif change == 'chunk_count': inputs['chunks']['chunk_count'] += 1
    run.provenance_path.write_text(yaml.safe_dump(record))
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = api.check_canary_receipts(run, registered)
    assert result['passed'] is False and result['receipts'] is None
    assert before == {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


NATIVE_ONLY = ('usage_missing', 'deadline_stop', 'forbidden_denial', 'prescribed_denial', 'late_stop_denial',
               'init_mismatch_denial', 'evidence_unreadable', 'manifest_read_denial', 'interrupted',
               'unicode_jsonl', 'playbook_term_denial', 'playbook_grounding_denial', 'playbook_report_denial')


@pytest.mark.parametrize('arm', ['api','agentic'])
@pytest.mark.parametrize('case, passed', [('valid',True), ('false_date',False), ('missing',False),
                                       ('redirected_provenance',False), ('usage_missing',False),
                                       ('deadline_stop',False), ('forbidden_denial',True), ('prescribed_denial',False),
                                       ('late_stop_denial',False), ('init_mismatch_denial',False),
                                       ('evidence_unreadable',False), ('manifest_read_denial',False),
                                       ('interrupted',False), ('unicode_jsonl',True),
                                       ('playbook_term_denial',False), ('playbook_grounding_denial',False),
                                       ('playbook_report_denial',False)])
def test_controller_completion_requires_current_receipt_floors(tmp_path, monkeypatch, controllers, arm, case, passed):
    api, native = controllers
    runner = api if arm == 'api' else native
    if case in NATIVE_ONLY and arm == 'api':
        pytest.skip('a terminal result and the attempt deadline are the native runtime\'s')
    # main() configures process globals; keep the synthetic launch isolated.
    monkeypatch.setattr(runner.os, 'environ', dict(runner.os.environ))
    monkeypatch.setattr(api_runner, 'MAX_ATTEMPTS', api_runner.MAX_ATTEMPTS)
    run = fixture_record(tmp_path, 'false_date' if case == 'redirected_provenance'
                         else 'valid' if case in NATIVE_ONLY else case)
    registered_inputs = run.input_identity()
    pinned = {p:p.read_bytes() for p in (run.bundle,run.chunk_manifest)}
    lookups = redirect_to_historical_bytes(run, monkeypatch) if case == 'redirected_provenance' else []
    rendered = {}
    if arm == 'agentic':
        from data_sheets_schema.agentic_runtime import toolchain
        rendered = {'agentic_toolchain': toolchain(), 'agentic_artifact_paths': {
            'full': str(run.full_path), 'core': str(run.core_path), 'report': str(run.report_path)}}
    monkeypatch.setattr(run, 'render_spec', lambda: rendered)
    monkeypatch.setattr(run, 'input_identity', lambda: registered_inputs)
    instruction = tmp_path/'instruction.md'; instruction.write_text('Synthetic offline fixture.')
    initial = tmp_path/'initial.json'; initial.write_text('{}')
    job = {'id':'example_'+arm, 'canary':True, 'execution_arm':arm, 'render_spec':rendered,
           'input_identity':registered_inputs, 'output_directories':[],
           'outputs': rendered.get('agentic_artifact_paths', {}),
           'instruction':str(instruction), 'initial_request':str(initial), 'bundle':str(run.bundle)}
    if arm == 'agentic':
        job['manifest'] = str(tmp_path/'source_manifest.yaml')
        job['outputs'] = {**job['outputs'], 'provenance': str(run.provenance_path)}
    base = {'repository':str(tmp_path), 'claude_version':'offline', 'python':sys.executable,
            'provider_base_url':'https://api.cborg.lbl.gov', 'model':{'model':'offline-model'},
            'budget':{'additional_usd':200, 'per_attempt_usd':5,
                      'ledger_path':str(tmp_path/'billing.json'), 'prices_per_token':{}},
            'generation':{'jobs':[job], 'canary_order':[job['id']], 'external_canary':{'status':'registered'},
                          'api_max_attempts':1, 'sdk_max_retries':0,
                          'api_phase_deadline_seconds':api_runner.PHASE_WALL_CLOCK_SECONDS,
                          'agentic_attempt_deadline_seconds':1}}
    registration = tmp_path/'registration.json'; registration.write_text(json.dumps(base))
    review = tmp_path/'review.json'
    verdict = {'verdict':'approve', 'ci_conclusion':'success', 'allowed_jobs':[job['id']],
               'registration_sha256':api.sha(registration)}
    for name in ['verify','verify_history']:
        monkeypatch.setattr(runner, name, lambda *args: None)
    monkeypatch.setattr(runner, 'spec_for', lambda *args: run)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-never-sent')
    import anthropic
    monkeypatch.setattr(anthropic, 'Anthropic', lambda **kw: object())
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *args, **kw: 'offline')
    if arm == 'api':
        monkeypatch.setattr(runner, 'CappedClient', lambda *args, **kw: SimpleNamespace(
            messages=SimpleNamespace(require_active=lambda: None, requests_started=0)))
        # A stale passing check in the returned object must not mask the file's receipt.
        monkeypatch.setattr(api_runner, 'execute', lambda *args, **kw: {
            'validation_problems':[], 'checks':{'receipts':{'checked':True, 'findings':[]}}})
        monkeypatch.setattr(api_runner, 'provider_identity', lambda: {'base_url':base['provider_base_url']})
        argv=['run_api_canary','--registration',str(registration),'--review',str(review),'--job',job['id']]
    else:
        from data_sheets_schema import agentic_observed
        from native_command_policy import build_command_policy
        policy = build_command_policy(job, sys.executable, tmp_path)
        overlay = tmp_path/'overlay.json'
        overlay.write_text(json.dumps({'registration':str(registration), 'registration_sha256':api.sha(registration),
            'allowed_jobs':[job['id']], 'pinned_files':{}, 'environment':{},
            'per_job_environment':{job['id']:{'D4D_LAUNCH_INSTRUCTION':str(instruction)}},
            'cli_flags':[], 'per_job_command_policy':{job['id']:policy}, 'system_prompt':str(instruction),
            'native_limits_observed_offline':{'context_window':1000,'max_output_tokens':100}}))
        verdict['overlay_sha256']=api.sha(overlay)
        monkeypatch.setattr(runner, 'verified_executable', lambda *args: sys.executable)
        class OfflineProxy:
            token='offline'; unfinished_handlers=0; failed=threading.Event()
            def __init__(self, **kw):
                ticket=kw['ledger'].reserve(kw['attempt'],'.01','offline')
                kw['ledger'].settle(ticket,'.001',response_sha256='offline',usage={})
            @contextmanager
            def running(self): yield 'http://127.0.0.1:1'
        monkeypatch.setattr(runner, 'NativeProxy', OfflineProxy)
        def child(*args, **kwargs):
            # The controller must deliver the complete policy through structured
            # settings; the native CLI list parser loses complex Python rules.
            argv = args[0]
            assert '--allowedTools' not in argv
            assert json.loads(argv[argv.index('--settings') + 1]) == {'permissions': {'allow': policy['allowed_tools']}}
            terminal={'type':'result','terminal_reason':'completed','stop_reason':'end_turn',
                      'modelUsage':{'offline-model':{'contextWindow':1000,'maxOutputTokens':100}}}
            if case != 'usage_missing':
                # The runtime's finalized accounting, which the completion gate requires (#2002/#2008).
                terminal['usage']={'input_tokens':1,'output_tokens':1}
            if case == 'forbidden_denial':
                terminal['permission_denials']=[{'tool_name':'Bash','tool_use_id':'d1',
                    'tool_input':{'command':sys.executable+' -m data_sheets_schema.cli --help'}}]
            if case in ('prescribed_denial', 'late_stop_denial'):
                terminal['permission_denials']=[{'tool_name':'Bash','tool_use_id':'d2',
                    'tool_input':{'command':sys.executable+' -m data_sheets_schema.cli receipts check --label L'}}]
            if case.startswith('playbook_'):
                name = {'playbook_term_denial': 'linkml_term_validator',
                        'playbook_grounding_denial': 'check_run',
                        'playbook_report_denial': 'check_report'}[case]
                command = next(command for command in policy['command_examples'] if name in command)
                terminal['permission_denials'] = [{'tool_name':'Bash','tool_use_id':'delegated',
                    'tool_input':{'command':command}}]
            if case == 'late_stop_denial':
                terminal['is_error'] = True     # stops after the classification (#2037)
            if case == 'init_mismatch_denial':
                terminal['permission_denials']=[{'tool_name':'Bash','tool_use_id':'d3',
                    'tool_input':{'command':sys.executable+' -m data_sheets_schema.cli --help'}}]
            if case == 'manifest_read_denial':
                terminal['permission_denials']=[{'tool_name':'Read','tool_use_id':'d4',
                    'tool_input':{'file_path':job['manifest']}}]
            if case == 'unicode_jsonl':
                # JSON.stringify emits these literal characters inside JSON
                # strings. They are data, not JSONL record separators.
                terminal['result'] = 'source text\u0085next\u2028line\u2029paragraph'
            events=[{'type':'system','subtype':'init','model':'offline-model','apiKeySource':'ANTHROPIC_API_KEY',
                     'claude_code_version':'offline','tools':['Read','Write','Bash']}, terminal]
            if case == 'init_mismatch_denial':
                events[0]['model'] = 'another-model'   # stops before the classification (#2037)
            if case == 'interrupted':
                (kwargs['attempt']/'transcript.jsonl').write_text(json.dumps(events[0])+'\n')
                raise KeyboardInterrupt
            if case == 'deadline_stop':
                # A child killed at the deadline mid-write: no result line and
                # undecodable trailing bytes (#2019).
                (kwargs['attempt']/'transcript.jsonl').write_bytes(
                    (json.dumps(events[0])+'\n').encode() + b'{"type":"assistant","message":{"id":"m1","content":"\xff\xfe')
                reason = 'native attempt deadline elapsed; retain all incomplete charge reservations'
                kwargs['record_stop'](reason)   # as execute_child does before closing admission (#2023)
                # main()'s wiring must really write the ledger here, not later (#2030)
                held = json.loads((tmp_path/'billing.json').read_bytes()).get('stopped_attempts') or {}
                assert [v['reason'] for v in held.values()] == ['controller: ' + reason]
                raise runner.BudgetStop(reason)
            (kwargs['attempt']/'transcript.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events))
            return 0
        monkeypatch.setattr(runner, 'execute_child', child)
        monkeypatch.setattr(api_runner, 'validate_outputs', lambda *args: [])
        monkeypatch.setattr(api_runner, 'pair_consistency', lambda *args: {'ran':True,'consistent':True})
        monkeypatch.setattr(runner, 'native_evidence_check', lambda *args: {'checked':True,'findings':[]})
        if case == 'evidence_unreadable':
            def unreadable(*args):
                raise FileNotFoundError('evidence/audit.json')
            monkeypatch.setattr(runner, 'native_evidence_check', unreadable)
            monkeypatch.setattr(run, 'render_version', 12)   # the renderer that checks evidence (>= 9)
        argv=['run_native_canary','--overlay',str(overlay),'--review',str(review),'--job',job['id']]
    review.write_text(json.dumps(verdict));monkeypatch.setattr(sys,'argv',argv)
    before={p:p.read_bytes() for p in run.full_path.parent.rglob('*') if p.is_file()}
    assert runner.main() == (0 if passed else 1)
    result=json.loads((tmp_path/'attempts'/job['id']/'result.json').read_bytes())
    if case == 'deadline_stop':
        # The original stop survives the diagnostics (#2019), the transcript
        # state is stated (#2014) and the ledger records the stop (#2018).
        assert result['status'] == 'stopped' and result['error_type'] == 'BudgetStop'
        assert result['reason_source'] == 'controller' and 'deadline' in result['reason']
        assert result['transcript_terminal_result'] == 'absent' and 'ledger' in result['transcript_accounting_note']
        assert (tmp_path/'attempts'/job['id']/'controller_traceback.txt').is_file()
        state = json.loads((tmp_path/'billing.json').read_bytes())
        (stop,) = state['stopped_attempts'].values()
        assert stop['reason'].startswith('controller: native attempt deadline elapsed')
        assert result['ledger_stop_recorded'] == stop['reason']
        assert result['pre_close_ledger_stop'] == {'ledger_stop_recorded': stop['reason']}
        # Nothing was classified, and the receipt says so (#2032).
        assert 'permission_denials' not in result
        assert result['permission_denials_note'] == runner.STOPPED_DENIALS_NOTE
        return
    if case in ('late_stop_denial', 'init_mismatch_denial'):
        # A stop with a result line still classifies it and names what would
        # disqualify (#2037), whether the stop came after the classification
        # or before it.
        assert result['status'] == 'stopped' and result['transcript_terminal_result'] == 'present'
        assert 'permission_denials_note' not in result and 'validation_problems' not in result
        (denial,) = result['permission_denials']
        if case == 'late_stop_denial':
            assert result['reason'] == 'native attempt failed or stopped before completion'
            assert denial['classification'] == 'prescribed' and len(result['disqualifying_denials']) == 1
        else:
            assert result['reason'] == 'native runtime initialization differs from registration'
            assert denial['classification'] == 'not_prescribed' and result['disqualifying_denials'] == []
        return
    if case == 'interrupted':
        # An interrupted controller names its stop, says it classified
        # nothing and records the stop in the ledger (#2038).
        assert result['status'] == 'stopped' and result['error_type'] == 'KeyboardInterrupt'
        assert result['reason'] == 'unexpected KeyboardInterrupt' and result['reason_source'] == 'controller'
        assert result['permission_denials_note'] == runner.STOPPED_DENIALS_NOTE
        (stop,) = json.loads((tmp_path/'billing.json').read_bytes())['stopped_attempts'].values()
        assert stop['reason'] == 'controller: unexpected KeyboardInterrupt' == result['ledger_stop_recorded']
        return
    if case == 'evidence_unreadable':
        # Unusable evidence inputs fail validation after every other check;
        # they do not stop the attempt (#2038).
        assert result['status'] == 'validation_failed'
        assert result['evidence_assertions'] == {'checked': False, 'error_type': 'FileNotFoundError'}
        assert 'explicit evidence assertions could not be checked (FileNotFoundError)' in result['validation_problems']
        assert result['native_observed'] and result['permission_denials'] == []
        return
    if case == 'manifest_read_denial':
        # main() classifies with the registered reads, the manifest included (#2033).
        assert result['status'] == 'validation_failed'
        (denial,) = result['permission_denials']
        assert denial['classification'] == 'prescribed'
        assert [p for p in result['validation_problems'] if p.startswith('denied ')] == [
            'denied prescribed call (Read): a registered input the instruction reads']
        return
    assert result['status'] == ('completed_pending_independent_review' if passed else 'validation_failed')
    check=result['checks']['receipt_acceptance'] if arm=='api' else result['receipt_acceptance']
    if case in ('forbidden_denial', 'prescribed_denial') or case.startswith('playbook_'):
        # Every denial is listed and classified; only the prescribed one disqualifies (#2026).
        (denial,) = result['permission_denials']
        assert denial['classification'] == ('not_prescribed' if case == 'forbidden_denial' else 'prescribed')
        assert result['receipt_acceptance']['passed'] is True
        problems = [p for p in result['validation_problems'] if p.startswith('denied ')]
        assert len(problems) == (0 if case == 'forbidden_denial' else 1)
        assert 'stopped' != result['status'] and 'permission_denials_note' not in result
        return
    if case == 'usage_missing':
        # The receipt passed; the transcript's missing finalized accounting is what refused completion (#2002).
        assert check['passed'] is True
        assert 'transcript carries no terminal result with complete usage' in result['validation_problems']
        assert result['native_observed'].get('terminal_results_without_usage') == 1
    else:
        assert check['passed'] is passed
    assert pinned == {p:p.read_bytes() for p in pinned}
    assert len(lookups) == (1 if case == 'redirected_provenance' else 0)
    assert before == {p:p.read_bytes() for p in run.full_path.parent.rglob('*') if p.is_file()}
