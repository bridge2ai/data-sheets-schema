"""Both canary controllers enforce the existing receipt floors on current files."""
from contextlib import contextmanager
import importlib
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
    run.provenance_path.write_text(yaml.safe_dump({'run': {'project':run.project, 'label':run.label, 'method':run.method, 'condition':run.condition}, 'inputs': {'bundle_md5':manifest['bundle_md5']}}))
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
    outcome = api.check_canary_receipts(run)
    assert outcome['passed'] is passed
    if case == 'false_date':
        assert outcome['receipts']['findings_gated'] == 0
        assert outcome['floors']['snippets unverified'] == 1
    if case == 'other_chunk':
        assert outcome['receipts']['snippets']['adjacent'] + outcome['receipts']['snippets']['elsewhere'] == 1
    assert before == {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('arm', ['api','agentic'])
@pytest.mark.parametrize('case, passed', [('valid',True), ('false_date',False), ('missing',False)])
def test_controller_completion_requires_current_receipt_floors(tmp_path, monkeypatch, controllers, arm, case, passed):
    api, native = controllers
    runner = api if arm == 'api' else native
    # main() configures process globals; keep the synthetic launch isolated.
    monkeypatch.setattr(runner.os, 'environ', dict(runner.os.environ))
    monkeypatch.setattr(api_runner, 'MAX_ATTEMPTS', api_runner.MAX_ATTEMPTS)
    run = fixture_record(tmp_path, case)
    monkeypatch.setattr(run, 'render_spec', lambda: {})
    monkeypatch.setattr(run, 'input_identity', lambda: {})
    instruction = tmp_path/'instruction.md'; instruction.write_text('Synthetic offline fixture.')
    initial = tmp_path/'initial.json'; initial.write_text('{}')
    job = {'id':'example_'+arm, 'canary':True, 'execution_arm':arm, 'render_spec':{},
           'input_identity':{}, 'output_directories':[], 'outputs':{},
           'instruction':str(instruction), 'initial_request':str(initial), 'bundle':str(run.bundle)}
    base = {'repository':str(tmp_path), 'claude_version':'offline',
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
        overlay = tmp_path/'overlay.json'
        overlay.write_text(json.dumps({'registration':str(registration), 'registration_sha256':api.sha(registration),
            'allowed_jobs':[job['id']], 'pinned_files':{}, 'environment':{},
            'per_job_environment':{job['id']:{'D4D_LAUNCH_INSTRUCTION':str(instruction)}},
            'cli_flags':[], 'allowed_tools':['Read','Write','Bash'], 'system_prompt':str(instruction),
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
            events=[{'type':'system','subtype':'init','model':'offline-model','apiKeySource':'ANTHROPIC_API_KEY',
                     'claude_code_version':'offline','tools':['Read','Write','Bash']},
                    {'type':'result','terminal_reason':'completed','stop_reason':'end_turn',
                     'modelUsage':{'offline-model':{'contextWindow':1000,'maxOutputTokens':100}}}]
            (kwargs['attempt']/'transcript.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            return 0
        monkeypatch.setattr(runner, 'execute_child', child)
        monkeypatch.setattr(api_runner, 'validate_outputs', lambda *args: [])
        monkeypatch.setattr(api_runner, 'pair_consistency', lambda *args: {'ran':True,'consistent':True})
        monkeypatch.setattr(runner, 'native_evidence_check', lambda *args: {'checked':True,'findings':[]})
        monkeypatch.setattr(agentic_observed, 'observe', lambda *args: {})
        argv=['run_native_canary','--overlay',str(overlay),'--review',str(review),'--job',job['id']]
    review.write_text(json.dumps(verdict));monkeypatch.setattr(sys,'argv',argv)
    before={p:p.read_bytes() for p in run.full_path.parent.rglob('*') if p.is_file()}
    assert runner.main() == (0 if passed else 1)
    result=json.loads((tmp_path/'attempts'/job['id']/'result.json').read_bytes())
    assert result['status'] == ('completed_pending_independent_review' if passed else 'validation_failed')
    check=result['checks']['receipt_acceptance'] if arm=='api' else result['receipt_acceptance']
    assert check['passed'] is passed
    assert before == {p:p.read_bytes() for p in run.full_path.parent.rglob('*') if p.is_file()}
