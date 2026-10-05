"""Fixed engine boundary and old facade fault-seam preservation; no child calls."""
from dataclasses import replace
from types import ModuleType, SimpleNamespace
import sys

import pytest

from data_sheets_schema import native_execution as old
from data_sheets_schema import native_execution_engine as engine
from data_sheets_schema import native_execution_authority as authority


def test_old_facade_keeps_current_effect_functions(monkeypatch):
    sentinel = OSError('same original exception through public seam')
    seen = []
    def verify(raw):
        seen.append(raw)
        raise sentinel
    monkeypatch.setattr(old.registration, 'verified', verify)
    with pytest.raises(OSError) as caught:
        old.launch(b'exact registration', review_path='r', ci_path='c', launch_word_path='w')
    assert caught.value is sentinel
    assert seen == [b'exact registration']
    for name, effect in (('_file', 'file'), ('durable_new', 'durable_new'),
            ('_sync_directory', 'sync_directory'), ('_mkdir_durable', 'mkdir_durable'),
            ('_signals', 'signals'), ('_now', 'now'), ('_probe_runtime', 'probe_runtime'),
            ('expected_runtime_observation', 'expected_runtime_observation'),
            ('authorizations', 'authorizations'), ('_unchanged', 'unchanged')):
        unique = lambda *a, **k: None
        monkeypatch.setattr(old, name, unique)
        assert getattr(old._engine_bindings()[1], effect) is unique


def test_fixed_contract_cannot_select_foreign_semantic_module():
    contract, _ = old._engine_bindings()
    contract.require_fixed()
    for field in ('registration', 'composition', 'authority', 'gates', 'replay', 'shared'):
        with pytest.raises(ValueError, match='fixed package'):
            replace(contract, **{field: ModuleType('foreign_plugin')}).require_fixed()
    with pytest.raises(ValueError, match='fixed package'):
        replace(contract, kind='caller_chosen_kind').require_fixed()


def test_legacy_transport_receives_original_spec_without_new_phase_check():
    contract, _ = old._engine_bindings()
    exact = object()
    assert contract.transport_phase_spec(SimpleNamespace(spec=exact)) is exact


def test_new_transport_requires_truthful_axis_and_mandatory_policy_observer():
    contract, _ = old._engine_bindings()
    contract = replace(contract, kind='d4d_native_shared_attempt')
    checked=[]
    adapter=SimpleNamespace(spec=SimpleNamespace(render_version=26, native_shared_generation_version=1),
        policy={'registered': True}, classify=lambda:None, observe=lambda:None,
        require_phase_authority=lambda:checked.append(True))
    assert contract.transport_phase_spec(adapter) is None
    assert checked == [True]
    for name, value in (('render_version', 25), ('render_version', 26.0),
                        ('native_shared_generation_version', True), ('native_shared_generation_version', 0)):
        before=getattr(adapter.spec,name)
        setattr(adapter.spec,name,value)
        with pytest.raises(ValueError,match='selected policy and phase'):
            contract.transport_phase_spec(adapter)
        setattr(adapter.spec,name,before)
    adapter.policy={}
    with pytest.raises(ValueError,match='selected policy and phase'):
        contract.transport_phase_spec(adapter)


def test_engine_in_actual_source_closure_and_foreign_loaded_origin_refused(monkeypatch):
    identity=authority.dependency_identity()
    assert 'src/data_sheets_schema/native_execution_engine.py' in identity['base']['package_sources']
    foreign=ModuleType('data_sheets_schema.native_execution_engine')
    foreign.__file__='/outside-selected-package/native_execution_engine.py'
    monkeypatch.setitem(sys.modules, foreign.__name__, foreign)
    with pytest.raises(ValueError,match='another origin'):
        authority.dependency_identity()


@pytest.mark.parametrize('present',[
    ('runtime-observation.json',), ('keep-awake.json',),
    ('runtime-observation.json','keep-awake.json'),
])
def test_public_read_final_recomputes_each_present_lifecycle_artifact(tmp_path,monkeypatch,present):
    """Synthetic failed publication; real disk/readback and canonical gates.

    Registration parsing alone is supplied as a private fixture seam. This is
    not a launch/auth fixture and does not claim an accepted native attempt.
    """
    from data_sheets_schema import native_attribution_registration as encoding
    from data_sheets_schema import native_execution_gates as checks
    attempt=tmp_path/'attempt';attempt.mkdir()
    evidence=tmp_path/'evidence';evidence.mkdir()
    executable=tmp_path/'synthetic-runtime-file';executable.write_bytes(b'never executed\n');executable.chmod(0o700)
    policy={'policy':'not_applicable','host_platform':sys.platform,'basis':'synthetic readback only'}
    value={'attempt_directory':str(attempt),'evidence_directory':str(evidence),
        'attempt_id':'synthetic-readback','composition_sha256':'a'*64,
        'runtime':{'executable':{'path':str(executable),'sha256':encoding._sha(executable.read_bytes()),
            'version':'synthetic'},'auth':{'loggedIn':True,'authMethod':'synthetic',
            'apiProvider':'synthetic','subscriptionType':'synthetic'},'keep_awake':policy},'environment':{}}
    raw=encoding._encoded({'fixture':'only private registration parser is supplied'})
    monkeypatch.setattr(old.registration,'verified',lambda supplied:value if supplied==raw else None)
    started=b'{}\n';(attempt/'started.json').write_bytes(started);(attempt/'registration.json').write_bytes(raw)
    observation={'checked':False,'passed':False,'reason':'synthetic auth refusal'}
    awake={'passed':True,'policy':policy,'state':'explicitly_not_applicable','signals_received':[]}
    lifecycle_raw={'runtime-observation.json':encoding._encoded(observation),
                   'keep-awake.json':encoding._encoded(awake)}
    gates={name:{'checked':False,'passed':False,'reason':'synthetic incomplete run'} for name in engine.GATES}
    identity=old.expected_runtime_observation(value)
    if 'runtime-observation.json' in present:
        gates['runtime_authority']=checks.runtime_observation_result(lifecycle_raw['runtime-observation.json'],observation,identity)
    if 'keep-awake.json' in present:
        gates['keep_awake']=checks.cleanup_result(lifecycle_raw['keep-awake.json'],awake,policy)
    result={'kind':old.KIND,'version':old.VERSION,'attempt_id':value['attempt_id'],
        'composition_sha256':value['composition_sha256'],'registration_sha256':encoding._sha(raw),
        'started_sha256':encoding._sha(started),**old.UNASSESSED,'gates':gates,
        'runtime_gates_passed':False,'state':'failed','first_stop':'synthetic incomplete run',
        'captured_files':{},'captured_aliases':{},'captured_metadata':{},'captured_alias_metadata':{},
        'runtime_observation':observation,'keep_awake':awake,'additional_report':None,
        'lifecycle_artifacts':{name:{'path':str(attempt/name),'sha256':encoding._sha(lifecycle_raw[name])} for name in present}}
    for name in present:(attempt/name).write_bytes(lifecycle_raw[name])
    final=encoding._encoded(result);(evidence/'final.json').write_bytes(final)
    (evidence/'published.json').write_bytes(encoding._encoded({'final_sha256':encoding._sha(final),
        'started_sha256':encoding._sha(started),'registration_sha256':encoding._sha(raw)}))
    assert old.read_final(raw)==result
    # A rewritten, internally rehashed top-level outcome is still compared with
    # the captured raw bytes by the actual canonical reader.
    field='runtime_observation' if 'runtime-observation.json' in present else 'keep_awake'
    result[field]['passed']=not result[field]['passed']
    final=encoding._encoded(result);(evidence/'final.json').write_bytes(final)
    (evidence/'published.json').write_bytes(encoding._encoded({'final_sha256':encoding._sha(final),
        'started_sha256':encoding._sha(started),'registration_sha256':encoding._sha(raw)}))
    with pytest.raises(ValueError,match='disagree'):
        old.read_final(raw)


def test_fixed_activation_preserves_legacy_and_requires_new_phase_authority():
    contract,_=old._engine_bindings()
    contract.activate_before_dispatch(object(),b'old started identity')
    contract=replace(contract,kind='d4d_native_shared_attempt')
    calls=[]
    adapter=SimpleNamespace(spec=SimpleNamespace(render_version=26,native_shared_generation_version=1),
        policy={'selected':True},classify=lambda:None,observe=lambda:None,
        require_phase_authority=lambda:calls.append('phase'),
        activate_before_dispatch=lambda raw:calls.append(raw))
    contract.activate_before_dispatch(adapter,b'new exact started bytes')
    assert calls==['phase',b'new exact started bytes']
    adapter.spec.render_version=25
    with pytest.raises(ValueError):contract.activate_before_dispatch(adapter,b'foreign')
    assert calls[-1]=='phase' and b'foreign' not in calls


def test_public_authorizations_retains_call_time_file_failure(monkeypatch):
    error=OSError('original observation load fault')
    monkeypatch.setattr(old,'_file',lambda *args:(_ for _ in ()).throw(error))
    with pytest.raises(OSError) as caught:
        old.authorizations(b'registration',{},review_path='/review',ci_path='/ci',launch_word_path='/owner')
    assert caught.value is error
